import discord
from discord.ext import commands
from src.core.database import db
from src.core.memory import memory
import time

class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check system latency and database connection status"""
        async with ctx.typing():
            # 1. Bot Latency
            latency = round(self.bot.latency * 1000)
            
            # 2. Database Checks
            db_status = "❌"
            cache_status = "❌"
            memory_status = "❌"
            
            # Postgres
            if db.pg_pool:
                try:
                    async with db.pg_pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                        db_status = "✅"
                except:
                    pass
            
            # Dragonfly
            if db.dragonfly:
                try:
                    if await db.dragonfly.ping():
                        cache_status = "✅"
                except:
                    pass

            # Qdrant
            if memory.client:
                try:
                    await memory.client.get_collections()
                    memory_status = "✅"
                except:
                    pass

            embed = discord.Embed(title="🧩 System Status", color=discord.Color.green())
            embed.add_field(name="Latency", value=f"`{latency}ms`", inline=True)
            embed.add_field(name="Uptime", value=f"<t:{int(self.start_time)}:R>", inline=True)
            embed.add_field(name="PostgreSQL", value=db_status, inline=True)
            embed.add_field(name="Dragonfly", value=cache_status, inline=True)
            embed.add_field(name="Qdrant", value=memory_status, inline=True)
            
            await ctx.send(embed=embed)

    @commands.command(name="wipe_memory", hidden=True)
    @commands.is_owner()
    async def wipe_memory(self, ctx):
        """Dangerous: Clear short-term memory (Dragonfly)"""
        if db.dragonfly:
            await db.dragonfly.flushdb()
            await ctx.send("💥 Short-term memory wiped.")
        else:
            await ctx.send("❌ Dragonfly not connected.")

async def setup(bot):
    await bot.add_cog(System(bot))
