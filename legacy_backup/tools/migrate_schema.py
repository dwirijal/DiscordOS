import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def migrate():
    print("🚀 Starting Schema Migration...")
    
    await database.Database.connect()
    
    async with database.Database.pool.acquire() as conn:
        print("🔧 Altering 'wallets.balance' to DECIMAL(32, 8)...")
        await conn.execute("ALTER TABLE wallets ALTER COLUMN balance TYPE DECIMAL(32, 8);")
        
        print("🔧 Altering 'transactions.amount' to DECIMAL(32, 8)...")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(32, 8);")
        
        print("🔧 Altering 'transactions.quantity' to DECIMAL(32, 8)...")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN quantity TYPE DECIMAL(32, 8);")

        print("🔧 Altering 'transactions.price_per_unit' to DECIMAL(32, 8)...")
        await conn.execute("ALTER TABLE transactions ALTER COLUMN price_per_unit TYPE DECIMAL(32, 8);")
        
    print("✅ Migration Complete!")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(migrate())
