import discord
from discord import app_commands
from discord.ext import commands
import database
import logging

logger = logging.getLogger('finance_wallets')

class WalletManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wallet_add", description="Add a new wallet (Bank, Crypto, Cash)")
    @app_commands.describe(name="Wallet Name", type="bank/crypto/cash/temp", balance="Initial Balance", currency="IDR/USD")
    @app_commands.choices(type=[
        app_commands.Choice(name="Bank", value="bank"),
        app_commands.Choice(name="Crypto", value="crypto"),
        app_commands.Choice(name="Cash", value="cash"),
        app_commands.Choice(name="Temp/Event", value="temp")
    ])
    @app_commands.describe(category="TradFi, CeFi, DeFi, Personal")
    @app_commands.choices(category=[
        app_commands.Choice(name="TradFi (Bank)", value="TradFi"),
        app_commands.Choice(name="CeFi (Exchange)", value="CeFi"),
        app_commands.Choice(name="DeFi (On-Chain)", value="DeFi"),
        app_commands.Choice(name="Personal (Cash)", value="Personal")
    ])
    @app_commands.describe(network="Network/Platform (EVM, SVM, BANK, CASH, etc)")
    @app_commands.choices(network=[
        app_commands.Choice(name="EVM (Eth/Base/Arb)", value="EVM"),
        app_commands.Choice(name="SVM (Solana)", value="SVM"),
        app_commands.Choice(name="Bitcoin", value="BITCOIN"),
        app_commands.Choice(name="Bank System", value="BANK"),
        app_commands.Choice(name="Physical Cash", value="CASH"),
        app_commands.Choice(name="Exchange (Binance/Bybit)", value="EXCHANGE"),
        app_commands.Choice(name="Move (Sui/Aptos)", value="MOVE"),
        app_commands.Choice(name="Dogecoin", value="DOGE")
    ])
    async def add_wallet(self, interaction: discord.Interaction, name: str, type: str, balance: float, 
                         currency: str = 'IDR', category: str = 'Personal', network: str = 'Unknown'):
        await interaction.response.defer()
        try:
            async with database.Database.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO wallets (name, type, balance, currency, category, network) 
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, name, type, balance, currency.upper(), category, network)
            
            await interaction.followup.send(f"✅ **Siap!** Dompet **{name}** udah jadi nih. ({category}/{network}). Isinya: {currency} {balance:,.2f}")
        except Exception as e:
            await interaction.followup.send(f"❌ **Yah, Gagal Bikin Dompet**: {e}")

    @app_commands.command(name="wallet_list", description="List all your wallets")
    async def list_wallets(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with database.Database.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM wallets WHERE is_active = TRUE ORDER BY category, network, name")
            
            if not rows:
                await interaction.followup.send("Dompet kamu masih kosong nih. Bikin dulu gih pake `/wallet_add`.")
                return

            embed = discord.Embed(title="🏛️ Portfolio Kamu", description="Ini daftar aset yang kamu punya, Kak:", color=discord.Color.blue())
            
            # Group by Category > Network
            grouped = {}
            
            for row in rows:
                cat = row['category']
                net = row['network']
                group_key = f"{cat} > {net}"
                
                if group_key not in grouped: grouped[group_key] = []
                
                # Format
                currency = row['currency']
                balance = row['balance']
                grouped[group_key].append(f"**{row['name']}**: {currency} {balance:,.2f}")
                
            for g_key, lines in grouped.items():
                embed.add_field(name=f"📂 {g_key}", value="\n".join(lines), inline=False)

            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error listing wallets: {e}")

    @app_commands.command(name="wallet_transfer", description="Transfer funds between wallets (Validated)")
    @app_commands.describe(from_id="Source Wallet ID (Check /wallet_list)", to_id="Dest Wallet ID", amount="Amount to Receive", fee="Transaction Fee (Deducted from Source)")
    async def transfer(self, interaction: discord.Interaction, from_id: int, to_id: int, amount: float, fee: float = 0.0):
        await interaction.response.defer()
        try:
            async with database.Database.pool.acquire() as conn:
                # Check Source
                src = await conn.fetchrow("SELECT id, balance, currency, name, category, network FROM wallets WHERE id = $1", from_id)
                if not src:
                    await interaction.followup.send("❌ Source wallet not found.")
                    return
                
                total_deduction = amount + fee
                
                if src['balance'] < total_deduction:
                    await interaction.followup.send(f"❌ **Waduh, Saldo Kurang!**\nDi **{src['name']}** cuma ada {src['balance']:,.2f} {src['currency']}. Eh butuhnya {total_deduction:,.2f} (termasuk fee). Isi dulu yuk!")
                    return

                # Check Dest
                dest = await conn.fetchrow("SELECT id, currency, name, category, network FROM wallets WHERE id = $1", to_id)
                if not dest:
                    await interaction.followup.send("❌ Destination wallet not found.")
                    return
                
                # Currency Check
                if src['currency'] != dest['currency']:
                    await interaction.followup.send(f"⚠️ **Mata Uang Beda!**\nAsal: `{src['currency']}`\nTujuan: `{dest['currency']}`\n\nGak bisa transfer langsung beda mata uang, Kak. Pake fitur `/trade` aja ya buat tuker aset!")
                    return

                # VALIDATION ENGINE
                from services.finance_validator import FinanceValidator
                is_valid, msg = FinanceValidator.validate_transfer(dict(src), dict(dest))
                if not is_valid:
                     await interaction.followup.send(f"🛡️ **Eits, Gak Bisa Transfer!**\n{msg}")
                     return

                # Atomic Transfer & Ledger
                async with conn.transaction():
                    # Deduct Source (Amount + Fee)
                    await conn.execute("UPDATE wallets SET balance = balance - $1 WHERE id = $2", total_deduction, from_id)
                    # Add Dest (Amount only)
                    await conn.execute("UPDATE wallets SET balance = balance + $1 WHERE id = $2", amount, to_id)
                    
                    # Log Transaction
                    tx_id = await conn.fetchval("""
                        INSERT INTO transactions (type, amount, currency, wallet_id, dest_wallet_id, description, category, fee)
                        VALUES ('transfer', $1, $2, $3, $4, $5, 'Transfer', $6)
                        RETURNING id
                    """, amount, src['currency'], from_id, to_id, f"Transfer from {src['name']} to {dest['name']} (Fee: {fee})", fee)
                    
                    # Ledger Entries (Double Entry)
                    # Debit Dest (Increase Asset)
                    await conn.execute("""
                        INSERT INTO ledger (transaction_id, wallet_id, debit, credit)
                        VALUES ($1, $2, $3, 0)
                    """, tx_id, to_id, amount) 
                    
                    # Credit Source (Decrease Asset = Total Outflow)
                    await conn.execute("""
                        INSERT INTO ledger (transaction_id, wallet_id, debit, credit)
                        VALUES ($1, $2, 0, $3)
                    """, tx_id, from_id, total_deduction)

            embed = discord.Embed(title="✅ Uang Berhasil Dikirim!", color=discord.Color.green())
            embed.add_field(name="📤 Dari", value=f"**{src['name']}**\n`{src['category']}`", inline=True)
            embed.add_field(name="📥 Ke", value=f"**{dest['name']}**\n`{dest['category']}`", inline=True)
            embed.add_field(name="💰 Jumlah", value=f"{amount:,.2f} {src['currency']}", inline=False)
            if fee > 0:
                embed.add_field(name="📉 Admin Fee", value=f"{fee:,.2f} {src['currency']}", inline=True)
                embed.set_footer(text=f"Total Kepotong: {total_deduction:,.2f} {src['currency']}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Transfer Error: {e}")
            await interaction.followup.send("❌ **Waduh, Error Nih!** Sistem lagi gangguan, coba lagi nanti ya.")

async def setup(bot):
    await bot.add_cog(WalletManagement(bot))
