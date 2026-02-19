import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from typing import Optional, List
from src.core.database import db
from src.core.google import google_manager
from src.core.brain import brain

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init_google())
        self.monthly_report_task.start()

    def cog_unload(self):
        self.monthly_report_task.cancel()

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
        for c in contacts[:25]:
            name = c['name']
            contact_id = c['id']
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
        query = "INSERT INTO accounts (name, type, balance) VALUES ($1, $2, $3) RETURNING id"
        try:
            async with db.pg_pool.acquire() as conn:
                val = await conn.fetchval(query, name, type.value, balance)
                await interaction.followup.send(f"✅ Account Created: **{name}** ({type.value}) - ID: {val}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @finance_group.command(name="income", description="Record Income")
    @app_commands.autocomplete(account=account_autocomplete, from_contact=contact_autocomplete)
    async def add_income(self, interaction: discord.Interaction, amount: float, category: str, account: int, note: Optional[str] = None, date: Optional[str] = None, from_contact: Optional[str] = None):
        await self._add_transaction(interaction, "income", amount, category, account, note, date, from_contact)

    @finance_group.command(name="expense", description="Record Expense")
    @app_commands.autocomplete(account=account_autocomplete, to_contact=contact_autocomplete)
    async def add_expense(self, interaction: discord.Interaction, amount: float, category: str, account: int, note: Optional[str] = None, date: Optional[str] = None, to_contact: Optional[str] = None):
        await self._add_transaction(interaction, "expense", amount, category, account, note, date, to_contact)

    async def _add_transaction(self, interaction: discord.Interaction, type: str, amount: float, category: str, account_id: int, note: str, date_str: str, contact_id_or_name: str):
        await interaction.response.defer()
        tx_date = datetime.date.today()
        if date_str:
            try:
                tx_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                await interaction.followup.send("⚠️ Invalid Date Format. Using Today.")

        contact_name = None
        contact_id = None
        if contact_id_or_name:
            if contact_id_or_name.startswith("people/"):
                contact_id = contact_id_or_name
                contact_name = "Google Contact"
                try:
                    if google_manager.people_service:
                        person = google_manager.people_service.people().get(resourceName=contact_id, personFields='names').execute()
                        contact_name = person.get('names', [{}])[0].get('displayName', 'Unknown Contact')
                except:
                    contact_name = contact_id
            else:
                contact_name = contact_id_or_name

        async with db.pg_pool.acquire() as conn:
            async with conn.transaction():
                query_tx = """
                    INSERT INTO transactions (account_id, type, amount, category, note, tx_date, contact_id, contact_name)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """
                await conn.execute(query_tx, account_id, type, amount, category, note, tx_date, contact_id, contact_name)

                if type == "income":
                    query_bal = "UPDATE accounts SET balance = balance + $1 WHERE id = $2"
                else:
                    query_bal = "UPDATE accounts SET balance = balance - $1 WHERE id = $2"
                await conn.execute(query_bal, amount, account_id)
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

    @finance_group.command(name="config_google", description="Connect Google Account")
    async def config_google(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        url, error = google_manager.get_auth_url()
        if not url:
            await interaction.followup.send(error or "Unknown Error")
            return
        view = GoogleAuthView(url)
        await interaction.followup.send("Click the link to authorize, then paste the code below.", view=view, ephemeral=True)

    @finance_group.command(name="generate_report", description="Manually trigger monthly report generation")
    async def manual_report(self, interaction: discord.Interaction, month: int = None, year: int = None):
        await interaction.response.defer()

        now = datetime.datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        url = await self.generate_monthly_spreadsheet(target_month, target_year)
        if url:
             await interaction.followup.send(f"✅ Report generated for {target_month}/{target_year}: {url}")
        else:
             await interaction.followup.send(f"❌ Failed to generate report. Check logs/auth.")

    # --- Scheduler ---
    @tasks.loop(hours=24)
    async def monthly_report_task(self):
        now = datetime.datetime.now()
        # Trigger on the 28th of every month
        if now.day == 28:
            print(f"📅 Triggering Monthly Report for {now.strftime('%B %Y')}")
            await self.generate_monthly_spreadsheet(now.month, now.year)

    @monthly_report_task.before_loop
    async def before_report_task(self):
        await self.bot.wait_until_ready()

    # --- Logic ---
    async def generate_monthly_spreadsheet(self, month, year):
        if not google_manager.sheets_service:
            print("❌ Google Sheets Service not available")
            return None

        sheet_title = "Financial Reports"
        tab_title = f"{datetime.date(year, month, 1).strftime('%b %Y')}"

        # 1. Get Spreadsheet ID (Create or Find)
        spreadsheet_id = await db.get_setting("finance_spreadsheet_id")
        if not spreadsheet_id:
            spreadsheet_id = await google_manager.create_spreadsheet(sheet_title)
            if spreadsheet_id:
                await db.set_setting("finance_spreadsheet_id", spreadsheet_id)
            else:
                return None

        # 2. Add Tab
        sheet_id = await google_manager.add_sheet(spreadsheet_id, tab_title)
        if not sheet_id:
             # If tab exists, we might overwrite or skip. For now, let's assume we append/overwrite by logic of just writing
             # But we need the ID for formatting. Let's find it if add_sheet returned existing ID.
             # Actually add_sheet implementation returns ID even if exists.
             pass

        # 3. Gather Data
        start_date = datetime.date(year, month, 1)
        # End date logic
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1)
        else:
            end_date = datetime.date(year, month + 1, 1)

        # 3a. Transactions
        tx_rows = []
        async with db.pg_pool.acquire() as conn:
            txs = await conn.fetch("""
                SELECT tx_date, type, category, amount, contact_name, note, accounts.name as account_name
                FROM transactions
                JOIN accounts ON transactions.account_id = accounts.id
                WHERE tx_date >= $1 AND tx_date < $2
                ORDER BY tx_date ASC
            """, start_date, end_date)

            total_income = 0
            total_expense = 0

            for tx in txs:
                amount = float(tx['amount'])
                if tx['type'] == 'income':
                    total_income += amount
                else:
                    total_expense += amount

                tx_rows.append([
                    str(tx['tx_date']),
                    tx['type'],
                    tx['category'],
                    amount,
                    tx['account_name'],
                    tx['contact_name'] or "",
                    tx['note'] or ""
                ])

            # 3b. Balance Sheet (Current Snapshot)
            accounts = await conn.fetch("SELECT name, type, balance FROM accounts WHERE is_active = TRUE")
            balance_rows = [[a['name'], a['type'], float(a['balance'])] for a in accounts]
            total_assets = sum(r[2] for r in balance_rows if r[2] > 0)
            total_liabilities = sum(r[2] for r in balance_rows if r[2] < 0)

        # 4. Generate AI Insight
        prompt = f"""
        Analyze this financial month ({tab_title}).
        Total Income: {total_income}
        Total Expense: {total_expense}
        Net Cash Flow: {total_income - total_expense}
        Top Expenses Categories: (Can be inferred from raw data if needed, but summary is enough)

        Provide 3 bullet points of recommendations/observations.
        """
        ai_advice = await brain.think(prompt)

        # 5. Write to Sheet
        data = []

        # Header
        data.append([f"REPORT: {tab_title}"])
        data.append(["Generated on", str(datetime.datetime.now())])
        data.append([]) # Spacer

        # Cash Flow
        data.append(["CASH FLOW"])
        data.append(["Metric", "Value"])
        data.append(["Total Income", total_income])
        data.append(["Total Expense", total_expense])
        data.append(["Net Flow", total_income - total_expense])
        data.append([])

        # Balance Sheet
        data.append(["BALANCE SHEET"])
        data.append(["Account", "Type", "Balance"])
        data.extend(balance_rows)
        data.append(["Total Assets", total_assets])
        data.append([])

        # AI Recommendations
        data.append(["AI INSIGHTS"])
        data.append([ai_advice])
        data.append([])

        # Transaction Log
        data.append(["TRANSACTION LOG"])
        data.append(["Date", "Type", "Category", "Amount", "Account", "Contact", "Note"])
        data.extend(tx_rows)

        await google_manager.write_values(spreadsheet_id, f"'{tab_title}'!A1", data)

        # 6. Formatting (Bold Headers)
        # Headers are at Row 5 (Cash Flow), Row 11 (Balance Sheet - approx), etc.
        # This is hard to pinpoint dynamically without tracking row indices.
        # Minimal formatting: Header Row of Transaction Log.
        # Log starts at: 3 (Header) + 5 (Cash) + 1 + 2 + len(balance) + 1 + 2 (AI) + 1 + 2 = approx row...
        # Let's simple format row 1 for Title.
        await google_manager.format_header(spreadsheet_id, sheet_id, 0, 1, 0, 1)

        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

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
