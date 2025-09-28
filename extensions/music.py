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
import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

import aiohttp
import twitchio
from twitchio.ext import commands

import core


if TYPE_CHECKING:
    from core.types_ import SpotifyRespT


SPOTIFY_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH = SPOTIFY_BASE + "/search"
SPOTIFY_DEVICES = SPOTIFY_BASE + "/me/player/devices"
SPOTIFY_QUEUE = SPOTIFY_BASE + "/me/player/queue"
SPOTIFY_CURRENT = SPOTIFY_BASE + "/me/player/currently-playing"


LOGGER: logging.Logger = logging.getLogger(__name__)


class Music(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self.db = bot.db

        self._device: str | None = None
        self._current_song_task: asyncio.Task[None] | None = None

    async def component_load(self) -> None:
        self._current_song_task = asyncio.create_task(self._check_current_song())

    async def component_teardown(self) -> None:
        if not self._current_song_task:
            return

        try:
            self._current_song_task.cancel()
        except Exception:
            pass

    async def _process_current_song(self, data: dict[str, Any] | None) -> float:
        LOGGER.debug("Updating Spotify Now Playing...")

        if not data:
            self.bot.stream_state["playing"] = {}
            return 10

        track = data.get("item")
        if not track:
            self.bot.stream_state["playing"] = {}
            return 10

        duration: int = track["duration_ms"]
        progress: int | None = data.get("progress_ms")
        remaining: int = duration - progress if progress else 10000
        remaining_s: float = remaining / 1000

        name: str = f"{track['name']} - {track['artists'][0]['name']}"
        update = {"title": name, "url": track["href"], "image": track["album"]["images"][0]["url"]}
        self.bot.stream_state["playing"].update(update)  # type: ignore

        return min(remaining_s + 1, 10)

    async def _check_current_song(self) -> None:
        while True:
            data = await self.make_request(SPOTIFY_CURRENT)
            duration = await self._process_current_song(data)

            await asyncio.sleep(duration)

    async def _refresh(self, refresh: str) -> str | None:
        client_id = core.config["spotify"]["client_id"]
        client_secret = core.config["spotify"]["client_secret"]

        secret = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {secret}"}

        data = aiohttp.FormData()
        data.add_field("refresh_token", refresh)
        data.add_field("grant_type", "refresh_token")

        async with self.bot.session.post(SPOTIFY_TOKEN, headers=headers, data=data) as resp:
            if resp.status != 200:
                LOGGER.error("Unable to refresh Spotify token: %s. Consider re-authenticating", resp.status)
                return

            oauth: SpotifyRespT = await resp.json()

            token = oauth["access_token"]
            new_refresh = oauth.get("refresh_token", None) or refresh

            encrypted_at = self.bot.fern.encrypt(token.encode()).decode()
            encrypted_rt = self.bot.fern.encrypt(new_refresh.encode()).decode()
            await self.bot.db.upsert_spotify(encrypted_at, encrypted_rt)

            return token

    async def make_request(self, url: str, method: str = "GET") -> dict[str, Any] | None:
        payload = await self.db.fetch_spotify()
        if not payload:
            return

        token = self.bot.fern.decrypt(payload.token).decode()
        refresh = self.bot.fern.decrypt(payload.refresh).decode()

        new: str | None = token

        while True:
            headers = {"Authorization": f"Bearer {new}"}

            async with self.bot.session.request(method, url, headers=headers) as resp:
                if resp.status == 401:
                    new = await self._refresh(refresh)

                    if new is None:
                        return

                    continue

                if resp.status == 204:
                    return

                resp.raise_for_status()

                try:
                    data = await resp.json()
                except Exception:
                    return

                return data

    def parse_search(self, resp: dict[str, Any]) -> None | dict[str, Any]:
        tracks = resp.get("tracks")
        if not tracks:
            return

        items = tracks["items"]
        if not items:
            return

        for item in items:
            if item["type"] == "track":
                return item

    async def find_device(self) -> None:
        try:
            data = await self.make_request(SPOTIFY_DEVICES)
        except Exception:
            return

        if not data:
            return

        devices = data.get("devices", None)
        if not devices:
            return

        for device in devices:
            if device["type"].lower() != "computer":
                continue

            self._device = device["id"]
            break

    async def enque_track(self, track: str) -> None | bool | dict[str, Any]:
        if not self._device:
            await self.find_device()

        if not self._device:
            raise core.SpotifyDeviceNotFound("No device for playback is available.")

        encoded = urllib.parse.quote(track)
        return await self.make_request(SPOTIFY_QUEUE + f"?uri={encoded}&device_id={self._device}", method="POST")

    @commands.reward_command(id="3231fc73-5a6a-4fdb-a0dc-40bf8e2260b9", invoke_when=commands.RewardStatus.unfulfilled)
    async def redeem_song(self, ctx: commands.Context[core.Bot], *, prompt: str | None = None) -> None:
        assert ctx.redemption and isinstance(ctx.redemption, twitchio.ChannelPointsRedemptionAdd)
        assert self.bot.owner_id

        if not prompt:
            await ctx.send("You need to actually request a song mystyp2Pats")
            await ctx.redemption.refund(token_for=self.bot.owner_id)
            return

        elif len(prompt) < 5:
            await ctx.send("You need to actually request a song mystyp2Pats More than 5 characters!")
            await ctx.redemption.refund(token_for=self.bot.owner_id)
            return

        encoded = urllib.parse.quote(prompt)
        resp: dict[str, Any] | None = None

        try:
            resp = await self.make_request(url=f"{SPOTIFY_SEARCH}?type=track&limit=5&q={encoded}")
        except Exception:
            pass

        if not resp:
            await ctx.redemption.refund(token_for=self.bot.owner_id)
            await ctx.send("An error occurred. Please try again later mystyp2Cry Your points were refunded.")
            return

        track = self.parse_search(resp)

        if not track:
            await ctx.redemption.refund(token_for=self.bot.owner_id)
            await ctx.send(f"A track with the prompt '{prompt}' could not be found mystyp2Cry Your points were refunded.")
            return

        try:
            await self.enque_track(track["uri"])
        except Exception as e:
            await ctx.send(f"{ctx.chatter.mention} an error occurred trying to queue your track: {e}.")
            return

        artists = ", ".join(a["name"] for a in track["artists"])
        await ctx.send(f"{ctx.chatter.mention} I have queued your request: {track['name']} by {artists}")

    @commands.command(aliases=["current", "song", "currentsong", "np", "nowplaying", "playing"])
    async def now_playing(self, ctx: commands.Context[core.Bot]) -> None:
        """Retrieve the currently playing track on stream.
        Usage: !np|current|song|currentsong|playing|nowplaying|now_playing
        """
        title = self.bot.stream_state.get("playing", {}).get("title", "Nothing!")
        await ctx.reply(f"Currently playing: {title}")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(Music(bot))
