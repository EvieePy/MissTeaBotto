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

import twitchio
from twitchio.ext import commands, routines

import core


class AnimalsComponet(commands.Component):
    def __init__(self, bot: core.Bot) -> None:
        self.bot = bot
        self.cache = self.bot.stream_state["chatter_cache"]  #type: ignore [Reason: Added in bot __init__]
        
    async def component_teardown(self) -> None:
        self.check_chatters.cancel()

    async def component_load(self) -> None:
        assert self.bot.owner_id  # [Reason: I always provided the ID]
        self.check_chatters.start()
    
    @routines.routine(delta=datetime.timedelta(minutes=3))
    async def check_chatters(self) -> None:
        await self.bot.wait_until_ready()
        
        if not self.bot.stream_state.get("online", False):
            return
        
        assert self.bot.owner and self.bot.user
        chatters = await self.bot.owner.fetch_chatters(moderator=self.bot.user)

        async for chatter in chatters.users:
            self.cache[chatter.display_name or str(chatter)] = chatter
    
    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        self.bot.stream_state["online"] = True

    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        self.bot.stream_state["online"] = False

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        assert self.bot.user
        
        if payload.chatter.id == self.bot.user.id:
            return
        
        chatter = payload.chatter
        self.cache[chatter.display_name or str(chatter)] = chatter


async def setup(bot: core.Bot) -> None:
    await bot.add_component(AnimalsComponet(bot))
