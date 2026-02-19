import discord
from discord.ext import commands, tasks
from discord import app_commands
import feedparser
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from src.core.database import db
from src.core.brain import brain
from src.core.memory import memory
import datetime

class RSS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.feed_channel_id = None
        self.rss_loop.start()

    def cog_unload(self):
        self.rss_loop.cancel()

    @commands.command(name="set_rss_channel")
    @commands.is_owner()
    async def set_rss_channel(self, ctx):
        """Set current channel for RSS updates"""
        self.feed_channel_id = ctx.channel.id
        await ctx.send(f"✅ RSS updates will be posted in {ctx.channel.mention}")

    rss_group = app_commands.Group(name="rss", description="Manage RSS Feeds")

    @rss_group.command(name="add", description="Add a new RSS feed")
    async def add_feed(self, interaction: discord.Interaction, url: str, category: str = "general"):
        await interaction.response.defer()

        # Verify URL
        try:
            d = feedparser.parse(url)
            if d.bozo:
                # Some valid feeds trigger bozo (encoding issues), but if entries exist, it's usable
                if not d.entries:
                    await interaction.followup.send("⚠️ Invalid RSS Feed URL.")
                    return
            title = d.feed.get('title', url)
        except Exception as e:
            await interaction.followup.send(f"❌ Error parsing feed: {e}")
            return

        feed_id = await db.add_rss_feed(url, category)
        if feed_id:
            await interaction.followup.send(f"✅ Added feed: **{title}** ({category})")
        else:
            await interaction.followup.send(f"⚠️ Feed already exists or database error.")

    @rss_group.command(name="list", description="List all RSS feeds")
    async def list_feeds(self, interaction: discord.Interaction):
        feeds = await db.get_rss_feeds()
        if not feeds:
            await interaction.response.send_message("📭 No feeds configured.")
            return

        text = "\n".join([f"- {f['url']} ({f['category']})" for f in feeds])
        await interaction.response.send_message(f"**tracked Feeds:**\n{text}")

    async def fetch_full_content(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200: return None
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Heuristics to find main content (can be improved)
                    # Exclude header/footer/nav
                    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                        tag.extract()

                    paragraphs = soup.find_all('p')
                    text = " ".join([p.get_text() for p in paragraphs])
                    # Take first chunk that looks substantial
                    return text[:4000] # Limit context for AI
        except:
            return None

    @tasks.loop(minutes=15)
    async def rss_loop(self):
        if not self.feed_channel_id:
            return

        feeds = await db.get_rss_feeds()
        if not feeds: return

        channel = self.bot.get_channel(self.feed_channel_id)
        if not channel: return

        for feed in feeds:
            try:
                # Async fetch feed content first
                async with aiohttp.ClientSession() as session:
                    async with session.get(feed['url'], timeout=10) as resp:
                        if resp.status != 200: continue
                        content = await resp.text()

                d = feedparser.parse(content)

                # Check last 3 entries
                for entry in d.entries[:3]:
                    link = entry.get('link')
                    if not link: continue

                    # Check DB if processed
                    if await db.is_article_processed(link):
                        continue

                    # Process New Article
                    title = entry.get('title', 'No Title')
                    raw_summary = entry.get('summary', '')

                    # Try to fetch full content for better summarization
                    full_text = await self.fetch_full_content(link)
                    context_text = full_text if full_text else raw_summary

                    if not context_text: context_text = title

                    # AI Summarize
                    prompt = f"Summarize this news article in maximum 3 concise bullet points. Focus on the main event and economic/global impact. Title: {title}\nContent: {context_text}"

                    # Use default configured brain
                    ai_summary = await brain.think(prompt=prompt)

                    # Publish
                    embed = discord.Embed(title=title, url=link, description=ai_summary, color=discord.Color.gold())
                    embed.set_footer(text=f"Source: {d.feed.get('title', 'RSS')} | Cat: {feed['category']}")
                    await channel.send(embed=embed)

                    # Log to DB
                    await db.log_rss_article(feed['id'], link, title, ai_summary)

                    # Remember in Vector DB
                    vector = await brain.embed_content(f"{title} {ai_summary}")
                    if vector:
                         await memory.remember(
                            "system_rss", # System user
                            vector,
                            {"type": "news", "title": title, "summary": ai_summary, "url": link}
                         )

                    # Wait a bit to not spam/rate limit
                    await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ RSS Error ({feed['url']}): {e}")

    @rss_loop.before_loop
    async def before_rss(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RSS(bot))
