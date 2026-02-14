import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def cleanup():
    print("🧹 Cleaning up Mock Redis Keys...")
    
    await database.Database.connect()
    
    # Keys to delete (The ones conflicting with Live Data)
    keys = ["price:BTC", "price:ETH", "price:SOL"]
    
    for k in keys:
        await database.Database.redis.delete(k)
        print(f"   Deleted {k}")
        
    print("✅ Cleanup Complete!")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
