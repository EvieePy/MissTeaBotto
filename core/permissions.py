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

import enum
from typing import TYPE_CHECKING, Any

import twitchio
from twitchio.ext import commands


if TYPE_CHECKING:
    from .bot import Bot


__all__ = ("ModPermissions", "permissions_check")


class ModPermissions(enum.IntFlag):
    none = enum.auto()

    # Special case role bypasses any permissions...
    admin = enum.auto()

    # Permissions
    edit = enum.auto()
    ban = enum.auto()
    timeout = enum.auto()
    warn = enum.auto()
    shoutout = enum.auto()
    raid = enum.auto()
    ads = enum.auto()

    @classmethod
    def perms(cls, o: int) -> list[tuple[str | None, bool]]:
        flags = [(m.name, (o & m) == m) for m in cls]
        return flags


def permissions_check(perms: ModPermissions) -> Any:
    async def predicate(ctx: commands.Context[Bot]) -> bool:
        assert isinstance(ctx.chatter, twitchio.Chatter)
        bot = ctx.bot

        if ctx.chatter.id == bot.owner_id:
            return True

        payload = await bot.db.fetch_mod(ctx.chatter.id)
        if not payload:
            return False

        if (payload.flags & perms) == ModPermissions.admin:
            return True

        return bool(payload.flags & perms)

    return commands.guard(predicate)
