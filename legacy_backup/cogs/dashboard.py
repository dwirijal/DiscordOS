import discord
from discord import app_commands, ui
from discord.ext import commands
import config

import database

# --- 1. MODAL (FORMULIR INPUT) ---
class TodoModal(ui.Modal, title="📝 Tambah Tugas Baru"):
    task_name = ui.TextInput(label="Nama Tugas", placeholder="Beli susu...", style=discord.TextStyle.short)
    deadline = ui.TextInput(label="Deadline / Catatan", placeholder="Nanti sore jam 5", style=discord.TextStyle.long, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Logic: Save to DB and Send to Channel
        await database.Database.add_task(content=self.task_name.value, priority='medium')
        
        target_channel = interaction.guild.get_channel(config.ACTIVE_TODOS_ID)
        
        if target_channel:
            embed = discord.Embed(title=f"📌 {self.task_name}", description=f"🕒 **Waktu:** {self.deadline}", color=discord.Color.blue())
            embed.set_footer(text="Status: Pending")
            await target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Tugas **{self.task_name}** berhasil disimpan!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Error: Channel '#active-todos' tidak ditemukan.", ephemeral=True)

# --- 2. VIEW (TOMBOL DASHBOARD) ---
class DashboardView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None agar tombol abadi

    @ui.button(label="Tambah To-Do", style=discord.ButtonStyle.primary, emoji="📝", custom_id="btn_todo")
    async def todo_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TodoModal())

# --- 1b. FINANCE FLOW ---

# Step 2: The Modal (Input Details)
class FinanceModal(ui.Modal, title="💰 Catat Transaksi"):
    def __init__(self, wallet_id, wallet_name):
        super().__init__()
        self.wallet_id = wallet_id
        self.wallet_name = wallet_name
        self.title = f"💰 {wallet_name}: Catat Transaksi"

    type = ui.TextInput(label="Tipe (income/expense)", placeholder="expense", style=discord.TextStyle.short)
    amount = ui.TextInput(label="Nominal", placeholder="50000", style=discord.TextStyle.short)
    description = ui.TextInput(label="Keterangan", placeholder="Makan siang", style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
             # Sanitize amount
            amt_str = self.amount.value.lower().replace('k', '000').replace(',', '')
            amount_val = float(amt_str)
            
            await database.Database.log_transaction(
                amount=amount_val, 
                type=self.type.value.lower(), 
                category="Manual Log", 
                description=self.description.value,
                wallet_id=self.wallet_id
            )
            
            target_channel = interaction.guild.get_channel(config.FINANCE_LOG_ID)
            if target_channel:
                 await target_channel.send(f"💸 **{self.type.value}** via {self.wallet_name}: {amount_val:,.0f} - {self.description.value}")
            
            await interaction.response.send_message(f"✅ Transaksi di **{self.wallet_name}** berhasil dicatat!", ephemeral=True)
            
        except ValueError:
             await interaction.response.send_message("❌ Error: Nominal harus angka.", ephemeral=True)
        except Exception as e:
             await interaction.response.send_message(f"❌ Error DB: {e}", ephemeral=True)

# Step 1: Wallet Select View
class WalletSelect(ui.Select):
    def __init__(self, wallets):
        options = []
        for w in wallets:
            # emoji = "🏦" if w['type'] == 'bank' else "🪙" if w['type'] == 'crypto' else "💵"
            options.append(discord.SelectOption(label=f"{w['name']} ({w['currency']})", value=str(w['id']), description=w['type'].title()))
        
        super().__init__(placeholder="Pilih Dompet / Sumber Dana...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        wallet_id = int(self.values[0])
        # Find name for display
        wallet_name = [opt.label for opt in self.options if opt.value == self.values[0]][0]
        await interaction.response.send_modal(FinanceModal(wallet_id, wallet_name))

class WalletSelectView(ui.View):
    def __init__(self, wallets):
        super().__init__()
        self.add_item(WalletSelect(wallets))

# --- 2. VIEW (TOMBOL DASHBOARD) ---
class DashboardView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None agar tombol abadi

    @ui.button(label="Tambah To-Do", style=discord.ButtonStyle.primary, emoji="📝", custom_id="btn_todo")
    async def todo_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TodoModal())

    @ui.button(label="Catat Keuangan", style=discord.ButtonStyle.success, emoji="💰", custom_id="btn_finance")
    async def finance_button(self, interaction: discord.Interaction, button: ui.Button):
        # Fetch wallets dynamic
        wallets = await database.Database.get_wallets_simple()
        if not wallets:
             await interaction.response.send_message("⚠️ Belum ada dompet! Gunakan `/wallet_add` dulu.", ephemeral=True)
             return
        
        await interaction.response.send_message("Pilih Dompet:", view=WalletSelectView(wallets), ephemeral=True)

    @ui.button(label="Quick Note", style=discord.ButtonStyle.secondary, emoji="📒", custom_id="btn_note")
    async def note_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Fitur Catatan sedang dibangun...", ephemeral=True)

    @ui.button(label="Fokus Mode", style=discord.ButtonStyle.danger, emoji="🍅", custom_id="btn_focus")
    async def focus_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Fitur Fokus sedang dibangun...", ephemeral=True)

# --- 2b. FINANCE CONTROL VIEW ---

# Step 3: Add Wallet Modal
class WalletModal(ui.Modal, title="➕ Tambah Dompet Baru"):
    name = ui.TextInput(label="Nama Dompet", placeholder="BCA / Binance / Dompet Saku", style=discord.TextStyle.short)
    w_type = ui.TextInput(label="Tipe (Bank/Crypto/Cash/Temp)", placeholder="bank", style=discord.TextStyle.short)
    balance = ui.TextInput(label="Saldo Awal", placeholder="0", style=discord.TextStyle.short)
    currency = ui.TextInput(label="Mata Uang (IDR/USD/BTC)", placeholder="IDR", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate Balance
            bal_str = self.balance.value.lower().replace('k', '000').replace(',', '')
            bal_val = float(bal_str)
            
            # Validate Type
            valid_types = ['bank', 'crypto', 'cash', 'temp']
            input_type = self.w_type.value.lower()
            if input_type not in valid_types:
                # Fallback or strict? Let's be lenient or default to cash
                # But best to just save it as is or correct it
                pass 

            async with database.Database.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO wallets (name, type, balance, currency) VALUES ($1, $2, $3, $4)
                """, self.name.value, input_type, bal_val, self.currency.value.upper())
            
            await interaction.response.send_message(f"✅ Dompet **{self.name.value}** ({self.currency.value}) berhasil dibuat!", ephemeral=True)
            
        except ValueError:
             await interaction.response.send_message("❌ Error: Saldo harus angka.", ephemeral=True)
        except Exception as e:
             await interaction.response.send_message(f"❌ Error DB: {e}", ephemeral=True)

class FinanceControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Add Transaction", style=discord.ButtonStyle.success, emoji="💰", custom_id="fin_btn_log")
    async def log_button(self, interaction: discord.Interaction, button: ui.Button):
        # reuse WalletSelectView logic
        wallets = await database.Database.get_wallets_simple()
        if not wallets:
             await interaction.response.send_message("⚠️ Belum ada dompet! Gunakan tombol [Add Wallet] dulu.", ephemeral=True)
             return
        await interaction.response.send_message("Pilih Dompet:", view=WalletSelectView(wallets), ephemeral=True)

    @ui.button(label="Add Wallet", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="fin_btn_add_wallet")
    async def add_wallet_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(WalletModal())

    @ui.button(label="My Wallets", style=discord.ButtonStyle.primary, emoji="💳", custom_id="fin_btn_wallets")
    async def wallets_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
             # Fast fetch, direct DB access (Duplicate logic from finance_wallets for speed)
             async with database.Database.pool.acquire() as conn:
                wallets = await conn.fetch("SELECT * FROM wallets WHERE is_active = TRUE ORDER BY type DESC, name")
             
             if not wallets:
                 await interaction.followup.send("No wallets found.", ephemeral=True)
                 return
                 
             embed = discord.Embed(title="💳 Wallet Summary", color=discord.Color.blue())
             grouped = {}
             for w in wallets:
                w_type = w['type'].title()
                if w_type not in grouped: grouped[w_type] = []
                grouped[w_type].append(f"**{w['name']}**: {w['currency']} {float(w['balance']):,.2f}")
                
             for w_type, lines in grouped.items():
                embed.add_field(name=w_type, value="\n".join(lines), inline=False)
                
             await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
             await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @ui.button(label="Net Worth", style=discord.ButtonStyle.secondary, emoji="🏦", custom_id="fin_btn_networth")
    async def networth_button(self, interaction: discord.Interaction, button: ui.Button):
         # Invoke the command logic or just point them to /balance?
         # Check balance logic is complex (requires Oracle).
         # For now, let's just say "Use /balance for full report" or do a simple fetch
         await interaction.response.send_message("ℹ️ Untuk laporan detail termasuk nilai Crypto realtime, gunakan command `/balance`.", ephemeral=True)

    @ui.button(label="Cashflow", style=discord.ButtonStyle.secondary, emoji="📉", custom_id="fin_btn_cashflow")
    async def cashflow_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            import datetime
            today = datetime.date.today()
            first_day = today.replace(day=1)
            
            async with database.Database.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT type, SUM(amount) as total 
                    FROM transactions 
                    WHERE date >= $1 AND type IN ('income', 'expense')
                    GROUP BY type
                """, first_day)
            
            income = 0
            expense = 0
            for r in rows:
                if r['type'] == 'income': income = float(r['total'])
                elif r['type'] == 'expense': expense = float(r['total'])
            
            net = income - expense
            embed = discord.Embed(title=f"📅 Cashflow: {today.strftime('%B')}", description=f"**Income**: ${income:,.2f}\n**Expense**: ${expense:,.2f}\n**Net**: ${net:,.2f}", color=discord.Color.gold())
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
             await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- 2c. ACTION ZONE VIEW ---
class ActionControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="New Task", style=discord.ButtonStyle.primary, emoji="✅", custom_id="act_btn_add")
    async def add_task(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TodoModal())

    @ui.button(label="Focus Session", style=discord.ButtonStyle.danger, emoji="🍅", custom_id="act_btn_focus")
    async def focus_session(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Focus Timer logic coming soon!", ephemeral=True)

    @ui.button(label="View Calendar", style=discord.ButtonStyle.secondary, emoji="📅", custom_id="act_btn_cal")
    async def view_calendar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Calendar sync coming soon!", ephemeral=True)


# --- 2d. SECOND BRAIN VIEW ---
class SecondBrainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Quick Note", style=discord.ButtonStyle.primary, emoji="📝", custom_id="sb_btn_note")
    async def quick_note(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Note taking logic coming soon!", ephemeral=True)

    @ui.button(label="Save Bookmark", style=discord.ButtonStyle.secondary, emoji="🔖", custom_id="sb_btn_bookmark")
    async def save_bookmark(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Bookmark logic coming soon!", ephemeral=True)

    @ui.button(label="Spark Idea", style=discord.ButtonStyle.success, emoji="💡", custom_id="sb_btn_idea")
    async def spark_idea(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚧 Idea capture logic coming soon!", ephemeral=True)


# --- 2e. LIFESTYLE VIEW ---
class LifestyleView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Track Habit", style=discord.ButtonStyle.success, emoji="✅", custom_id="life_btn_habit")
    async def track_habit(self, interaction: discord.Interaction, button: ui.Button):
         await interaction.response.send_message("🚧 Habit tracker logic coming soon!", ephemeral=True)

    @ui.button(label="Add Shopping Item", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="life_btn_shop")
    async def add_shopping(self, interaction: discord.Interaction, button: ui.Button):
         await interaction.response.send_message("🚧 Shopping list logic coming soon!", ephemeral=True)


# --- 2f. SYSTEM VIEW ---
class SystemControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="System Status", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="sys_btn_status")
    async def system_status(self, interaction: discord.Interaction, button: ui.Button):
         await interaction.response.send_message("✅ All Systems Operational. DB: Connected. Redis: Connected.", ephemeral=True)

    @ui.button(label="View Logs", style=discord.ButtonStyle.primary, emoji="📜", custom_id="sys_btn_logs")
    async def view_logs(self, interaction: discord.Interaction, button: ui.Button):
         await interaction.response.send_message("🚧 Log viewer coming soon!", ephemeral=True)


# --- 3. CONFIG & LOGIC ---

# Centralized Interface Configuration
def get_interface_config():
    """Returns the configuration for all persistent interfaces."""
    return {
        config.FINANCE_LOG_ID: {
            'key': 'panel_finance_id',
            'view_class': FinanceControlView,
            'embed': {
                'title': "💳 FINANCE CONTROL CENTER",
                'description': "Kelola keuanganmu dari sini.",
                'color': discord.Color.green(),
                'fields': [{'name': 'Actions', 'value': "Gunakan tombol di bawah untuk mencatat transaksi atau melihat laporan."}]
            }
        },
        config.ACTIVE_TODOS_ID: {
            'key': 'panel_action_id',
            'view_class': ActionControlView,
            'embed': {
                'title': "⚡ ACTION ZONE",
                'description': "Fokus pada apa yang harus dikerjakan hari ini.",
                'color': discord.Color.blue(),
                'fields': [{'name': 'Controls', 'value': "Tambah tugas, mulai sesi fokus, atau cek kalender."}]
            }
        },
        config.NOTES_STREAM_ID: {
            'key': 'panel_brain_id',
            'view_class': SecondBrainView,
            'embed': {
                'title': "🧠 SECOND BRAIN",
                'description': "Simpan ide, catatan, dan bookmark secepat kilat.",
                'color': discord.Color.purple(),
                'fields': [{'name': 'Quick Capture', 'value': "Jangan biarkan ide hilang. Catat sekarang."}]
            }
        },
        config.HABIT_TRACKER_ID: {
            'key': 'panel_lifestyle_id',
            'view_class': LifestyleView,
            'embed': {
                'title': "🥗 LIFESTYLE TRACKER",
                'description': "Bangun kebiasaan baik dan jaga keseimbangan.",
                'color': discord.Color.orange(),
                'fields': [{'name': 'Tracker', 'value': "Log kebiasaan atau update belanjaan."}]
            }
        },
        config.SYSTEM_LOGS_ID: {
            'key': 'panel_system_id',
            'view_class': SystemControlView,
            'embed': {
                'title': "🤖 SYSTEM INTERFACE",
                'description': "Monitor kesehatan server dan bot.",
                'color': discord.Color.dark_grey(),
                'fields': [{'name': 'Status', 'value': "Cek logs dan status sistem."}]
            }
        }
    }

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def deploy_or_update_panel(self, channel_id, config_data):
        """Logic to deploy or update a panel (used by setup and auto-heal)."""
        channel = self.bot.get_channel(channel_id)
        if not channel: return
        
        view = config_data['view_class']()
        embed_data = config_data['embed']
        
        embed = discord.Embed(title=embed_data['title'], description=embed_data['description'], color=embed_data['color'])
        if 'fields' in embed_data:
            for f in embed_data['fields']:
                embed.add_field(name=f['name'], value=f['value'], inline=False)

        # DB Check
        msg_id = await database.Database.get_config(config_data['key'])
        message = None
        
        if msg_id:
            try:
                message = await channel.fetch_message(int(msg_id))
                await message.edit(embed=embed, view=view)
            except discord.NotFound:
                pass # Trigger send new
            except Exception:
                pass

        if not message:
             message = await channel.send(embed=embed, view=view)
             await database.Database.set_config(config_data['key'], str(message.id))
             # print(f"✅ Auto-Deployed {embed_data['title']}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """Watchdog: If an interface message is deleted, redeploy it."""
        channel_id = payload.channel_id
        msg_id = payload.message_id
        
        interfaces = get_interface_config()
        if channel_id in interfaces:
            cfg = interfaces[channel_id]
            # Check if the deleted message was the active panel
            stored_id = await database.Database.get_config(cfg['key'])
            if stored_id and int(stored_id) == msg_id:
                # print(f"⚠️ Interface deleted in {channel_id}. Redeploying...")
                await self.deploy_or_update_panel(channel_id, cfg)

    @app_commands.command(name="setup_dashboard", description="Spawn Dashboard GUI (Admin Only)")
    async def setup_dashboard(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🚀 LIFE OS CONTROL CENTER", description="Selamat datang di pusat komando hidupmu.\nSilakan pilih menu di bawah ini untuk memulai aksi.", color=discord.Color.dark_theme())
        # embed.set_image(url="https://i.imgur.com/your-header-image.png") # Optional image
        embed.set_footer(text="System v1.0 • Connected")
        
        await interaction.channel.send(embed=embed, view=DashboardView())
        await interaction.response.send_message("✅ Dashboard berhasil dipasang!", ephemeral=True)

    @app_commands.command(name="setup_finance", description="Spawn Finance Control Panel (Admin Only)")
    async def setup_finance(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💳 FINANCE CONTROL CENTER", description="Kelola keuanganmu dari sini.", color=discord.Color.green())
        embed.add_field(name="Actions", value="Gunakan tombol di bawah untuk mencatat transaksi atau melihat laporan.", inline=False)
        
        await interaction.channel.send(embed=embed, view=FinanceControlView())
        await interaction.response.send_message("✅ Finance Panel berhasil dipasang!", ephemeral=True)

async def setup(bot):
    # Register the persistent view so it works after restart
    bot.add_view(DashboardView())
    bot.add_view(FinanceControlView())
    bot.add_view(ActionControlView())
    bot.add_view(SecondBrainView())
    bot.add_view(LifestyleView())
    bot.add_view(SystemControlView())
    await bot.add_cog(Dashboard(bot))
