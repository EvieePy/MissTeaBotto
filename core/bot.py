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
import logging
from typing import TYPE_CHECKING

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from .adapter import CustomAdapter
from .cache import TTLCache
from .config import config
from .exceptions import *


if TYPE_CHECKING:
    from aiohttp import ClientSession
    from cryptography.fernet import Fernet
    from twitchio.authentication import UserTokenPayload

    from database import Database

    from .types_ import StreamStateT


LOGGER: logging.Logger = logging.getLogger("Bot")


class Bot(commands.AutoBot):
    def __init__(self, *, db: Database, fern: Fernet, session: ClientSession) -> None:
        self.db = db
        self.fern = fern
        self.session = session
        self.stream_state: StreamStateT = {"playing": {}, "online": False, "chatter_cache": TTLCache()}

        options = config["bot"]
        super().__init__(**options, prefix=self.prefix, adapter=CustomAdapter())

    def get_subs(self, user_id: str) -> list[eventsub.SubscriptionPayload]:
        assert self.user

        return [
            eventsub.ChatMessageSubscription(broadcaster_user_id=user_id, user_id=self.user.id),
            eventsub.ChannelFollowSubscription(broadcaster_user_id=user_id, moderator_user_id=user_id),
            eventsub.AdBreakBeginSubscription(broadcaster_user_id=user_id),
            eventsub.ChatNotificationSubscription(broadcaster_user_id=user_id, user_id=self.user.id),
            eventsub.StreamOnlineSubscription(broadcaster_user_id=user_id),
            eventsub.StreamOfflineSubscription(broadcaster_user_id=user_id),
            eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=user_id),
            eventsub.ChannelPointsRedeemUpdateSubscription(broadcaster_user_id=user_id),
            eventsub.ChatNotificationSubscription(broadcaster_user_id=user_id, user_id=self.user.id),
            eventsub.ChannelRaidSubscription(to_broadcaster_user_id=user_id),
        ]

    def log_sub_errors(self, resp: twitchio.MultiSubscribePayload) -> None:
        for error in resp.errors:
            if error.error.status == 409:
                continue

            LOGGER.error("An error occurred during subscribing: %s", error.error, exc_info=error.error)

    async def subscribe(self, user_id: str | None = None) -> None:
        assert self.user

        if user_id:
            subs = self.get_subs(user_id)
            resp = await self.multi_subscribe(subs)
            self.log_sub_errors(resp)
            return

        tokens = await self.db.fetch_tokens()
        for payload in tokens:
            if payload.user_id == self.user.id:
                continue

            subs = self.get_subs(payload.user_id)
            resp = await self.multi_subscribe(subs)
            self.log_sub_errors(resp)

    async def setup_hook(self) -> None:
        await self.subscribe()
        await self.load_module("extensions")
        await self.update_state()

    async def event_ready(self) -> None:
        LOGGER.info("Logged in as: %s", self.user)

    async def update_state(self) -> None:
        if not self.owner:
            LOGGER.warning("No user object available for owner. Stream state cannot be updated.")
            return

        followers = await self.owner.fetch_followers(first=1)
        latest_follow = (await followers.followers)[0]

        with open("static/LSUB") as fp:
            latest_sub = fp.read()

        first = await self.db.fetch_first_redeem()
        first_user = await self.fetch_user(id=first.user_id) if first else None

        self.stream_state["follower"] = latest_follow.user.display_name or str(latest_follow.user)
        self.stream_state["subscriber"] = latest_sub
        self.stream_state["first"] = first_user.display_name if first_user else "None?"

        streams = self.fetch_streams(user_ids=[str(self.owner_id)], max_results=20)
        async for stream in streams:
            if stream.user.id != self.owner_id:
                continue

            self.stream_state["online"] = True

        LOGGER.info("Successfully updated Stream State.")

    async def event_oauth_authorized(self, payload: UserTokenPayload) -> None:
        token = payload.access_token
        refresh = payload.refresh_token
        user_id = payload.user_id

        if not user_id:  # Should never be True (TwitchIO quirk)
            return

        encrypted_at = self.fern.encrypt(token.encode()).decode()
        encrypted_rt = self.fern.encrypt(refresh.encode()).decode()
        await self.db.add_token(user_id, encrypted_at, encrypted_rt)

        assert self.user
        if user_id == self.user.id:  # Don't subscribe to events for Bot...
            return

        await self.subscribe(user_id=user_id)

    async def load_tokens(self, path: str | None = None) -> None:
        tokens = await self.db.fetch_tokens()

        for payload in tokens:
            encrypted_at = payload.access_token
            encrypted_rt = payload.refresh_token

            token = self.fern.decrypt(encrypted_at).decode()
            refresh = self.fern.decrypt(encrypted_rt).decode()

            await self.add_token(token=token, refresh=refresh)

    # NOTE: Twitchio Fix... (Type buggo)
    async def prefix(self, _: commands.Bot, message: twitchio.ChatMessage) -> list[str]:
        # TODO: Do this later...

        defaults = config["bot"]["default_prefix"]
        return defaults

    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        error = getattr(payload.exception, "original", payload.exception)
        ctx = payload.context

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"You are on cooldown. Try again in {int(error.remaining)} seconds.")
            return
        elif isinstance(error, (commands.CommandNotFound, commands.GuardFailure, NoCommandFound, NoPermissionForCommand)):
            return

        LOGGER.exception(error, exc_info=error, stack_info=True)

    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        if not payload.broadcaster or payload.broadcaster.id != self.owner_id:
            return

        webhook = config["webhooks"]["discord"]
        if not webhook:
            return

        # Discords embed bot vs Twitch's Embed data are slightly out of sync...
        await asyncio.sleep(10)

        webhook = config["webhooks"]["discord"]
        url = f"https://twitch.tv/{payload.broadcaster.name}"

        data = {
            "allowed_mentions": {"parse": ["roles"]},
            "content": f"<@&{config['notifications']}> {payload.broadcaster.name} is live and streaming!\n\n{url}",
        }

        async with self.session.post(webhook, json=data) as resp:
            if resp.status >= 300:
                LOGGER.warning("Unable to send discord live notification: %s", resp.status)

    async def event_chat_notification(self, payload: twitchio.ChatNotification) -> None:
        if payload.notice_type not in ("sub", "resub"):
            return

        if payload.anonymous:
            return

        with open("static/LSUB", "w") as fp:
            sub = payload.chatter.display_name or str(payload.chatter)
            fp.write(sub)

            self.stream_state["subscriber"] = sub

    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        self.stream_state["follower"] = payload.user.display_name or str(payload.user)
