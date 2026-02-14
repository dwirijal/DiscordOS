import discord
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

if not TOKEN or not GUILD_ID:
    print("Error: DISCORD_TOKEN or GUILD_ID not found in .env")
    exit(1)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def setup_server():
    await client.wait_until_ready()
    guild = client.get_guild(int(GUILD_ID))
    
    if not guild:
       print(f"Error: Could not find guild with ID {GUILD_ID}")
       await client.close()
       return

    print(f"Connected to guild: {guild.name}")
    print("WARNING: This will delete ALL channels and categories in 5 seconds. Press Ctrl+C to cancel.")
    await asyncio.sleep(5)

    print("DELETING CHANNELS...")
    for channel in guild.channels:
        try:
            await channel.delete()
            print(f"Deleted {channel.name}")
        except Exception as e:
            print(f"Failed to delete {channel.name}: {e}")

    print("CREATING STRUCTURE...")

    # Define structure
    structure = {
        "🏁 CONTROL STATION": ["🎛️・main-dashboard", "📥・quick-dump"],
        "⚡ ACTION ZONE": ["📝・active-todos", "📅・agenda-calendar", "🍅・focus-session"],
        "🧠 SECOND BRAIN": ["📒・notes-stream", "🔖・bookmarks", "💡・ideas-spark"],
        "💎 LIFESTYLE & DATA": ["💰・finance-log", "🥗・habit-tracker"]
    }

    env_output = []

    for category_name, channels in structure.items():
        category = await guild.create_category(category_name)
        print(f"Created Category: {category_name}")
        
        for channel_name in channels:
            channel = await guild.create_text_channel(channel_name, category=category)
            print(f"  Created Channel: {channel_name} (ID: {channel.id})")
            
            # Format env variable name
            env_var = channel_name.split('・')[1].replace('-', '_').upper() + "_CHANNEL_ID"
            env_output.append(f"{env_var}={channel.id}")

    print("\n--- NEW CONFIGURATION ---")
    print("\n".join(env_output))
    
    # Write to a file for easy copying
    with open("new_channels.env", "w") as f:
        f.write("\n".join(env_output))
    
    print("\nConfiguration saved to new_channels.env")
    await client.close()

@client.event
async def on_ready():
    await setup_server()

client.run(TOKEN)
