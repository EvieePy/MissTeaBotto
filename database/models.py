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

from typing import Any

import asyncpg


__all__ = ("TokenModel",)


class TokenModel(asyncpg.Record):
    access_token: str
    refresh_token: str
    scopes: ...
    user_id: str

    def __getattr__(self, attr: str) -> Any:
        return self[attr]
