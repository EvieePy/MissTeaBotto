"""Copyright 2025 MystyPy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import asyncio
import base64
import datetime
import logging
import secrets
from typing import TYPE_CHECKING, Any, cast

import aiohttp
from starlette.responses import RedirectResponse, Response
from twitchio import web

from .config import config


if TYPE_CHECKING:
    from starlette.requests import Request

    from .bot import Bot
    from .types_ import SpotifyRespT


LOGGER: logging.Logger = logging.getLogger(__name__)


SPOTIFY_AUTH = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN = "https://accounts.spotify.com/api/token"


class CustomAdapter(web.StarletteAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.spotify_state: dict[str, datetime.datetime] = {}

        self._clear_state_task: asyncio.Task[None] = asyncio.create_task(self._clear_state())

        self.add_route("/spotify/callback", self.spotify_callback, methods=["GET"])
        self.add_route("/oauth/spotify", self.spotify_oauth, methods=["GET"])
        self.add_route("/overlays/first", self.first_redeem_route, methods=["GET"])

    async def _clear_state(self) -> None:
        while not self._closing:
            await asyncio.sleep(300)

            now = datetime.datetime.now(tz=datetime.UTC)
            states = self.spotify_state.copy()

            for state, dt in states.items():
                if dt + datetime.timedelta(minutes=5) <= now:
                    self.spotify_state.pop(state, None)

    async def close(self, with_client: bool = True) -> None:
        if self._clear_state_task:
            try:
                self._clear_state_task.cancel()
            except Exception as e:
                LOGGER.debug("Unknown error occurred during close of state cleanup task: %s", e)

        return await super().close(with_client)

    async def spotify_oauth(self, request: Request) -> Response:
        client_id: str = config["spotify"]["client_id"]
        redirect: str = config["spotify"]["redirect"]
        state: str = secrets.token_urlsafe(32)
        scope: str = (
            "app-remote-control streaming user-modify-playback-state user-read-playback-state user-read-currently-playing"
        )

        url = f"{SPOTIFY_AUTH}?response_type=code&client_id={client_id}&scope={scope}&redirect_uri={redirect}&state={state}"
        self.spotify_state[state] = datetime.datetime.now(tz=datetime.UTC)

        return RedirectResponse(url)

    async def spotify_callback(self, request: Request) -> Response:
        params = request.query_params

        code = params.get("code", None)
        state = params.get("state", None)
        error = params.get("error", None)

        if error:
            LOGGER.warning("Failed to Authorize Spotify User: %s", error)
            return Response(error, status_code=400)

        if not code:
            return Response("Invalid code provided", status_code=400)

        if not state:
            return Response("Expected a 'state' parameter", status_code=400)

        stored = self.spotify_state.pop(state, None)
        if not stored:
            return Response("Invalid 'state' provided.", status_code=400)

        now = datetime.datetime.now(tz=datetime.UTC)
        if (stored + datetime.timedelta(minutes=5)) <= now:
            return Response("Invalid 'state' provided. Provided state has expired.", status_code=400)

        redirect: str = config["spotify"]["redirect"]
        client_id: str = config["spotify"]["client_id"]
        client_secret: str = config["spotify"]["client_secret"]
        secret = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        headers = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {secret}"}

        data = aiohttp.FormData()
        data.add_field("code", code)
        data.add_field("redirect_uri", redirect)
        data.add_field("grant_type", "authorization_code")

        bot = cast("Bot", self.client)
        session = bot.session

        async with session.post(SPOTIFY_TOKEN, data=data, headers=headers) as resp:
            if resp.status != 200:
                LOGGER.warning("Unexpected status code handling Spotify OAuth: %s", resp.status)
                return Response(f"Unexpected reponse from Spotify: {resp.status}.")

            oauth: SpotifyRespT = await resp.json()

        encrypted_at = bot.fern.encrypt(oauth["access_token"].encode()).decode()
        encrypted_rt = bot.fern.encrypt(oauth["refresh_token"].encode()).decode()
        await bot.db.upsert_spotify(encrypted_at, encrypted_rt)

        return Response("Success. You can now leave this page.")

    async def first_redeem_route(self, request: Request) -> Response:
        bot = cast("Bot", self.client)

        payload = await bot.db.fetch_first_redeem()
        if not payload:
            return Response("First: None?")

        user = await bot.fetch_user(id=payload.user_id)
        return Response(f"First: {user.display_name}")
