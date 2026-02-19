import discord
from discord.ext import commands
from discord import app_commands
from src.core.database import db
from src.core.brain import brain

class OpenAIConfigModal(discord.ui.Modal, title="Configure OpenAI/Ollama"):
    base_url = discord.ui.TextInput(
        label="Base URL",
        placeholder="https://api.openai.com/v1 or http://localhost:11434/v1",
        default="http://localhost:11434/v1",
        required=True
    )
    api_key = discord.ui.TextInput(
        label="API Key",
        placeholder="sk-... (or 'ollama')",
        default="ollama",
        required=False
    )
    model_name = discord.ui.TextInput(
        label="Chat Model Name",
        placeholder="gpt-4o or qwen2.5:7b",
        default="qwen2.5:7b",
        required=True
    )
    embed_provider = discord.ui.TextInput(
        label="Embedding Provider (openai/gemini)",
        placeholder="openai",
        default="openai",
        required=True,
        max_length=10
    )
    embed_model = discord.ui.TextInput(
        label="Embedding Model Name",
        placeholder="text-embedding-3-small or nomic-embed-text",
        default="nomic-embed-text",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Save settings
        await db.set_setting("ai_provider", "openai")
        await db.set_setting("openai_base_url", self.base_url.value)
        await db.set_setting("openai_api_key", self.api_key.value or "ollama")
        await db.set_setting("openai_model", self.model_name.value)
        await db.set_setting("embed_provider", self.embed_provider.value)
        if self.embed_model.value:
            await db.set_setting("embed_model", self.embed_model.value)

        # Reload Brain
        await brain.reload()

        embed = discord.Embed(title="✅ AI Configuration Updated", color=discord.Color.green())
        embed.add_field(name="Provider", value="OpenAI/Ollama", inline=True)
        embed.add_field(name="Model", value=self.model_name.value, inline=True)
        embed.add_field(name="Base URL", value=self.base_url.value, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

class GeminiConfigModal(discord.ui.Modal, title="Configure Google Gemini"):
    api_key = discord.ui.TextInput(
        label="Gemini API Key",
        placeholder="AIza...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await db.set_setting("gemini_api_key", self.api_key.value)
        # Default embed provider to gemini if not set
        await db.set_setting("embed_provider", "gemini")

        await brain.reload()

        embed = discord.Embed(title="✅ Gemini Configuration Updated", color=discord.Color.green())
        embed.add_field(name="Provider", value="Google Gemini", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

class ProviderSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ollama / Local AI", description="Connect to local Ollama instance", emoji="🦙", value="ollama"),
            discord.SelectOption(label="OpenAI Compatible", description="OpenAI, Groq, DeepSeek, etc.", emoji="🤖", value="openai"),
            discord.SelectOption(label="Google Gemini", description="Use Google's Gemini API", emoji="✨", value="gemini"),
        ]
        super().__init__(placeholder="Select AI Provider...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] in ["ollama", "openai"]:
            settings = await db.get_all_settings()

            modal = OpenAIConfigModal()
            # Try to pre-fill from DB
            if settings.get("openai_base_url"):
                modal.base_url.default = settings.get("openai_base_url")
            if settings.get("openai_api_key"):
                modal.api_key.default = settings.get("openai_api_key")
            if settings.get("openai_model"):
                modal.model_name.default = settings.get("openai_model")
            if settings.get("embed_provider"):
                modal.embed_provider.default = settings.get("embed_provider")
            if settings.get("embed_model"):
                modal.embed_model.default = settings.get("embed_model")

            # Specific defaults for Ollama if empty
            if self.values[0] == "ollama" and modal.base_url.default == "http://localhost:11434/v1":
                 pass # Already default
            elif self.values[0] == "openai" and modal.base_url.default == "http://localhost:11434/v1":
                 modal.base_url.default = "https://api.openai.com/v1" # Reset to OpenAI default if switching

            await interaction.response.send_modal(modal)

        elif self.values[0] == "gemini":
            modal = GeminiConfigModal()
            await interaction.response.send_modal(modal)

class ConfigView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ProviderSelect())

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="System Configuration")

    @config_group.command(name="ai", description="Configure AI Provider and Models")
    async def config_ai(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ AI Configuration", description="Select a provider to configure connection details.", color=discord.Color.blue())

        # Show current config summary
        settings = await db.get_all_settings()

        active_provider = settings.get("ai_provider", "gemini")

        model_info = "N/A"
        provider_info = "Not Configured"

        if active_provider == "openai" and brain.qwen:
            provider_info = f"OpenAI/Ollama ({settings.get('openai_base_url', 'Unknown')})"
            model_info = settings.get("openai_model", "Unknown")
        elif brain.gemini:
             provider_info = "Google Gemini"
             model_info = "Gemini Flash 1.5"
        elif active_provider == "openai":
             provider_info = f"OpenAI/Ollama (Not Connected)"
             model_info = settings.get("openai_model", "Unknown")

        embed.add_field(name="Current Active Provider", value=provider_info, inline=False)
        embed.add_field(name="Current Chat Model", value=model_info, inline=True)
        embed.add_field(name="Embedding Provider", value=settings.get("embed_provider", "gemini"), inline=True)

        await interaction.response.send_message(embed=embed, view=ConfigView(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Configuration(bot))
