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

import twitchio
from twitchio.ext import commands

import core


LOGGER: logging.Logger = logging.getLogger(__name__)


class FlagConverter(commands.Converter[int]):
    async def convert(self, ctx: commands.Context[core.Bot], arg: str) -> core.ModPermissions:
        try:
            value = int(arg)
        except ValueError:
            return core.ModPermissions[arg]

        return core.ModPermissions(value)


class AdminComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot

    @commands.Component.guard()
    async def owner_guard(self, ctx: commands.Context[core.Bot]) -> bool:
        return ctx.chatter.id == self.bot.owner_id

    @commands.command()
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

    @commands.command()
    async def create_reward(
        self,
        ctx: commands.Context[core.Bot],
        name: str,
        cost: int,
        skip: bool,
        *,
        prompt: str | None = None,
    ) -> None:
        assert self.bot.owner_id

        user = self.bot.create_partialuser(user_id=self.bot.owner_id)
        reward = await user.create_custom_reward(name, cost, prompt=prompt, redemptions_skip_queue=skip)

        await ctx.reply(f"Successfully created reward: {reward.title} (ID: {reward.id})")

    @commands.command(name="modupdate", aliases=["mod_update"])
    async def update_mod(self, ctx: commands.Context[core.Bot], user: twitchio.User, *perms: FlagConverter) -> None:
        name = ""
        flags = 0

        for perm in set(perms):
            assert isinstance(perm, core.ModPermissions)

            flags |= perm
            name += f"{perm.name}, "

        await self.bot.db.upsert_mod(user.id, flags=flags)
        await ctx.reply(f"Updated {user.mention} with {name.removesuffix(', ')}.")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(AdminComponent(bot))
