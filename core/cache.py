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

import datetime
from collections.abc import ItemsView, Iterator
from types import MappingProxyType
from typing import Any, overload

from twitchio.utils import MISSING

from .exceptions import CacheFullError, KeyExpiredError


__all__ = ("TTLCache",)


class TTLCache[K, V]:
    _cache: dict[K, V]
    _times: dict[K, datetime.datetime]

    def __init__(self, max_size: int = MISSING, ttl: int | datetime.timedelta = 600, data: dict[K, V] | None = None) -> None:
        self._initial_update(data)

        self._max_size = max_size
        self._cache: dict[K, V] = {}
        self._times: dict[K, datetime.datetime] = {}
        self._ttl: datetime.timedelta = ttl if isinstance(ttl, datetime.timedelta) else datetime.timedelta(seconds=ttl)

    def _initial_update(self, data: dict[K, V] | None = None) -> None:
        if not data:
            self._cache = {}
            self._times = {}
            return

        now = datetime.datetime.now(tz=datetime.UTC)
        self._cache.update(data)
        self._times.update({k: now for k in self._cache})

    def __repr__(self) -> str:
        return f"TTLCache(max_size={self._max_size}, ttl={self._ttl.total_seconds()})"

    def __str__(self) -> str:
        return str(self.items())

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def ttl(self) -> datetime.timedelta:
        return self._ttl

    def _check_cache(self) -> None:
        cache_copy = self._cache.copy()
        now = datetime.datetime.now(tz=datetime.UTC)

        for k in cache_copy:
            dt = self._times.get(k, None)

            if dt and dt + self._ttl <= now:
                self._cache.pop(k, None)
                self._times.pop(k, None)

    def _check_expiry(self, key: K) -> bool:
        self._check_cache()
        return key in self._times

    def items(self) -> ItemsView[K, V]:
        self._check_cache()
        return MappingProxyType(self._cache).items()

    @overload
    def get(self, key: K) -> V | None: ...

    @overload
    def get(self, key: K, default: None) -> V | None: ...

    def get[DT](self, key: K, default: DT | None = None) -> DT | V | None:
        result = self._cache.get(key, MISSING)
        if result is MISSING:
            return default

        if not self._check_expiry(key):
            return default

        return result

    def __contains__(self, key: K) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def __iter__(self) -> Iterator[K]:
        return iter(self._cache)

    def __getitem__(self, key: K) -> V:
        result = self._cache[key]
        if not self._check_expiry(key):
            raise KeyExpiredError(f"The key '{key}' has expired.")

        return result

    def __setitem__(self, key: K, value: V) -> None:
        if self._max_size is not MISSING and len(self) >= self._max_size:
            raise CacheFullError(f"The cache has reached the max size of {self._max_size} items.")

        self._cache[key] = value
        self._times[key] = datetime.datetime.now(tz=datetime.UTC)

    def __delitem__(self, key: K) -> None:
        self._cache.pop(key, None)
        self._times.pop(key, None)

    def as_json(self) -> list[dict[str, Any]]:
        to_return: list[dict[str, Any]] = []

        for k, v in self._cache.items():
            inner: dict[str, Any] = {}
            key = str(k)

            value = str(v) if not isinstance(v, (str, int, float, bool)) and v is not None else v

            inner[key] = value
            to_return.append(inner)

        return to_return
