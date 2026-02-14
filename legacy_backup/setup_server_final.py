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
# intents.message_content = True  # Not strictly needed for setup but good practice
client = discord.Client(intents=intents)

async def setup_server():
    await client.wait_until_ready()
    print(f"Discord Version: {discord.__version__}")
    guild = client.get_guild(int(GUILD_ID))
    
    if not guild:
       print(f"Error: Could not find guild with ID {GUILD_ID}")
       await client.close()
       return

    print(f"Connected to guild: {guild.name}")
    
    # We already deleted channels, so we can just verify or create if missing
    # But for simplicity, let's just attempt to create the missing ones (Forum and Voice)
    # properly. The previous run crashed halfway.
    
    # Check if we need to delete again?
    # Let's just delete everything again to be clean, it's safer.
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
    categories = {
        "🏁 CONTROL STATION": ["🎛️・main-dashboard", "📥・quick-dump"],
        "⚡ ACTION ZONE": ["📝・active-todos", "📅・agenda-calendar", "🍅・focus-session"],
        # "📂 PROJECT MANAGEMENT": SPECIAL CASE (Forum)
        "🧠 SECOND BRAIN": ["📒・notes-stream", "🔖・bookmarks", "💡・ideas-spark"],
        "💎 LIFESTYLE & DATA": ["💰・finance-log", "🥗・habit-tracker", "🛒・shopping-list"],
        "🛠️ SYSTEM & STORAGE": ["🤖・system-logs", "📂・cloud-storage", "🧪・dev-playground"],
        # "🔊 AUDIO ZONE": SPECIAL CASE (Voice)
    }

    env_output = []

    # 1. Standard Categories
    for category_name, channels in categories.items():
        category = await guild.create_category(category_name)
        print(f"Created Category: {category_name}")
        
        for channel_name in channels:
            channel = await guild.create_text_channel(channel_name, category=category)
            print(f"  Created Channel: {channel_name} (ID: {channel.id})")
            
            # Format env variable name
            env_var = channel_name.split('・')[1].replace('-', '_').upper() + "_CHANNEL_ID"
            env_output.append(f"{env_var}={channel.id}")

    # 2. Project Management (Forum)
    pm_cat = await guild.create_category("📂 PROJECT MANAGEMENT")
    print("Created Category: 📂 PROJECT MANAGEMENT")
    
    try:
        if hasattr(guild, 'create_forum_channel'):
             forum = await guild.create_forum_channel("🚀・active-projects", category=pm_cat)
        else:
             print("create_forum_channel not found, trying create_channel with type=forum")
             forum = await guild.create_channel("🚀・active-projects", type=discord.ChannelType.forum, category=pm_cat)
             
        print(f"  Created Forum: 🚀・active-projects (ID: {forum.id})")
        env_output.append(f"ACTIVE_PROJECTS_CHANNEL_ID={forum.id}")
    except Exception as e:
        print(f"FAILED TO CREATE FORUM: {e}")
        # Fallback to text channel
        fallback = await guild.create_text_channel("🚀・active-projects-fallback", category=pm_cat)
        print(f"  Created Fallback Text Channel: {fallback.id}")
        env_output.append(f"ACTIVE_PROJECTS_CHANNEL_ID={fallback.id}")


    # 3. Audio Zone (Voice)
    audio_cat = await guild.create_category("🔊 AUDIO ZONE")
    print("Created Category: 🔊 AUDIO ZONE")
    
    vc1 = await guild.create_voice_channel("🎧・deep-focus", category=audio_cat)
    print(f"  Created Voice: 🎧・deep-focus (ID: {vc1.id})")
    env_output.append(f"DEEP_FOCUS_CHANNEL_ID={vc1.id}")
    
    vc2 = await guild.create_voice_channel("🗣️・voice-notes", category=audio_cat)
    print(f"  Created Voice: 🗣️・voice-notes (ID: {vc2.id})")
    env_output.append(f"VOICE_NOTES_CHANNEL_ID={vc2.id}")

    print("\n--- NEW CONFIGURATION ---")
    print("\n".join(env_output))
    
    # Write to a file for easy copying
    with open("final_channels.env", "w") as f:
        f.write("\n".join(env_output))
    
    print("\nConfiguration saved to final_channels.env")
    await client.close()

@client.event
async def on_ready():
    await setup_server()

client.run(TOKEN)
