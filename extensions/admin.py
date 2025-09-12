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

from twitchio.ext import commands

import core


LOGGER: logging.Logger = logging.getLogger(__name__)


class AdminComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context[core.Bot], *, module: str) -> None:
        if module.startswith("extensions"):
            module = module.removeprefix("extenions.")

        module = f"extensions.{module}"

        try:
            await self.bot.reload_module(module)
        except Exception as e:
            LOGGER.warning("Unable to reload module %r: %s.", module, e)
        else:
            await ctx.send(f"Successfully reloaded: {module}")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(AdminComponent(bot))
