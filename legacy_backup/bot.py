import discord
from discord.ext import commands
import os
import config
import database
from services.fin_oracle import oracle 

# Setup Intent
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ BOT IS ONLINE!')
    print(f'👤 Logged in as: {bot.user}')
    print('==================================================')
    
    # Initialize Database
    await database.Database.connect()
    
    # Load Cogs
    await load_extensions()
    
    # Sync Commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def load_extensions():
    # Only load files in ./cogs that end with .py
    if os.path.exists("./cogs"):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded: cogs.{filename[:-3]}")
                except Exception as e:
                    print(f"❌ Failed to load cogs.{filename[:-3]}: {e}")

@bot.event # Graceful Shutdown
async def on_close():
    await oracle.close()
    await database.Database.close()
    print("🛑 Bot Shutdown Complete")

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(config.DISCORD_TOKEN)
