import os
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in environment variables")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

class DiscordOSClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        # Don't respond to ourselves
        if message.author.id == self.user.id:
            return

        if message.content.startswith('!ping'):
            await message.channel.send('Pong!')

client = DiscordOSClient(intents=intents)

if __name__ == "__main__":
    client.run(TOKEN)
