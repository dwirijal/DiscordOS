import discord
from discord.ext import commands
from discord import app_commands
from src.core.brain import brain
from src.core.database import db
from src.core.memory import memory
import io
import PIL.Image
import re

class Health(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    fit_group = app_commands.Group(name="fit", description="Health and Fitness Tracking")

    @fit_group.command(name="face", description="Analyze face for health recommendations")
    async def face(self, interaction: discord.Interaction, photo: discord.Attachment):
        await interaction.response.defer(thinking=True)

        # Check if valid image
        if not photo.content_type or not photo.content_type.startswith("image/"):
            await interaction.followup.send("❌ Please upload a valid image.")
            return

        try:
            image_bytes = await photo.read()
            image = PIL.Image.open(io.BytesIO(image_bytes))

            prompt = """
            Analyze this selfie for health indicators (skin quality, fatigue signs, hydration, etc).
            Based on the analysis, provide brief recommendations for:
            1. Meal/Nutrition
            2. Skincare
            3. Rest/Sleep
            4. Supplements
            Keep it concise and actionable.
            """

            # Brain thinking with image
            analysis = await brain.think(prompt=prompt, images=[image])

            # Save to DB
            data = {"analysis": analysis, "image_url": photo.url}
            await db.log_health_data(interaction.user.id, "face_check", data)

            # Save to Memory (Vector Store)
            vector = await brain.embed_content(analysis)
            if vector:
                await memory.remember(
                    user_id=interaction.user.id,
                    vector=vector,
                    payload={"type": "face_check", "content": analysis, "url": photo.url}
                )

            embed = discord.Embed(title="🧬 Face Health Analysis", description=analysis, color=discord.Color.green())
            embed.set_thumbnail(url=photo.url)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error analyzing face: {e}")

    @fit_group.command(name="weight", description="Log and track weight")
    async def weight(self, interaction: discord.Interaction, amount: float = None, photo: discord.Attachment = None):
        await interaction.response.defer(thinking=True)

        weight_val = amount
        analysis = ""

        try:
            if photo:
                if not photo.content_type or not photo.content_type.startswith("image/"):
                     await interaction.followup.send("❌ Please upload a valid image.")
                     return

                image_bytes = await photo.read()
                image = PIL.Image.open(io.BytesIO(image_bytes))

                # Extract weight from image
                prompt = "Read the weight value from this scale display. Return ONLY the number (e.g. 70.5). If not clear, return '0'."
                weight_text = await brain.think(prompt=prompt, images=[image])

                try:
                    # Clean up response to get float
                    match = re.search(r"(\d+(\.\d+)?)", weight_text)
                    if match:
                        weight_val = float(match.group(1))
                    else:
                        weight_val = 0.0
                except:
                    weight_val = 0.0

            if weight_val is None or weight_val <= 0:
                await interaction.followup.send("❌ Could not determine weight. Please provide `amount` or a clear photo.")
                return

            # Analyze/Encourage
            prompt = f"The user weighs {weight_val} kg. Give a very short, encouraging 1-sentence comment."
            comment = await brain.think(prompt=prompt) # Text only

            # Save
            data = {"weight": weight_val, "comment": comment}
            await db.log_health_data(interaction.user.id, "weight", data)

            embed = discord.Embed(title="⚖️ Weight Logged", description=f"**{weight_val} kg**\n\n_{comment}_", color=discord.Color.blue())
            if photo: embed.set_thumbnail(url=photo.url)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error logging weight: {e}")

    @fit_group.command(name="nutrition", description="Analyze meal nutrition")
    async def nutrition(self, interaction: discord.Interaction, text: str = None, photo: discord.Attachment = None):
        if not text and not photo:
             await interaction.response.send_message("❌ Please provide text or a photo of your meal.", ephemeral=True)
             return

        await interaction.response.defer(thinking=True)

        try:
            analysis = ""
            image_url = None

            if photo:
                if not photo.content_type or not photo.content_type.startswith("image/"):
                     await interaction.followup.send("❌ Please upload a valid image.")
                     return
                image_bytes = await photo.read()
                image = PIL.Image.open(io.BytesIO(image_bytes))
                image_url = photo.url

                prompt = f"Analyze this meal image. Estimate calories and macros (Protein, Carbs, Fat). Is it healthy? {text if text else ''}"
                analysis = await brain.think(prompt=prompt, images=[image])
            else:
                # Text only -> Qwen (if configured) or Gemini
                prompt = f"Analyze this meal: {text}. Estimate calories and macros."
                # Use Qwen if strictly text
                analysis = await brain.think(prompt=prompt, model="qwen")

            # Save
            data = {"analysis": analysis, "input": text, "image_url": image_url}
            await db.log_health_data(interaction.user.id, "nutrition", data)

            # Memory
            vector = await brain.embed_content(analysis)
            if vector:
                await memory.remember(
                    interaction.user.id,
                    vector,
                    {"type": "nutrition", "content": analysis}
                )

            embed = discord.Embed(title="🍎 Nutrition Analysis", description=analysis, color=discord.Color.orange())
            if image_url: embed.set_thumbnail(url=image_url)
            await interaction.followup.send(embed=embed)

        except Exception as e:
             await interaction.followup.send(f"❌ Error analyzing nutrition: {e}")

    @fit_group.command(name="progress", description="Show health progress")
    @app_commands.choices(metric=[
        app_commands.Choice(name="Weight", value="weight"),
        app_commands.Choice(name="Face Health", value="face_check"),
        app_commands.Choice(name="Nutrition", value="nutrition")
    ])
    async def progress(self, interaction: discord.Interaction, metric: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True)

        real_metric = metric.value
        rows = await db.get_recent_health_logs(interaction.user.id, real_metric, limit=5)

        if not rows:
            await interaction.followup.send(f"📭 No data found for {metric.name}.")
            return

        text = ""
        for row in rows:
            date = row['created_at'].strftime("%Y-%m-%d %H:%M")
            data = row['data']

            if real_metric == "weight":
                val = data.get('weight', 'N/A')
                text += f"**{date}**: {val} kg\n"
            elif real_metric == "face_check":
                analysis = data.get('analysis', '')[:100].replace('\n', ' ') + "..."
                text += f"**{date}**: {analysis}\n"
            elif real_metric == "nutrition":
                analysis = data.get('analysis', '')[:100].replace('\n', ' ') + "..."
                text += f"**{date}**: {analysis}\n"

        embed = discord.Embed(title=f"📈 Progress: {metric.name}", description=text, color=discord.Color.purple())
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Health(bot))
