import discord
from discord.ext import commands, tasks
import psutil
import platform
import time
import os

class Monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor_channel_id = None
        self.monitor_message = None
        self.server_stats.start()

    def cog_unload(self):
        self.server_stats.cancel()

    @commands.command(name="monitor")
    @commands.is_owner()
    async def set_monitor(self, ctx):
        """Set current channel as the server monitor channel"""
        self.monitor_channel_id = ctx.channel.id
        await ctx.send(f"✅ Monitor set to this channel. Updates every 15s.")
        # Force immediate update
        if self.monitor_message:
            try:
                await self.monitor_message.delete()
            except:
                pass
            self.monitor_message = None

    @tasks.loop(seconds=15)
    async def server_stats(self):
        if not self.monitor_channel_id:
            return

        channel = self.bot.get_channel(self.monitor_channel_id)
        if not channel:
            return

        # 1. Gather Metrics
        cpu_percent = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 2. Build Embed
        embed = discord.Embed(title="🖥️ Server Vital Constants", color=discord.Color.blue())
        embed.set_footer(text=f"Updated: {time.strftime('%H:%M:%S')} | OS: {platform.system()} {platform.release()}")
        
        # CPU Bar
        cpu_bar = self.make_bar(cpu_percent)
        embed.add_field(name=f"CPU: {cpu_percent}%", value=f"`{cpu_bar}`", inline=False)
        
        # RAM Bar
        ram_percent = ram.percent
        ram_bar = self.make_bar(ram_percent)
        ram_used_gb = round(ram.used / (1024**3), 2)
        ram_total_gb = round(ram.total / (1024**3), 2)
        embed.add_field(name=f"RAM: {ram_used_gb}GB / {ram_total_gb}GB ({ram_percent}%)", value=f"`{ram_bar}`", inline=False)

        # Disk
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_total_gb = round(disk.total / (1024**3), 2)
        embed.add_field(name="Storage (Root)", value=f"{disk_used_gb}GB / {disk_total_gb}GB ({disk.percent}%)", inline=True)

        # 3. Update or Send Message
        if self.monitor_message:
            try:
                await self.monitor_message.edit(embed=embed)
            except discord.NotFound:
                self.monitor_message = await channel.send(embed=embed)
        else:
            self.monitor_message = await channel.send(embed=embed)

    def make_bar(self, percent, length=20):
        filled_length = int(length * percent // 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return bar

    @server_stats.before_loop
    async def before_server_stats(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Monitor(bot))
