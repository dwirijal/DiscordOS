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

guide_content = """
# 🏛️ Personal Life OS - User Guide

Welcome to your new **Personal Life Operating System**. This server is designed to act as a second brain, managing your tasks, finances, and knowledge through a clean GUI interface.

---

## 🏁 1. The Control Station
This is where everything starts. You barely need to type anything.

### `#🎛️・main-dashboard`
*   **What is it?** The Command Center.
*   **How to use:** Click the buttons to trigger actions.
    *   **📝 Add Task**: Opens a form to create a new To-Do.
    *   **💰 Log Money**: (Coming Soon) Log income/expenses.
    *   **📒 Quick Note**: (Coming Soon) Save a thought.
    *   **🍅 Focus Mode**: (Coming Soon) Start a Pomodoro timer.
*   *Note: You cannot type in this channel. It is for buttons only.*

### `#📥・quick-dump`
*   **What is it?** The "Inbox" for your brain.
*   **How to use:** Type *anything* here. The bot will sort it.
    *   **Tasks**: Start with `todo`, `buy`, `task`, `remember`.
        *   *Example:* "Buy milk tomorrow" -> Moves to `#📝・active-todos`
    *   **Finance**: Type an amount with `k` or currency.
        *   *Example:* "50k lunch" -> Moves to `#💰・finance-log`
    *   **Notes**: Anything else.
        *   *Example:* "Idea for new app..." -> Moves to `#📒・notes-stream`

---

## ⚡ 2. The Action Zone
Where work gets done.

### `#📝・active-todos`
*   **Content:** Cards (Embeds) of your pending tasks.
*   **Source:** Populated from the Dashboard button or `#quick-dump`.

### `#📅・agenda-calendar` / `#🍅・focus-session`
*   Reserved for future calendar sync and focus timer logs.

---

## 🧠 3. Second Brain & Knowledge
Your digital storage.

### `#📒・notes-stream`
*   Raw stream of notes captured from `#quick-dump`.

### `#🔖・bookmarks`
*   Paste links here. (Future: Bot will auto-summarize).

### `#🚀・active-projects` (Forum)
*   Create a new **Post** for each major project you are working on. Keep discussions threaded.

---

## 💎 4. Lifestyle & Data
Tracking your life metrics.

### `#💰・finance-log`
*   Shows a log of all transactions entered via Quick Dump or Dashboard.

### `#🥗・habit-tracker`
*   (Coming Soon) Daily checklist for habits.

---

## 🛠️ System & Settings
*   `#🤖・system-logs`: Watch here for bot errors or status updates.
*   `#🧪・dev-playground`: Test new commands here.

---

**💡 Pro Tip:**
If you ever get lost, come back to this channel (`#walkthrough`). This message will be updated as new features are added.
"""

async def create_walkthrough():
    await client.wait_until_ready()
    guild = client.get_guild(int(GUILD_ID))
    
    if not guild:
       print("Error: Guild not found.")
       return

    # Check/Create Channel
    channel_name = "walkthrough"
    channel = discord.utils.get(guild.text_channels, name=channel_name)

    if not channel:
        # Create at top level (no category)
        try:
            channel = await guild.create_text_channel(channel_name, position=0)
            print(f"Created channel: #{channel_name}")
        except Exception as e:
            print(f"Failed to create channel: {e}")
            return
    else:
        print(f"Found existing channel: #{channel_name}")

    # Clear channel content to ensure clean slate (Optional, but requested "1 message")
    # await channel.purge(limit=10) 
    # Actually, user said "saved 1 message for us to update", implies we might want to keep the same message ID if it exists?
    # But for a script run, it's easier to send a new one or edit the last one.
    # Let's just send a new one for now as this is a setup script.
    
    embed = discord.Embed(
        title="📘 Personal Life OS Manual", 
        description=guide_content,
        color=discord.Color.teal()
    )
    
    msg = await channel.send(embed=embed)
    await msg.pin()
    print("✅ Guide posted and pinned.")
    
    await client.close()

@client.event
async def on_ready():
    await create_walkthrough()

client.run(TOKEN)
