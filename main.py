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

import asyncio
import logging
import platform

import aiohttp
from cryptography.fernet import Fernet
from twitchio.utils import setup_logging

import core
from database import Database


LOGGER: logging.Logger = logging.getLogger(__name__)


def set_event_loop() -> None:
    system = platform.system()

    if system == "Windows":
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
        LOGGER.warning("Set Event Loop Policy for windows to ProtactorEventLoop.")


def main() -> None:
    setup_logging()
    set_event_loop()

    with open(".secret") as fp:
        key = fp.read()
        fern = Fernet(key)

    async def runner() -> None:
        async with (
            aiohttp.ClientSession() as session,
            Database(**core.config["database"]) as db,
            core.Bot(db=db, fern=fern, session=session) as bot,
        ):
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt.")


if __name__ == "__main__":
    main()
