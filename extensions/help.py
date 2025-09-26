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

from typing import Any

from twitchio.ext import commands

import core


type CT = commands.Command[Any, ...] | commands.Group[Any, ...]


class CommandConverter(commands.Converter[CT]):
    async def convert(self, ctx: commands.Context[core.Bot], arg: str) -> CT:
        splat = arg.split()
        original = ctx.bot.get_command(splat[0])

        if not original:
            raise core.NoCommandFound(f"No command {arg!r} found.")

        found: CT | None = original
        for n in splat[1:]:
            if not isinstance(found, commands.Group):
                found = None
                break

            found = found.get_command(n)
            if not found:
                break

        if not found:
            raise core.NoCommandFound(f"No command {arg!r} found.")

        try:
            await found.run_guards(ctx, with_cooldowns=False)
        except commands.GuardFailure as e:
            raise core.NoPermissionForCommand(f"No permission to run command {arg!r}.") from e

        return found


class HelpComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot

    async def process_all_help(self, ctx: commands.Context[core.Bot]) -> None:
        comms = ctx.bot.unique_commands
        available: set[CT] = set()

        for comm in comms:
            if isinstance(comm, commands.RewardCommand):
                continue

            try:
                await comm.run_guards(ctx, with_cooldowns=False)
            except commands.GuardFailure:
                continue

            available.add(comm)
            if not isinstance(comm, commands.Group):
                continue

            for sub in comm.walk_commands():
                try:
                    await sub.run_guards(ctx, with_cooldowns=False)
                except commands.GuardFailure:
                    continue

                available.add(sub)

        sorted_ = sorted(available, key=lambda c: c.qualified_name)
        joined = ", ".join(c.qualified_name for c in sorted_)
        await ctx.reply(f"You can use: {joined}")

    @commands.command()
    async def help(self, ctx: commands.Context[core.Bot], *, comm: str | None = None) -> None:
        """Retrieve help for a specific command or view all available commands.
        Usage: !help [command] E.g. To display this message: !help help
        """
        if not comm:
            return await self.process_all_help(ctx)

        converter = CommandConverter()
        found = await converter.convert(ctx, comm)

        assert isinstance(found, commands.Command)

        # We do perm checks for singular commands in converter...
        help = found.help
        if not help:
            await ctx.reply(f"The command: {found.qualified_name} does not have specific help information.")
            return

        await ctx.reply(f"{found.qualified_name}: {help}")

    @help.error
    async def help_error(self, payload: commands.CommandErrorPayload) -> bool | None:
        ctx = payload.context
        error = getattr(payload.exception, "original", payload.exception)

        if isinstance(error, core.NoCommandFound):
            await ctx.reply(f"The command {ctx.kwargs.get('comm', None)} could not be found mystyp2Cry")
            return False

        elif isinstance(error, core.NoPermissionForCommand):
            return False


async def setup(bot: core.Bot) -> None:
    await bot.add_component(HelpComponent(bot))
