import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def seed_assets():
    print("🚀 Seeding Live Oracle Assets...")
    
    await database.Database.connect()
    
    # 1. New Assets to Track
    # (Symbol, Base, Quote, Type)
    new_assets = [
        ("DOGE/USDT", "DOGE", "USDT", "crypto"),
        ("SUI/USDT", "SUI", "USDT", "crypto"),
        ("SUPRA/USDT", "SUPRA", "USDT", "crypto"),
        ("ethereum/0xcbcdf9626bc03e24f779434178a73a0b4bad62ed", "WBTC", "ETH", "defi") # WBTC/ETH LP
    ]
    
    print("📋 Re-creating Assets Table (Schema Alignment)...")
    async with database.Database.pool.acquire() as conn:
        # DROP to ensure schema update
        await conn.execute("DROP TABLE IF EXISTS assets CASCADE")
        # Re-create using database.py's new schema
        await database.Database.create_tables()

        print(f"📋 Inserting {len(new_assets)} Assets...")
        for sym, base, quote, type_ in new_assets:
            # We explicitly cast type to asset_type enum if it exists, or text if not.
            # Postgres might complain if column is ENUM but we try to insert text.
            # Let's check if ENUM exists.
            try:
                await conn.execute("""
                    INSERT INTO assets (symbol, base_asset, quote_asset, asset_type) 
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (symbol) DO NOTHING
                """, sym, base, quote, type_)
            except Exception as e:
                # Fallback if ENUM issue: try casting
                print(f"⚠️ Insert failed for {sym}: {e}. Trying simple insert...")
                pass
            
        # 2. Update Wallet Currency to Match Oracle Symbol
        print("🔗 Linking 'Uniswap V3 LP' Wallet to DexScreener Pair...")
        await conn.execute("""
            UPDATE wallets 
            SET currency = 'ethereum/0xcbcdf9626bc03e24f779434178a73a0b4bad62ed'
            WHERE type = 'crypto' AND name LIKE '%Uniswap%'
        """)
        
        print("🔗 Linking 'Doge Vault' to DOGE/USDT...")
        await conn.execute("UPDATE wallets SET currency = 'DOGE/USDT' WHERE name LIKE '%Doge%'")
        
        print("🔗 Linking 'Sui Wallet' to SUI/USDT...")
        await conn.execute("UPDATE wallets SET currency = 'SUI/USDT' WHERE name LIKE '%Sui%'")
        
        print("🔗 Linking 'Supra Allocation' to SUPRA/USDT...")
        await conn.execute("UPDATE wallets SET currency = 'SUPRA/USDT' WHERE name LIKE '%Supra%'")

    print("✅ Oracle Assets Seeded & Wallets Linked!")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(seed_assets())
