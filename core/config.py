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

from typing import TYPE_CHECKING

from dotenv import dotenv_values
from yaml import Loader, load


if TYPE_CHECKING:
    from .types_ import ConfigT


env = dotenv_values(".env")

try:
    CID: str = env["CLIENT_ID"]  # type: ignore
    CSEC: str = env["CLIENT_SECRET"]  # type: ignore
    BID: str = env["BOT_ID"]  # type: ignore
    OID: str = env["OWNER_ID"]  # type: ignore
    DWEB: str = env["DISCORD_WEBHOOK"]  # type: ignore
    SPOT: str = env["SPOTIFY_SECRET"]  # type: ignore
except KeyError as e:
    raise RuntimeError("Unable to start Bot: An environment variable is missing.") from e


with open("config.yaml") as fp:
    config: ConfigT = load(fp, Loader)

    config["bot"]["client_id"] = CID
    config["bot"]["client_secret"] = CSEC
    config["bot"]["bot_id"] = BID
    config["bot"]["owner_id"] = OID
    config["webhooks"]["discord"] = DWEB
    config["spotify"]["client_secret"] = SPOT
