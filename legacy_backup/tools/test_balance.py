import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database
from services.fin_oracle import oracle

async def test_balance():
    print("🚀 Testing Balance Calculation...")
    
    await database.Database.connect()
    
    async with database.Database.pool.acquire() as conn:
        wallets = await conn.fetch("SELECT * FROM wallets WHERE is_active = TRUE ORDER BY type DESC, name")
        
    total_usd = 0
    grouped = {}
    
    print("\n--- WALLET BREAKDOWN ---")
    
    for w in wallets:
        w_type = w['type'].title()
        if w_type not in grouped: grouped[w_type] = []
        
        balance = float(w['balance'])
        currency = w['currency']
        usd_val = balance
        
        exchange_rate = 1.0
        
        if currency == 'IDR':
            exchange_rate = 1 / 15500
            usd_val = balance * exchange_rate
        elif currency != 'USD':
            price = await oracle.get_price(currency)
            if price:
                exchange_rate = price
                usd_val = balance * price
            else:
                print(f"⚠️ No price for {currency}")
                usd_val = 0
                
        total_usd += usd_val
        print(f"[{w_type}] {w['name']}: {balance:,.2f} {currency} @ ${exchange_rate:,.4f} = ${usd_val:,.2f}")

    print(f"\n💰 Total Net Worth: ${total_usd:,.2f}")
    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(test_balance())
