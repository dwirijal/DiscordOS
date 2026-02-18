import discord
from discord.ext import commands, tasks
from discord import app_commands
import psutil
import platform
import time
import socket
import aiohttp
import datetime

class Monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel_id = None
        self.system_check_loop.start()

    def cog_unload(self):
        self.system_check_loop.cancel()

    @app_commands.command(name="system", description="Show real-time system status")
    async def system_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await self.get_system_embed()
        await interaction.followup.send(embed=embed)

    @commands.command(name="set_alert_channel")
    @commands.is_owner()
    async def set_alert_channel(self, ctx):
        """Set current channel for system alerts"""
        self.alert_channel_id = ctx.channel.id
        await ctx.send(f"✅ System alerts will be sent to {ctx.channel.mention}")

    async def get_public_ip(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org') as resp:
                    return await resp.text()
        except:
            return "Unknown"

    async def get_system_embed(self):
        # 1. Gather Metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        
        # Network
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        public_ip = await self.get_public_ip()
        
        # Ping (google.com)
        ping_ms = "N/A"
        try:
            st = time.time()
            # Simple connect check
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            ping_ms = round((time.time() - st) * 1000, 2)
        except:
            pass

        # DNS (Simulated check by resolving a domain)
        dns_server = "System Default"
        try:
            # On Linux/Unix we can try to read /etc/resolv.conf
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        dns_server = line.split()[1]
                        break
        except:
            pass

        embed = discord.Embed(title="🖥️ System Status", color=discord.Color.blue())
        embed.timestamp = datetime.datetime.now()

        # Time
        now_ts = int(time.time())
        embed.add_field(name="🕒 Time", value=f"<t:{now_ts}:F> (<t:{now_ts}:R>)", inline=False)

        # Vital Stats
        embed.add_field(name="CPU Usage", value=f"**{cpu_percent}%**", inline=True)
        embed.add_field(name="RAM Usage", value=f"**{ram.percent}%** ({round(ram.used/1024**3, 1)}/{round(ram.total/1024**3, 1)} GB)", inline=True)
        embed.add_field(name="Disk Usage", value=f"**{disk.percent}%** ({round(disk.used/1024**3, 1)}/{round(disk.total/1024**3, 1)} GB)", inline=True)

        # Network
        net_info = (
            f"**Hostname:** `{hostname}`\n"
            f"**Local IP:** `{local_ip}`\n"
            f"**Public IP:** `{public_ip}`\n"
            f"**Ping (8.8.8.8):** `{ping_ms}ms`\n"
            f"**DNS Server:** `{dns_server}`"
        )
        embed.add_field(name="🌐 Network", value=net_info, inline=False)

        embed.set_footer(text=f"OS: {platform.system()} {platform.release()} | Uptime since: {boot_time.strftime('%Y-%m-%d %H:%M')}")
        return embed

    @tasks.loop(minutes=1)
    async def system_check_loop(self):
        # Alert Logic
        if not self.alert_channel_id:
            return

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        alerts = []
        if cpu > 90: alerts.append(f"🔥 **High CPU Load:** {cpu}%")
        if ram > 90: alerts.append(f"💾 **High RAM Usage:** {ram}%")
        if disk > 90: alerts.append(f"📀 **Low Disk Space:** {disk}% Used")

        if alerts:
            channel = self.bot.get_channel(self.alert_channel_id)
            if channel:
                await channel.send("⚠️ **SYSTEM ALERT** ⚠️\n" + "\n".join(alerts))

    @system_check_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Monitor(bot))
