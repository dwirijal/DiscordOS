import discord
from discord.ext import commands
from src.core.memory import memory
from src.core.brain import brain
from qdrant_client.models import PointStruct
import uuid
import datetime

class Ingestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="memorize")
    async def memorize(self, ctx, *, content: str = None):
        """Save text or attached file content to Long-term Memory"""
        
        target_content = content
        
        # Handle Attachments (Text files only for now)
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.endswith(('.txt', '.md', '.py', '.json')):
                    try:
                        file_data = await attachment.read()
                        text_data = file_data.decode('utf-8')
                        if target_content:
                            target_content += f"\n\nFile: {attachment.filename}\n{text_data}"
                        else:
                            target_content = f"File: {attachment.filename}\n{text_data}"
                    except Exception as e:
                        await ctx.send(f"❌ Failed to read {attachment.filename}: {e}")
        
        if not target_content:
            await ctx.send("❓ Please provide text or a text file to memorize.")
            return

        async with ctx.typing():
            # 1. Embed Content
            vector = await brain.embed_content(target_content)
            
            if not vector:
                await ctx.send("❌ Failed to generate embedding.")
                return

            # 2. Store in Qdrant
            point_id = str(uuid.uuid4())
            payload = {
                "content": target_content,
                "author": str(ctx.author),
                "timestamp": datetime.datetime.now().isoformat(),
                "source": "discord_command"
            }
            
            try:
                await memory.client.upsert(
                    collection_name=memory.collection_name,
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=vector,
                            payload=payload
                        )
                    ]
                )
                await ctx.send(f"✅ Memorized! (ID: {point_id})")
            except Exception as e:
                await ctx.send(f"❌ Storage Error: {e}")

async def setup(bot):
    await bot.add_cog(Ingestion(bot))
