import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def seed():
    print("🚀 Starting Portfolio Seeder...")
    
    # 1. Connect
    await database.Database.connect()
    
    # 2. Define Wallets
    # (Name, Type, Balance, Currency)
    wallets = [
        ("Bitcoin Cold Storage", "crypto", 5, "BTC"),
        ("Ethereum Mainnet", "crypto", 2, "ETH"),
        ("Solana Phantom", "crypto", 5, "SOL"),
        ("Doge Vault", "crypto", 1231241, "DOGE"),
        ("Uniswap V3 LP (BTC/ETH)", "crypto", 2, "UNI-V3-BTC-ETH"),
        ("BRI Savings", "bank", 12432423, "IDR"),
        ("GoPay", "cash", 241231231, "IDR"),
        ("SeaBank", "bank", 12123123123, "IDR"),
        ("Binance Exchange", "crypto", 121231, "USDT"),
        ("Sui Wallet", "crypto", 12312, "SUI"),
        ("Supra Allocation", "crypto", 2323, "SUPRA")
    ]
    
    # 3. Clear & Insert Wallets
    print("🧹 Clearing Wallets Table...")
    async with database.Database.pool.acquire() as conn:
        await conn.execute("DELETE FROM wallets")
        
        print(f"🌱 Seeding {len(wallets)} Wallets...")
        for w in wallets:
            await conn.execute("""
                INSERT INTO wallets (name, type, balance, currency) 
                VALUES ($1, $2, $3, $4)
            """, *w)
            
    # 4. Seed Oracle Prices (Redis)
    # Mock prices for test
    print("📈 Seeding Mock Oracle Prices (Redis)...")
    prices = {
        "BTC": 98500,
        "ETH": 2750,
        "SOL": 195,
        "DOGE": 0.35,
        "SUI": 3.20,
        "SUPRA": 0.15,
        "UNI-V3-BTC-ETH": 15000,
        "USDT": 1.0,
        "IDR": 0 # Special case in logic
    }
    
    for sym, price in prices.items():
        if price > 0:
             key = f"price:{sym}"
             await database.Database.redis.set(key, str(price))
             print(f"   -> {sym}: ${price}")
             
    print("✅ Portfolio Seeded Successfully!")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(seed())
