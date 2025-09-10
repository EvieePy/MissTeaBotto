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

import logging
from typing import TYPE_CHECKING

import twitchio
from twitchio import eventsub
from twitchio.authentication import UserTokenPayload
from twitchio.ext import commands

from .config import config


if TYPE_CHECKING:
    from database import Database


LOGGER: logging.Logger = logging.getLogger("Bot")


class Bot(commands.AutoBot):
    def __init__(self, *, db: Database) -> None:
        self.db = db

        options = config["bot"]
        super().__init__(**options, prefix=self.prefix)

    def get_subs(self, user_id: str) -> list[eventsub.SubscriptionPayload]:
        assert self.user

        return [
            eventsub.ChatMessageSubscription(broadcaster_user_id=user_id, user_id=self.user.id),
            eventsub.ChannelFollowSubscription(broadcaster_user_id=user_id, moderator_user_id=user_id),
            eventsub.AdBreakBeginSubscription(broadcaster_user_id=user_id),
            eventsub.ChatNotificationSubscription(broadcaster_user_id=user_id, user_id=self.user.id),
            eventsub.StreamOfflineSubscription(broadcaster_user_id=user_id),
            eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=user_id),
            eventsub.ChannelPointsRedeemUpdateSubscription(broadcaster_user_id=user_id),
        ]

    async def subscribe(self, user_id: str | None = None) -> None:
        # TODO: Logging...

        assert self.user

        if user_id:
            subs = self.get_subs(user_id)
            await self.multi_subscribe(subs)
            return

        tokens = await self.db.fetch_tokens()
        for payload in tokens:
            if payload.user_id == self.user.id:
                continue

            subs = self.get_subs(payload.user_id)
            await self.multi_subscribe(subs)

    async def setup_hook(self) -> None:
        await self.subscribe()

        await self.load_module("extensions")

    async def event_ready(self) -> None:
        LOGGER.info("Logged in as: %s", self.user)

    async def event_oauth_authorized(self, payload: UserTokenPayload) -> None:
        token = payload.access_token
        refresh = payload.refresh_token
        user_id = payload.user_id

        if not user_id:
            # Should never be True (TwitchIO quirk)
            return

        await self.db.add_token(user_id, token, refresh)

        assert self.user
        if user_id == self.user.id:
            # Don't subscribe to events for Bot...
            return

        await self.subscribe(user_id=user_id)

    # NOTE: Twitchio Fix...
    async def prefix(self, _: commands.Bot, message: twitchio.ChatMessage) -> list[str]:
        # TODO: Do this later...

        defaults = config["bot"]["default_prefix"]
        return defaults

    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        error = payload.exception
        
        if isinstance(error, commands.CommandNotFound):
            return
        
        LOGGER.exception(error, exc_info=error, stack_info=True)