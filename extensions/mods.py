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

import twitchio
from twitchio.ext import commands

import core


class ModeratorComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self._raid: twitchio.User | None = None

    @core.permissions_check(perms=core.ModPermissions.timeout)
    async def timeout(self, ctx: commands.Context[core.Bot], user: twitchio.User, duration: int, *, reason: str) -> None:
        """Timeout a user for a specified amount of time (as seconds).
        Usage: !timeout <user> <duration> [reason]. E.g. !timeout mystypy 600 for being a loser.
        """
        try:
            await ctx.broadcaster.timeout_user(moderator=self.bot.user, user=user, duration=duration, reason=reason)
        except twitchio.HTTPException as e:
            await ctx.reply(f"An error occurred attempting to timeout {user}: {e}")
            return

        await ctx.reply("VoteYea")

    @core.permissions_check(perms=core.ModPermissions.warn)
    async def warn(self, ctx: commands.Context[core.Bot], user: twitchio.User, *, reason: str) -> None:
        """Warn a user with the provided reason.
        Usage: !warn <user> <reason>. E.g. !warn mystypy for being a loser.
        """
        assert self.bot.user

        try:
            await ctx.broadcaster.warn_user(moderator=self.bot.user, user_id=user, reason=reason)
        except twitchio.HTTPException as e:
            await ctx.reply(f"An error occurred attempting to warn {user}: {e}")
            return

        await ctx.reply("VoteYea")

    @core.permissions_check(perms=core.ModPermissions.shoutout)
    @commands.command(aliases=["so", "shout"])
    @commands.cooldown(rate=2, per=120, key=commands.BucketType.channel)
    async def shoutout(self, ctx: commands.Context[core.Bot], *, user: twitchio.User) -> None:
        """Send a shoutout announcement to a user.
        Usage: !shoutout <user>. E.g. !shoutout mystypy

        This command has a cooldown of 2/120s.
        """
        info = await user.fetch_channel_info()
        url = f"https://twitch.tv/{user.name}"

        await ctx.send_announcement(
            (f"Shoutout to {user.mention} Go check them out! mystyp2Love They were last playing {info.game_name} {url}")
        )

    @core.permissions_check(perms=core.ModPermissions.raid)
    @commands.group(invoke_fallback=True)
    async def raid(self, ctx: commands.Context[core.Bot], *, user: twitchio.User) -> None:
        """Start a raid to the provided channel.
        Usage: !raid <user> E.g. !raid mystypy
        """
        if self._raid:
            await ctx.reply("A raid has already begun!")
            return

        try:
            await ctx.broadcaster.start_raid(to_broadcaster=user.id)
        except twitchio.HTTPException as e:
            await ctx.reply(f"Starting a raid to {user} failed: {e}")
            return

        self._raid = user
        await ctx.send(f"{ctx.chatter.mention} has started a raid to {user.mention}!")

    @core.permissions_check(perms=core.ModPermissions.raid)
    @raid.command(name="cancel")
    async def raid_cancel(self, ctx: commands.Context[core.Bot]) -> None:
        """Cancel an ongoing raid started by a moderator.
        Usage: !raid cancel
        """
        if not self._raid:
            await ctx.reply("There is no current raid in progress.")
            return

        try:
            await ctx.broadcaster.cancel_raid()
        except twitchio.HTTPException as e:
            await ctx.reply(f"Unable to cancel raid: {e}")
            return

        user = self._raid
        self._raid = None

        await ctx.send(f"{ctx.chatter.mention} cancelled the current raid! {user.display_name}")

    @raid.error
    async def raid_error(self, payload: commands.CommandErrorPayload) -> bool | None: ...

    @commands.command()
    async def perms(self, ctx: commands.Context[core.Bot], *, user: twitchio.User | None = None) -> None:
        """Check your fine-grained moderator permissions.
        Usage: !perms
        """
        chatter = user or ctx.chatter
        payload = await self.bot.db.fetch_mod(chatter.id)

        if not payload:
            await ctx.reply(f"{chatter.mention} has no granted moderator permissions mystyp2Cry")
            return

        flags = core.ModPermissions.perms(payload.flags)
        joined = ", ".join([str(p[0]) for p in flags if p[1]])

        await ctx.reply(f"{chatter.mention} moderator permissions are: {joined}")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(ModeratorComponent(bot))
