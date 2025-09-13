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
import datetime
import logging
from typing import TYPE_CHECKING

import twitchio  # noqa: TC002
from twitchio.ext import commands, routines


if TYPE_CHECKING:
    import core


LOGGER: logging.Logger = logging.getLogger(__name__)


class GeneralComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot

    async def component_teardown(self) -> None:
        self.discord_routine.cancel()

    async def component_load(self) -> None:
        self.discord_routine.start()

    @routines.routine(delta=datetime.timedelta(minutes=30), wait_first=True)
    async def discord_routine(self) -> None:
        # TODO: Logging...

        user = self.bot.owner
        if not user:
            return

        assert self.bot.user
        await user.send_message("Join my discord for tea! https://discord.gg/cft7GbQt58", sender=self.bot.user)

    @commands.Component.listener()
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        LOGGER.info("Ad-Break begin received for %s.", payload.broadcaster)

        if payload.broadcaster.id != self.bot.owner_id:
            return

        assert self.bot.user
        await payload.broadcaster.send_announcement(
            message=f"An Ad-Break is starting for {payload.duration} seconds. Chat soon mystyp2Sip mystyp2Cry",
            moderator=self.bot.user,
            color="orange",
        )
        
        await asyncio.sleep(payload.duration)
        await payload.broadcaster.send_message(message="Welcome back from ads! mystyp2Pats", sender=self.bot.user)
        
    async def event_custom_redemption_add(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        if payload.broadcaster.id != self.bot.owner_id:
            return
        
        title = payload.reward.title
        if title == "First!":
            await self.bot.db.add_first_redeem(payload.user.id)

    @commands.group()
    async def socials(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.send("Discord: https://discord.gg/cft7GbQt58, GitHub: https://github.com/EvieePy")

    @socials.command(aliases=["disco", "dc"])
    async def discord(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.send("https://discord.gg/cft7GbQt58")

    @socials.command(aliases=["git", "gh"])
    async def github(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.send("https://github.com/EvieePy")

    @commands.command(aliases=["disco", "dc", "discord"])
    async def discord_command(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.send("https://discord.gg/cft7GbQt58")

    @commands.command(aliases=["l", "bye"])
    async def lurk(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.reply(f"Thanks for the lurky lurk {ctx.chatter.mention} mystyp2Love")

    @commands.command()
    async def code(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.reply("My code: https://github.com/EvieePy/MissTeaBotto")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(GeneralComponent(bot))
