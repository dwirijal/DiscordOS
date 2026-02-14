import discord
from discord.ext import commands
from src.core.database import db
from src.core.memory import memory
from src.core.brain import brain
import time

class Assistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore own messages
        if message.author == self.bot.user:
            return

        # Check if mentioned or DM
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions
        
        if is_dm or is_mentioned:
            async with message.channel.typing():
                # 1. Save to Short-term Memory (Dragonfly)
                user_id = str(message.author.id)
                chat_key = f"chat:{user_id}"
                
                # Format: "User: Hello"
                new_entry = f"User: {message.content}"
                
                if db.dragonfly:
                    # Append to list, expire in 10 mins (600s)
                    await db.dragonfly.rpush(chat_key, new_entry)
                    await db.dragonfly.expire(chat_key, 600)
                    
                    # Retrieve last 10 messages for context
                    history_list = await db.dragonfly.lrange(chat_key, -10, -1)
                    history_text = "\n".join(history_list)
                else:
                    history_text = new_entry

                # 2. Recall Long-term Memory (Qdrant)
                vector = await brain.embed_content(message.content)
                qa_context = ""
                
                if vector:
                    # Search Qdrant
                    search_results = await memory.recall(query_vector=vector, limit=3)
                    
                    if search_results:
                        qa_context = "\nRelevant Knowledge:\n"
                        for res in search_results:
                            # Assuming payload has 'content' field
                            qa_context += f"- {res.payload.get('content', '')}\n"

                context = f"Short-term History:\n{history_text}\n{qa_context}"

                # 3. Think (Brain)
                # Clean prompt (remove mention)
                clean_content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
                
                response_text = await brain.think(
                    prompt=clean_content, 
                    model="gemini", # Default to Gemini
                    context=context
                )

                # 4. Reply
                # Split long messages if needed (Discord limit 2000)
                if len(response_text) > 2000:
                    for i in range(0, len(response_text), 2000):
                        await message.channel.send(response_text[i:i+2000])
                else:
                    await message.channel.send(response_text)

                # 5. Save Bot Response to Short-term Memory
                if db.dragonfly:
                    bot_entry = f"Assistant: {response_text}"
                    await db.dragonfly.rpush(chat_key, bot_entry)
                    await db.dragonfly.expire(chat_key, 600)

async def setup(bot):
    await bot.add_cog(Assistant(bot))
