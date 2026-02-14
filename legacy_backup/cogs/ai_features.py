import discord
from discord import app_commands
from discord.ext import commands
from services.ai_agent import ai_agent
import logging

class AIFeatures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Tanya sama Gemini AI (via n8n)")
    @app_commands.describe(question="Apa yang mau ditanyain?")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        
        # Context building
        context = {
            "channel_name": interaction.channel.name if interaction.channel else "Direct Message",
            "server_name": interaction.guild.name if interaction.guild else "DM",
            "author_roles": [r.name for r in interaction.user.roles] if hasattr(interaction.user, 'roles') else []
        }
        
        # Send to AI Agent
        response_text = await ai_agent.ask_n8n(
            user_id=str(interaction.user.id),
            username=interaction.user.name,
            query=question,
            context=context
        )
        
        # Formatting response (Split if too long)
        if len(response_text) > 2000:
            # Simple chunking for now
            chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
            for chunk in chunks:
                await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(response_text)

async def setup(bot):
    await bot.add_cog(AIFeatures(bot))
