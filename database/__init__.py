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
import logging
from typing import TYPE_CHECKING, Any, Self

import asyncpg

from .models import *


if TYPE_CHECKING:
    type PoolT = asyncpg.Pool[asyncpg.Record]

else:
    type PoolT = asyncpg.Pool


LOGGER: logging.Logger = logging.getLogger("Database")


class Database:
    def __init__(self, *, dsn: str) -> None:
        self.pool: PoolT | None = None
        self.dsn = dsn

    def __repr__(self) -> str:
        return "Database(...)"

    async def __aenter__(self) -> Self:
        return await self.setup()

    async def __aexit__(self, *_: Any, **__: Any) -> None:
        return await self.close()

    async def setup(self) -> Self:
        pool: PoolT = await asyncpg.create_pool(dsn=self.dsn)

        try:
            with open("schema.sql") as fp:
                await pool.execute(fp.read())
        except Exception as e:
            raise RuntimeError(f"Unable to start {self!r}: An error occurred loading schema: {e}.")

        self.pool = pool
        return self

    async def close(self) -> None:
        if not self.pool or self.pool.is_closing():
            return

        try:
            async with asyncio.timeout(10):
                await self.pool.close()
        except TimeoutError:
            LOGGER.warning("Unable to gracefully close Database Pool: Forcefully terminating.")
            self.pool.terminate()
        else:
            LOGGER.info("Gracefully shutdown Database Pool.")

    async def add_token(self, user_id: str, token: str, refresh: str) -> None:
        assert self.pool

        query = """INSERT INTO
        tokens (user_id, access_token, refresh_token)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO NOTHING
        """

        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, token, refresh)

    async def fetch_tokens(self) -> list[TokenModel]:
        assert self.pool

        query = """SELECT * FROM tokens"""

        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, record_class=TokenModel)

        return records

    async def batch_add_points(self, speakers: dict[str, Any], *, points: int) -> None:
        assert self.pool

        query = """INSERT INTO
        gambles (user_id, points)
        VALUES ($1, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET points = gambles.points + $2
        """

        args = [(k, points) for k in speakers]
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args)

    async def fetch_all_points(self, order: bool = False) -> list[GambleModel]:
        assert self.pool

        query = """SELECT * FROM gambles ORDER BY points DESC""" if order else """SELECT * FROM gambles"""
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, record_class=GambleModel)

        return records

    async def fetch_points(self, user_id: str) -> GambleModel | None:
        assert self.pool

        query = """SELECT * FROM gambles WHERE user_id = $1"""

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, user_id, record_class=GambleModel)

    async def update_points(self, user_id: str, points: float) -> GambleModel | None:
        assert self.pool

        query = """INSERT INTO
        gambles (user_id, points)
        VALUES ($1, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET points = gambles.points + $2
        RETURNING *
        """

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, user_id, points, record_class=GambleModel)
