import discord
from discord import app_commands
from discord.ext import commands
from services.fin_oracle import oracle
import database
import logging

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="price", description="Check the price of an asset (Crypto, Stock, Forex)")
    @app_commands.describe(symbol="The ticker symbol (e.g. BTC, AAPL, EURUSD)")
    async def price(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        
        try:
            price = await oracle.get_price(symbol)
            if price:
                embed = discord.Embed(title=f"💸 Harga {symbol.upper()} Update!", color=discord.Color.green())
                embed.add_field(name="Harga Sekarang", value=f"${price:,.2f}", inline=False)
                # embed.add_field(name="Source", value=source, inline=True) # Oracle returns simple price for now
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ **Waduh, Gak Ketemu!** Harga **{symbol}** lagi gak ada nih.")
        except Exception as e:
            await interaction.followup.send(f"❌ **Error Pas Cek Harga**: {e}")

    @app_commands.command(name="trade", description="Execute a Trade (Buy/Sell) between wallets")
    @app_commands.describe(type="Buy or Sell", pay_wallet_id="ID of Wallet YOU PAY FROM", receive_wallet_id="ID of Wallet YOU RECEIVE INTO", quantity="Amount of Asset to Receive/Sell", price="Price per unit")
    @app_commands.choices(type=[
        app_commands.Choice(name="Buy", value="buy"),
        app_commands.Choice(name="Sell", value="sell")
    ])
    async def trade(self, interaction: discord.Interaction, type: str, pay_wallet_id: int, receive_wallet_id: int, quantity: float, price: float = None):
        """
        Strict Mode Trade:
        - BUY: Pay from USDT Wallet -> Receive in BTC Wallet.
        - SELL: Pay from BTC Wallet -> Receive in USDT Wallet.
        """
        await interaction.response.defer()
        try:
             async with database.Database.pool.acquire() as conn:
                # 1. Fetch Wallets
                pay_w = await conn.fetchrow("SELECT * FROM wallets WHERE id = $1", pay_wallet_id)
                recv_w = await conn.fetchrow("SELECT * FROM wallets WHERE id = $1", receive_wallet_id)
                
                if not pay_w:
                    await interaction.followup.send("❌ Pay Wallet not found.")
                    return
                if not recv_w:
                    await interaction.followup.send("❌ Receive Wallet not found.")
                    return

                # 2. Determine Asset Symbol from Receive Wallet (or Pay Wallet if Sell? - Let's use logic below)
                target_asset = recv_w['currency']
                
                # Auto-fetch price if needed (using target asset)
                if price is None:
                    # If BUY, we value the Receive Asset. If SELL, we value the Pay Asset? 
                    # Convention: Price is usually Quote Currency (Pay Wallet Currency).
                    # Let's try to fetch price of the "Risk Asset".
                    # If Pay=USDT, Recv=BTC -> Price of BTC.
                    # If Pay=BTC, Recv=USDT -> Price of BTC.
                    
                    risk_asset = recv_w['currency'] if type == 'buy' else pay_w['currency']
                    price = await oracle.get_price(risk_asset)
                    if not price:
                        await interaction.followup.send(f"❌ Could not determine price for {risk_asset}. Please specify.")
                        return

                # 3. Calculate Totals
                # BUY: Pay [Total Cost] USDT -> Recv [Quantity] BTC
                # SELL: Pay [Quantity] BTC -> Recv [Total Value] USDT 
                # This logic is slightly ambiguous with just "quantity". 
                # Let's assume 'quantity' is ALWAYS the amount of the 'risk asset' being traded?
                # No, to match standard UX:
                # BUY: Quantity of ASSET (BTC). Cost = Qty * Price.
                # SELL: Quantity of ASSET (BTC). Proceeds = Qty * Price.
                # BUT user selects Wallets.
                
                # Let's simplify: Strict Double Entry does not care about "Buy/Sell" label as much as flows.
                # We adhere to: 
                # PAY WALLET decreases by (Cost).
                # RECV WALLET increases by (Proceeds).
                
                payment_amount = 0.0
                receive_amount = 0.0
                asset_symbol = ""
                
                if type == 'buy':
                    # Buying Receive Wallet's Asset.
                    # Qty = Amount of BTC to get.
                    # Pay = Qty * Price.
                    receive_amount = quantity
                    payment_amount = quantity * price
                    asset_symbol = recv_w['currency']
                else:
                    # Selling Pay Wallet's Asset.
                    # Qty = Amount of BTC to sell.
                    # Recv = Qty * Price.
                    payment_amount = quantity # Deduct BTC
                    receive_amount = quantity * price # Add USDT
                    asset_symbol = pay_w['currency']

                # 4. Check Balance
                if pay_w['balance'] < payment_amount:
                     await interaction.followup.send(f"❌ **Saldo Gak Cukup!**\nDi **{pay_w['name']}** cuma ada {pay_w['balance']:,.2f} {pay_w['currency']}. Butuhnya {payment_amount:,.2f}.")
                     return

                # 5. VALIDATOR
                from services.finance_validator import FinanceValidator
                # Validate the flow (Pay -> Recv)
                is_valid, msg = FinanceValidator.validate_transfer(dict(pay_w), dict(recv_w))
                if not is_valid:
                    await interaction.followup.send(f"⚠️ **Eits, Transaksi Ditolak!**\n{msg}")
                    return

                # 6. EXECUTE
                async with conn.transaction():
                    # Deduct Pay Wallet
                    await conn.execute("UPDATE wallets SET balance = balance - $1 WHERE id = $2", payment_amount, pay_wallet_id)
                    # Add Recv Wallet
                    await conn.execute("UPDATE wallets SET balance = balance + $1 WHERE id = $2", receive_amount, receive_wallet_id)
                    
                    # Log Transaction
                    tx_id = await conn.fetchval("""
                        INSERT INTO transactions (type, amount, currency, wallet_id, dest_wallet_id, description, category, asset_symbol, quantity, price_per_unit)
                        VALUES ($1, $2, $3, $4, $5, $6, 'Trade', $7, $8, $9)
                        RETURNING id
                    """, type, payment_amount, pay_w['currency'], pay_wallet_id, receive_wallet_id, 
                       f"{type.title()} {quantity} {asset_symbol} @ ${price}", asset_symbol, quantity, price)

                    # Ledger
                    # Debit Receive Wallet (Increase), Credit Pay Wallet (Decrease)
                    await conn.execute("""
                        INSERT INTO ledger (transaction_id, wallet_id, debit, credit)
                        VALUES ($1, $2, $3, 0)
                    """, tx_id, receive_wallet_id, receive_amount)
                    
                    await conn.execute("""
                        INSERT INTO ledger (transaction_id, wallet_id, debit, credit)
                        VALUES ($1, $2, 0, $3)
                    """, tx_id, pay_wallet_id, payment_amount)
                    
                embed = discord.Embed(title="🤝 Deal! Trade Berhasil", color=discord.Color.green())
                embed.add_field(name="Aksi", value=f"**{type.upper()}** {asset_symbol}", inline=True)
                embed.add_field(name="Harga @", value=f"${price:,.2f}", inline=True)
                embed.add_field(name="📉 Bayar Pake", value=f"{payment_amount:,.4f} {pay_w['currency']}\ndari {pay_w['name']}", inline=False)
                embed.add_field(name="📈 Dapatnya", value=f"{receive_amount:,.4f} {recv_w['currency']}\nmasuk {recv_w['name']}", inline=False)
                
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ **Yah, Trade Gagal**: {e}")

    @app_commands.command(name="portfolio", description="View your asset portfolio")
    async def portfolio(self, interaction: discord.Interaction):
        # Placeholder for portfolio logic
        # 1. Aggregate buy/sells from transactions
        # 2. Calculate average buy price
        # 3. Fetch current oracle price
        # 4. Calculate PnL
        await interaction.response.send_message("🚧 Portfolio features are coming soon! (Data is being logged)")

    @app_commands.command(name="balance", description="View Net Worth & Wallet Balances")
    async def balance(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with database.Database.pool.acquire() as conn:
                wallets = await conn.fetch("SELECT * FROM wallets WHERE is_active = TRUE ORDER BY type DESC, name")
            
            if not wallets:
                await interaction.followup.send("Belum ada dompet nih. Bikin dulu yuk!")
                return

            total_usd = 0
            breakdown = ""
            
            # Group by Type
            grouped = {}
            for w in wallets:
                w_type = w['type'].title()
                if w_type not in grouped: grouped[w_type] = []
                
                # Convert to USD (Approx)
                balance = float(w['balance'])
                currency = w['currency']
                usd_val = balance
                
                # Simple Oracle Conversion
                if currency == 'IDR':
                    usd_val = balance / 15500 # Static fallback or fetch oracle?
                elif currency != 'USD':
                    # Try fetch crypto price
                    price = await oracle.get_price(currency) # e.g. BTC
                    if price:
                        usd_val = balance * price
                
                total_usd += usd_val
                grouped[w_type].append(f"**{w['name']}**: {currency} {balance:,.2f} (~${usd_val:,.2f})")

            embed = discord.Embed(title="📊 Rekap Aset Kamu", description=f"Total Net Worth\n# 💰 ${total_usd:,.2f}", color=discord.Color.gold())
            
            for w_type, lines in grouped.items():
                embed.add_field(name=f"📂 {w_type}", value="\n".join(lines), inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="cashflow", description="Monthly Income vs Expense Report")
    async def cashflow(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Get First Day of Month
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
            color = discord.Color.green() if net >= 0 else discord.Color.red()
            
            embed = discord.Embed(title=f"📅 Laporan Bulan {today.strftime('%B %Y')}", color=color)
            embed.add_field(name="💸 Pemasukan", value=f"${income:,.2f}", inline=True)
            embed.add_field(name="🔥 Pengeluaran", value=f"${expense:,.2f}", inline=True)
            embed.add_field(name="📉 Sisa Duit", value=f"${net:,.2f}", inline=False)
            
            if expense > 0:
                burn_rate = expense / today.day
                embed.set_footer(text=f"🔥 Duit Kebakar: ${burn_rate:,.2f} / hari")
                
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Finance(bot))
