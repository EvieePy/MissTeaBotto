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
import logging
import random
from typing import TYPE_CHECKING

import twitchio  # noqa: TC002
from twitchio.ext import commands, routines

import core


if TYPE_CHECKING:
    from ..database import Database
    from ..database.models import GambleModel


LOGGER: logging.Logger = logging.getLogger(__name__)


class GambleComponent(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self.db: Database = bot.db
        self.speakers: dict[str, datetime.datetime] = {}

        self.time_to_speak: int = 30
        self.point_addition: int = 3

        self.base_exp: int = 100
        self.base_per: int = 50
        self.sheps_per: int = 55
        self.mul: int = 10

        self.rob_exp: int = 100
        self.rob_per: int = 15

        self.point_mul: float = 1.75
        self.all_points_mul: float = 2.25

    async def component_load(self) -> None:
        self.check_points.start()

    async def component_teardown(self) -> None:
        self.check_points.cancel()

    @routines.routine(delta=datetime.timedelta(minutes=1))
    async def check_points(self) -> None:
        LOGGER.debug("Attempting to update points.")

        now = datetime.datetime.now(tz=datetime.UTC)

        for user, ts in self.speakers.copy().items():
            if ts + datetime.timedelta(minutes=self.time_to_speak) <= now:
                self.speakers.pop(user, None)

        if not self.speakers:
            return

        await self.db.batch_add_points(self.speakers, points=self.point_addition)

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        if payload.broadcaster != self.bot.owner:
            return

        self.bot.stream_state["online"] = True

    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        if payload.broadcaster != self.bot.owner:
            return

        self.bot.stream_state["online"] = False
        self.speakers.clear()

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        if payload.chatter.id == self.bot.bot_id:
            return

        if not self.bot.stream_state.get("online", False):
            return

        self.speakers[payload.chatter.id] = datetime.datetime.now(tz=datetime.UTC)

    async def parse_points(self, ctx: commands.Context[core.Bot], amount: str, current: int) -> int | bool:
        value: float

        amount = amount.replace(" ", "")
        if amount.endswith("%"):
            amount = amount.removesuffix("%")
            value = float(amount)

            if value <= 0:
                await ctx.reply("No!")
                return False

            elif value > 100:
                await ctx.reply("Silly!")
                return False

            per = value / 100
            return int(per * current)

        value = float(amount)
        if value < 0:
            await ctx.send("Don't do this...")
            return False

        return int(value)

    async def do_gamble(
        self,
        chatter: twitchio.Chatter | twitchio.PartialUser,
        old: GambleModel,
        *,
        amount: int | None = None,
        everything: bool = False,
    ) -> tuple[GambleModel, bool]:
        mul = self.all_points_mul if everything else self.point_mul
        total = old.points if everything else (amount or 1)

        per = self.sheps_per if chatter.id == "124081412" else self.base_per
        selection = random.randint(0, self.base_exp * self.mul)
        win = selection <= (per * self.mul)

        points = int(-total if not win else ((total) * mul))
        updated = await self.db.update_points(chatter.id, points)

        assert updated
        return updated, win

    @commands.group(invoke_fallback=True)
    @commands.cooldown(rate=2, per=8)
    async def gamble(self, ctx: commands.Context[core.Bot], *, amount: str) -> None:
        """Gamble the provided amount of points.
        Usage: !gamble <amount>
        """
        chatter = ctx.chatter

        record = await self.db.fetch_points(chatter.id)
        if not record or record.points <= 0:
            await ctx.reply("You have no points mystyp2Cry")
            return

        try:
            parsed = await self.parse_points(ctx, amount=amount, current=record.points)
        except Exception:
            await ctx.send("Please enter a valid number or percentage LUL")
            return

        if parsed is False:
            return

        if record.points < parsed:
            await ctx.reply(f"You do not have enough points! You have: {record.points} points!")
            return

        updated, win = await self.do_gamble(chatter, old=record, amount=parsed)
        if win:
            await ctx.send(
                f"{chatter.mention} gambled {parsed} points and won! PipeHype They now have: {updated.points} points!"
            )
        else:
            await ctx.send(f"{chatter.mention} gambled {parsed} points and lost LUL They now have: {updated.points} points!")

    @gamble.command(name="all")
    async def gamble_all(self, ctx: commands.Context[core.Bot]) -> None:
        """Gamble all your current points for a chance of a better return.
        Usage: !gamble all
        """
        chatter = ctx.chatter

        record = await self.db.fetch_points(chatter.id)
        if not record or record.points <= 0:
            await ctx.reply("You have no points mystyp2Cry")
            return

        updated, win = await self.do_gamble(chatter, old=record, everything=True)

        if win:
            await ctx.send(
                f"{chatter.mention} gambled everything and WON! PipeHype PipeHype They now have: {updated.points} points!"
            )
        else:
            await ctx.send(f"{chatter.mention} gambled everything and lost everything LUL LUL")

    async def fetch_top_n(self, ctx: commands.Context[core.Bot], n: int = 5) -> None:
        records = (await self.db.fetch_all_points(order=True))[:n]
        users = {u.id: u for u in await self.bot.fetch_users(ids=[r.user_id for r in records])}

        strings: list[str] = []
        for record in records:
            user = users.get(record.user_id)
            if not user:
                continue

            strings.append(f"{user.mention}: {record.points}")
        await ctx.send(f"Top {n}: " + ", ".join(strings))

    @commands.group(invoke_fallback=True)
    @commands.cooldown(rate=3, per=30)
    async def points(self, ctx: commands.Context[core.Bot], *, user: twitchio.User | None = None) -> None:
        """Check points for yourself or a provided user.
        Usage: !points [user]
        """
        to_fetch = user or ctx.chatter
        record = await self.db.fetch_points(user_id=to_fetch.id)

        if not record:
            await ctx.reply(f"{to_fetch.mention} has never made any points here!")
            return

        await ctx.reply(f"{to_fetch.mention} has {record.points} points!")

    @points.command(name="leaderboard", aliases=["board", "leaders", "top", "leader"])
    @commands.cooldown(rate=3, per=30)
    async def points_leaderboard(self, ctx: commands.Context[core.Bot]) -> None:
        """Fetch and display the top 5 points leaders.
        Usage: !points leaderboard|board|leaders|top
        """
        await self.fetch_top_n(ctx)

    @points.command(aliases=["donate"])
    @core.permissions_check(perms=core.ModPermissions.admin)
    async def give(self, ctx: commands.Context[core.Bot], user: twitchio.User, *, amount: int) -> None:
        """Give points to another user. This is not the same as sharing as no points are taken from you.
        Usage: !give|donate <user> <amount>
        """
        await self.db.update_points(user.id, amount)
        await ctx.reply(f"You have granted {user.mention} {amount} points mystyp2Sip")

    @points.command(aliases=["share"])
    async def send(self, ctx: commands.Context[core.Bot], user: twitchio.User, *, amount: str) -> None:
        """Send some of your points to a user.
        Usage: !send|share <user> <amount>
        """
        chatter = ctx.chatter

        record = await self.db.fetch_points(chatter.id)
        if not record or record.points == 0:
            await ctx.reply("You have no points to send mystyp2Cry")
            return

        try:
            parsed = await self.parse_points(ctx, amount=amount, current=record.points)
        except Exception:
            await ctx.reply("Please enter a valid number or percentage to send LUL")
            return

        if parsed is False:
            return

        if record.points < parsed:
            await ctx.reply(f"You do not have enough points to send! You have: {record.points} points!")
            return

        await self.db.update_points(chatter.id, -parsed)
        await self.db.update_points(user.id, parsed)

        await ctx.reply(f"You sent {user.mention} {parsed} points mystyp2Sip")

    @commands.command()
    @commands.cooldown(rate=2, per=120, base=commands.GCRACooldown)
    async def rob(self, ctx: commands.Context[core.Bot], *, user: twitchio.User) -> None:
        """Attempt to rob another user. 10% chance to win, 10% chance to backfire!
        Usage: !rob <user>
        """
        chatter = ctx.chatter

        record = await self.db.fetch_points(user.id)
        if not record or record.points == 0:
            await ctx.reply(f"You can not rob {user.mention} they are too poor mystyp2Cry")
            return

        other = await self.db.fetch_points(chatter.id)
        if not other or other.points < -10:
            await ctx.reply(f"You can not rob {user.mention} you are in too much debt mystyp2Cry")
            return

        chosen = random.randint(0, self.rob_exp)
        win = chosen <= self.rob_per
        backfire = chosen >= (self.rob_exp - self.rob_per)
        points = min(record.points, random.randint(1, 100))

        if win:
            await self.db.update_points(user.id, -points)
            await self.db.update_points(chatter.id, points)
            await ctx.reply(f"You robbed {user.mention} of {points} of their points mystyp2Sip")
        elif backfire:
            await self.db.update_points(user.id, points)
            await self.db.update_points(chatter.id, -points)
            await ctx.reply(
                f"You tried to rob {user.mention} but they pulled a weapon and stole {points} of your points instead mystyp2Nerd"
            )
        else:
            await self.db.update_points(chatter.id, -10)
            await ctx.reply(f"You tried to rob {user.mention} but failed and lost 10 points mystyp2Pats")


async def setup(bot: core.Bot) -> None:
    await bot.add_component(GambleComponent(bot))
