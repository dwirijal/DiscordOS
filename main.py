import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from src.core.database import db
from src.core.memory import memory

load_dotenv()

# Setup Intents (Hak akses bot)
intents = discord.Intents.default()
intents.message_content = True # Wajib agar bisa baca chat

class DiscordOS(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="os.", intents=intents, help_command=None)

    async def setup_hook(self):
        # 1. Connect ke Database saat bot start
        print("🔗 Connecting to Neural Network...")
        await db.connect()
        await memory.initialize()
        
        # 2. Load Cogs (Fitur)
        await self.load_extension("src.cogs.assistant")
        await self.load_extension("src.cogs.ingestion")
        await self.load_extension("src.cogs.system")
        await self.load_extension("src.cogs.monitor")
        await self.load_extension("src.cogs.health")
        await self.load_extension("src.cogs.rss")

        # 3. Sync Slash Commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"❌ Command Sync Error: {e}")
        
        print("🚀 DiscordOS Kernel Online")

    async def close(self):
        # Tutup koneksi database saat bot mati
        await db.close()
        await super().close()

bot = DiscordOS()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your_token_here":
        print("❌ Error: DISCORD_TOKEN not set in .env")
    else:
        try:
            bot.run(token)
        except Exception as e:
            print(f"❌ Boot Error: {e}")
