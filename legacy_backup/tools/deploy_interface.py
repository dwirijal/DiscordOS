import discord
import asyncio
import os
import sys

# Add parent directory to path to import config and cogs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from cogs.dashboard import (
    DashboardView, 
    FinanceControlView, 
    ActionControlView, 
    SecondBrainView, 
    LifestyleView, 
    SystemControlView
)
import database

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def deploy_panel(channel_id, embed_data, view, config_key):
    channel = client.get_channel(channel_id)
    if not channel:
        print(f"❌ Channel ID {channel_id} not found!")
        return

    print(f"Scanning Channel: {channel.name}...")
    
    embed = discord.Embed(title=embed_data['title'], description=embed_data['description'], color=embed_data['color'])
    if 'fields' in embed_data:
        for f in embed_data['fields']:
            embed.add_field(name=f['name'], value=f['value'], inline=False)
            
    # Logic:
    # 1. Try to get ID from DB
    # 2. If valid, use it.
    # 3. If invalid or missing, SCAN channel for bot's messages.
    # 4. If found, use the latest, delete others.
    # 5. If none, create new.

    msg_id = await database.Database.get_config(config_key)
    target_message = None
    
    # 1. Try DB
    if msg_id:
        try:
            target_message = await channel.fetch_message(int(msg_id))
        except discord.NotFound:
            print(f"⚠️ Saved Message ID {msg_id} not found in Discord.")
            target_message = None
        except Exception as e:
            print(f"⚠️ Error fetching saved message: {e}")
            target_message = None

    # 2. Scan if needed
    if not target_message:
        print(f"🔎 Scanning history for {channel.name}...")
        found_messages = []
        async for message in channel.history(limit=20):
            if message.author == client.user:
                found_messages.append(message)
        
        if found_messages:
            # Sort by date (newest first is default for history, but let's be safe)
            # Use the first one (latest) as target
            target_message = found_messages[0]
            print(f"✅ Found existing bot message (ID: {target_message.id})")
            
            # Save to DB
            await database.Database.set_config(config_key, str(target_message.id))
            
            # Delete older duplicates
            if len(found_messages) > 1:
                print(f"🧹 Deleting {len(found_messages) - 1} duplicate messages...")
                for old_msg in found_messages[1:]:
                    try:
                        await old_msg.delete()
                    except:
                        pass
        else:
            print("✨ No existing messages found.")

    # 3. Edit or Send
    if target_message:
        try:
            await target_message.edit(embed=embed, view=view)
            print(f"✅ {embed_data['title']} Updated (ID: {target_message.id})")
        except Exception as e:
             print(f"❌ Failed to edit message: {e}")
             # Fallback: Send new if edit fails hard?
    else:
        target_message = await channel.send(embed=embed, view=view)
        await database.Database.set_config(config_key, str(target_message.id))
        print(f"✅ {embed_data['title']} Sent New (ID: {target_message.id})")

@client.event
async def on_ready():
    print(f"Logged in as {client.user} for Deployment")
    
    # Initialize DB (Required for kv_store)
    import database
    await database.Database.connect()

    # Define Deployments using Centralized Config
    from cogs.dashboard import get_interface_config
    interfaces = get_interface_config()
    
    for channel_id, cfg in interfaces.items():
        # Map config format to deploy_panel format
        # cfg: {'key', 'view_class', 'embed'}
        # deploy_panel expects: channel_id, embed_data, view, config_key
        
        # Instantiate view
        view = cfg['view_class']()
        
        await deploy_panel(channel_id, cfg['embed'], view, cfg['key'])

    # 2. Deploy Main Dashboard (Legacy/Main)
    dash_channel = client.get_channel(config.MAIN_DASHBOARD_ID)
    if dash_channel:
        print(f"Found Dashboard Channel: {dash_channel.name}")
        embed = discord.Embed(title="🚀 LIFE OS CONTROL CENTER", description="Selamat datang di pusat komando hidupmu.\nSilakan pilih menu di bawah ini untuk memulai aksi.", color=discord.Color.dark_theme())
        embed.set_footer(text="System v1.0 • Connected")
        await dash_channel.send(embed=embed, view=DashboardView())
        print("✅ Main Dashboard Sent!")
    else:
        print(f"❌ Dashboard Channel ID {config.MAIN_DASHBOARD_ID} not found!")

    await client.close()

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found")
    else:
        client.run(config.DISCORD_TOKEN)
