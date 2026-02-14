import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def migrate_strict():
    print("🚀 Starting Strict Mode Migration...")
    
    await database.Database.connect()
    
    async with database.Database.pool.acquire() as conn:
        # 1. Schema Updates
        print("🔧 Updating 'wallets' schema...")
        await conn.execute("ALTER TABLE wallets ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'Personal';")
        await conn.execute("ALTER TABLE wallets ADD COLUMN IF NOT EXISTS network TEXT DEFAULT 'Unknown';")
        
        print("🔧 Creating 'ledger' table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER REFERENCES transactions(id),
                wallet_id INTEGER REFERENCES wallets(id),
                debit DECIMAL(32, 8) DEFAULT 0,
                credit DECIMAL(32, 8) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Backfill Logic
        print("🔄 Backfilling Wallet Metadata...")
        wallets = await conn.fetch("SELECT id, name, type FROM wallets")
        
        for w in wallets:
            w_id = w['id']
            name = w['name']
            w_type = w['type']
            
            category = "Personal"
            network = "Unknown"
            
            # Logic
            if "Bank" in name or "Savings" in name:
                category = "TradFi"
                network = "BANK"
            elif "GoPay" in name or "Cash" in name:
                category = "Personal"
                network = "CASH"
            elif "Binance" in name or "Exchange" in name:
                category = "CeFi"
                network = "EXCHANGE"
            elif w_type == "crypto":
                category = "DeFi"
                if "Bitcoin" in name: network = "BITCOIN"
                elif "Ethereum" in name or "Uniswap" in name: network = "EVM"
                elif "Solana" in name: network = "SVM"
                elif "Sui" in name: network = "MOVE"
                elif "Doge" in name: network = "DOGE"
                elif "Supra" in name: network = "SUPRA"
            
            await conn.execute(
                "UPDATE wallets SET category = $1, network = $2 WHERE id = $3",
                category, network, w_id
            )
            print(f"   -> {name}: {category} / {network}")

    print("✅ Strict Mode Migration Complete!")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(migrate_strict())
