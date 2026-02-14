import discord
from discord.ext import commands
from discord import app_commands

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! 🏓 {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="info", description="About Personal Life OS")
    async def info(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🏛️ Personal Life OS", description="v1.0.0", color=discord.Color.blue())
        embed.add_field(name="Developer", value="Antigravity")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
