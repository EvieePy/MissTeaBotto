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

from typing import TypedDict


class BotOptionsT(TypedDict):
    default_prefix: list[str]
    client_id: str
    client_secret: str
    bot_id: str
    owner_id: str


class DatabaseT(TypedDict):
    dsn: str


class WebhooksT(TypedDict):
    discord: str


class SpotifyT(TypedDict):
    client_id: str
    client_secret: str
    redirect: str


class ConfigT(TypedDict):
    notifications: int
    bot: BotOptionsT
    database: DatabaseT
    webhooks: WebhooksT
    spotify: SpotifyT


class SpotifyRespT(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: str
    scope: str
    token_type: str


class PlayingT(TypedDict, total=False):
    title: str
    url: str
    image: str


class StreamStateT(TypedDict, total=False):
    subscriber: str
    follower: str
    first: str
    playing: PlayingT
