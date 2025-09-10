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

import datetime
from typing import TYPE_CHECKING

from twitchio.ext import commands, routines

if TYPE_CHECKING:
    import core


class GeneralComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self.discord_routine.start()

    @commands.command()
    async def test(self, ctx: commands.Context[core.Bot]) -> None:
        await ctx.send("wot")
        
    @routines.routine(delta=datetime.timedelta(minutes=30))
    async def discord_routine(self) -> None:
        # TODO: Logging...
        
        user = self.bot.owner
        if not user:
            return
        
        assert self.bot.user
        await user.send_message("Join my discord for tea! https://discord.gg/cft7GbQt58", sender=self.bot.user)


async def setup(bot: core.Bot) -> None:
    await bot.add_component(GeneralComponent(bot))
