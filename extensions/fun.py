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

import logging
from typing import TYPE_CHECKING, cast

import twitchio
from twitchio.ext import commands

import core


if TYPE_CHECKING:
    from core.types_ import AlertEventT


LOGGER: logging.Logger = logging.getLogger(__name__)


class FunComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self.adapter: core.CustomAdapter = cast(core.CustomAdapter, self.bot.adapter)

    @commands.reward_command(id="62ee12ad-4c52-44b4-92a4-2d69727464b6", invoke_when=commands.RewardStatus.fulfilled)
    async def sorry_cat(self, ctx: commands.Context[core.Bot]) -> None:
        message = f"{ctx.author.display_name} says sorry :("
        data: AlertEventT = {
            "name": "sorry",
            "data": {
                "audio": "/static/sounds/alerts/sadcat.mp3",
                "image": "/static/images/alerts/sadcat.gif",
                "text": message,
            },
            "duration": 25,
        }
        await self.adapter.add_alert(data)

    @commands.reward_command(id="9b8fb1ab-06d7-43ba-85be-e796d1e5f393", invoke_when=commands.RewardStatus.fulfilled)
    async def happy_cat(self, ctx: commands.Context[core.Bot]) -> None:
        message = f"{ctx.author.display_name} is happy!"
        data: AlertEventT = {
            "name": "sorry",
            "data": {
                "audio": "/static/sounds/alerts/happycat.mp3",
                "image": "/static/images/alerts/catdance.gif",
                "text": message,
            },
            "duration": 8,
        }

        await self.adapter.add_alert(data)

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        user = payload.from_broadcaster.display_name
        count = payload.viewer_count
        message = f"{user} just raided with {count} new kit-teas!"

        data: AlertEventT = {
            "name": "raid",
            "data": {
                "audio": "/static/sounds/alerts/catrap.mp3",
                "image": "/static/images/alerts/catraid1.gif",
                "text": message,
            },
            "duration": 11,
        }
        await self.adapter.add_alert(data)


async def setup(bot: core.Bot) -> None:
    await bot.add_component(FunComponent(bot))
