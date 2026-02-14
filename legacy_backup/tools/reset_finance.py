import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def reset_finance():
    print("🗑️  Resetting Financial Data...")
    
    await database.Database.connect()
    
    try:
        async with database.Database.pool.acquire() as conn:
            # Order matters due to Foreign Keys
            # 1. Ledger (depends on Wallets & Transactions)
            await conn.execute("TRUNCATE TABLE ledger RESTART IDENTITY CASCADE")
            print("   ✅ Ledger Cleared.")
            
            # 2. Transactions (depends on Wallets)
            await conn.execute("TRUNCATE TABLE transactions RESTART IDENTITY CASCADE")
            print("   ✅ Transactions Cleared.")
            
            # 3. Wallets
            await conn.execute("TRUNCATE TABLE wallets RESTART IDENTITY CASCADE")
            print("   ✅ Wallets Cleared.")
            
        print("\n✨ Financial System Reset Complete! You can now start fresh.")
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")
    finally:
        await database.Database.close()

if __name__ == "__main__":
    asyncio.run(reset_finance())
