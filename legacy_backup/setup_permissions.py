import discord
import os
import asyncio
from dotenv import load_dotenv
import config

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

if not TOKEN or not GUILD_ID:
    print("Error: DISCORD_TOKEN or GUILD_ID not found in .env")
    exit(1)

intents = discord.Intents.default()
intents.members = True # Need members intent to find owner
client = discord.Client(intents=intents)

async def setup_permissions():
    await client.wait_until_ready()
    guild = client.get_guild(int(GUILD_ID))
    
    if not guild:
       print(f"Error: Could not find guild with ID {GUILD_ID}")
       await client.close()
       return

    print(f"Connected to guild: {guild.name}")
    print("Beginning Permission Setup...")

    # 1. Create/Get Roles
    existing_roles = {role.name: role for role in guild.roles}
    
    # [BOT] Role
    if "[BOT]" in existing_roles:
        bot_role = existing_roles["[BOT]"]
        print("Role [BOT] exists.")
    else:
        bot_role = await guild.create_role(name="[BOT]", color=discord.Color.purple(), permissions=discord.Permissions.all())
        print("Created Role: [BOT]")
        
    # [OWNER] Role
    if "[OWNER]" in existing_roles:
        owner_role = existing_roles["[OWNER]"]
        print("Role [OWNER] exists.")
    else:
        owner_role = await guild.create_role(name="[OWNER]", color=discord.Color.gold())
        print("Created Role: [OWNER]")

    # Assign OWNER role to Guild Owner
    if guild.owner:
        await guild.owner.add_roles(owner_role)
        print(f"Assigned [OWNER] role to {guild.owner.name}")
    else:
        print("WARNING: Could not determine guild owner.")

    # Assign BOT role to Self
    me = guild.get_member(client.user.id)
    if me:
        await me.add_roles(bot_role)
        print(f"Assigned [BOT] role to {client.user.name}")


    # 2. Define Overwrites
    
    # Default Owner: View=True, Send=True
    owner_allow_all = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    
    # Locked Owner: View=True, Send=False
    owner_readonly = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
    
    # Everyone: View=False (Private Server)
    everyone_deny = discord.PermissionOverwrite(view_channel=False)

    channels_to_lock = [
        config.MAIN_DASHBOARD_ID,
        config.ACTIVE_TODOS_ID,
        config.FINANCE_LOG_ID,
        config.HABIT_TRACKER_ID
    ]

    print("APPLYING PERMISSIONS...")

    # Categories
    for category in guild.categories:
        await category.set_permissions(guild.default_role, overwrite=everyone_deny)
        await category.set_permissions(owner_role, overwrite=owner_allow_all)
        print(f"Secured Category: {category.name}")
        
    # Channels
    for channel in guild.channels:
        # Defaults inherited from category usually, but we force specific locks
        
        if channel.id in channels_to_lock:
            await channel.set_permissions(owner_role, overwrite=owner_readonly)
            print(f"🔒 LOCKED (Read-Only) for OWNER: {channel.name}")
        
    print("\n✅ Permission Setup Complete!")
    await client.close()

@client.event
async def on_ready():
    await setup_permissions()

client.run(TOKEN)
