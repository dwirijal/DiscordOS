import discord
from discord.ext import commands
from discord import app_commands
import datetime
from typing import Optional, List
from src.core.database import db
from src.core.google import google_manager

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init_google())

    async def init_google(self):
        await self.bot.wait_until_ready()
        await google_manager.initialize()

    # --- Autocomplete ---
    async def contact_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not current:
            return []

        # Call Google People API
        contacts = await google_manager.search_contacts(current)

        choices = []
        for c in contacts[:25]: # Limit 25 choices
            name = c['name']
            contact_id = c['id']
            # We store ID in value, but we need to handle it carefully
            # Ideally value is the ID, name is the Display Name
            choices.append(app_commands.Choice(name=name, value=contact_id))

        return choices

    async def account_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
        if not db.pg_pool: return []

        query = "SELECT id, name FROM accounts WHERE is_active = TRUE AND name ILIKE $1 LIMIT 25"
        async with db.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, f"%{current}%")
            return [app_commands.Choice(name=row['name'], value=row['id']) for row in rows]

    # --- Commands ---
    finance_group = app_commands.Group(name="finance", description="Manage Personal Finance")

    # /finance account add
    @finance_group.command(name="account_add", description="Add a new financial account")
    @app_commands.choices(type=[
        app_commands.Choice(name="Bank", value="bank"),
        app_commands.Choice(name="E-Wallet", value="ewallet"),
        app_commands.Choice(name="Cash", value="cash"),
        app_commands.Choice(name="Exchange", value="exchange"),
        app_commands.Choice(name="Crypto Wallet", value="wallet")
    ])
    async def account_add(self, interaction: discord.Interaction, name: str, type: app_commands.Choice[str], balance: float = 0.0):
        await interaction.response.defer()

        query = """
            INSERT INTO accounts (name, type, balance)
            VALUES ($1, $2, $3)
            RETURNING id
        """
        try:
            async with db.pg_pool.acquire() as conn:
                val = await conn.fetchval(query, name, type.value, balance)
                await interaction.followup.send(f"✅ Account Created: **{name}** ({type.value}) - ID: {val}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # /finance add income
    @finance_group.command(name="income", description="Record Income")
    @app_commands.autocomplete(account=account_autocomplete, from_contact=contact_autocomplete)
    async def add_income(self, interaction: discord.Interaction,
                         amount: float,
                         category: str,
                         account: int,
                         note: Optional[str] = None,
                         date: Optional[str] = None,
                         from_contact: Optional[str] = None): # this will be the contact ID if selected from autocomplete

        await self._add_transaction(interaction, "income", amount, category, account, note, date, from_contact)

    # /finance add expense
    @finance_group.command(name="expense", description="Record Expense")
    @app_commands.autocomplete(account=account_autocomplete, to_contact=contact_autocomplete)
    async def add_expense(self, interaction: discord.Interaction,
                          amount: float,
                          category: str,
                          account: int,
                          note: Optional[str] = None,
                          date: Optional[str] = None,
                          to_contact: Optional[str] = None):

        await self._add_transaction(interaction, "expense", amount, category, account, note, date, to_contact)

    async def _add_transaction(self, interaction: discord.Interaction, type: str, amount: float, category: str, account_id: int, note: str, date_str: str, contact_id_or_name: str):
        await interaction.response.defer()

        # Resolve Date
        tx_date = datetime.date.today()
        if date_str:
            try:
                tx_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                await interaction.followup.send("⚠️ Invalid Date Format. Using Today.")

        # Resolve Contact Name (if ID provided via autocomplete)
        contact_name = None
        contact_id = None

        if contact_id_or_name:
            if contact_id_or_name.startswith("people/"): # Google ID format
                contact_id = contact_id_or_name
                # Ideally we fetch name again, but for now we might store ID.
                # Or we can assume interaction.namespace would have the resolved name if we could access it?
                # People API get request to resolve name from ID would be best.
                # For Phase 1 speed, let's just mark it.
                contact_name = "Google Contact"
                # Try to resolve name from cache or just accept it might be displayed as ID in DB for now without a lookup helper
                # Let's add a quick lookup helper
                try:
                    if google_manager.service:
                        person = google_manager.service.people().get(resourceName=contact_id, personFields='names').execute()
                        contact_name = person.get('names', [{}])[0].get('displayName', 'Unknown Contact')
                except:
                    contact_name = contact_id # Fallback
            else:
                contact_name = contact_id_or_name # User typed a manual name

        async with db.pg_pool.acquire() as conn:
            async with conn.transaction():
                # 1. Insert Transaction
                query_tx = """
                    INSERT INTO transactions (account_id, type, amount, category, note, tx_date, contact_id, contact_name)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """
                await conn.execute(query_tx, account_id, type, amount, category, note, tx_date, contact_id, contact_name)

                # 2. Update Balance
                if type == "income":
                    query_bal = "UPDATE accounts SET balance = balance + $1 WHERE id = $2"
                else: # expense
                    query_bal = "UPDATE accounts SET balance = balance - $1 WHERE id = $2"

                await conn.execute(query_bal, amount, account_id)

                # Get Account Name for reply
                acc_name = await conn.fetchval("SELECT name FROM accounts WHERE id = $1", account_id)

        embed = discord.Embed(title=f"✅ {type.capitalize()} Recorded", color=discord.Color.green() if type == "income" else discord.Color.red())
        embed.add_field(name="Amount", value=f"{amount:,.2f}", inline=True)
        embed.add_field(name="Account", value=acc_name, inline=True)
        embed.add_field(name="Category", value=category, inline=True)
        if contact_name:
            embed.add_field(name="Contact", value=contact_name, inline=True)
        if note:
             embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=str(tx_date))

        await interaction.followup.send(embed=embed)

    # /finance config google
    @finance_group.command(name="config_google", description="Connect Google Account")
    async def config_google(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        url, error = google_manager.get_auth_url()
        if not url:
            await interaction.followup.send(error or "Unknown Error")
            return

        view = GoogleAuthView(url)
        await interaction.followup.send("Click the link to authorize, then paste the code below.", view=view, ephemeral=True)

class GoogleAuthModal(discord.ui.Modal, title="Google Auth Code"):
    code = discord.ui.TextInput(label="Paste Code Here", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success, msg = await google_manager.finish_auth(self.code.value)
        await interaction.followup.send(msg, ephemeral=True)

class GoogleAuthView(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(discord.ui.Button(label="🔗 Authorize Google", url=url))

    @discord.ui.button(label="🔑 Enter Code", style=discord.ButtonStyle.primary)
    async def enter_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GoogleAuthModal())

async def setup(bot):
    await bot.add_cog(Finance(bot))
