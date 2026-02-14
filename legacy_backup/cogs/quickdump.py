import discord
from discord.ext import commands
import config
import re

class QuickDump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id != config.QUICK_DUMP_ID:
            return

        content = message.content
        
        # Simple Regex Headers
        # Finance: "50k lunch" or "Rp 50000 lunch"
        finance_pattern = re.search(r'(\d+[kK]?)', content) 
        
        # Task: starts with "todo", "task", "buy"
        task_keywords = ["todo", "task", "buy", "need to", "remember"]
        is_task = any(content.lower().startswith(k) for k in task_keywords)

        if is_task:
            await self.process_task(message)
        elif finance_pattern and ("spent" in content.lower() or "paid" in content.lower() or "buy" in content.lower()):
             await self.process_finance(message)
        else:
            await self.process_note(message)

    async def process_task(self, message):
        await message.add_reaction("✅")
        # Forward to Active Todos
        target_channel = self.bot.get_channel(config.ACTIVE_TODOS_ID)
        if target_channel:
             await target_channel.send(f"**Task from Quick Dump:**\n{message.content}")

    async def process_finance(self, message):
        await message.add_reaction("💰")
        # Forward to Finance Log
        target_channel = self.bot.get_channel(config.FINANCE_LOG_ID)
        if target_channel:
            await target_channel.send(f"**Transaction:**\n{message.content}")

    async def process_note(self, message):
        await message.add_reaction("📝")
        # Forward to Notes Stream
        target_channel = self.bot.get_channel(config.NOTES_STREAM_ID)
        if target_channel:
            await target_channel.send(f"**Note:**\n{message.content}")

async def setup(bot):
    await bot.add_cog(QuickDump(bot))
