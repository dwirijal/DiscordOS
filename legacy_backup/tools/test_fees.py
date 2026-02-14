import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database

async def test_fees():
    print("🚀 Testing Transfer Fees...")
    
    await database.Database.connect()
    
    # 1. Setup Test Wallets using raw SQL to avoid needing Discord Interaction context
    async with database.Database.pool.acquire() as conn:
        # Create Source (Bank)
        w_src = await conn.fetchval("""
            INSERT INTO wallets (name, type, balance, currency, category, network)
            VALUES ('Test Bank Src', 'bank', 1000.00, 'USD', 'TradFi', 'BANK')
            RETURNING id
        """)
        
        # Create Dest (Exchange) - Must be distinct to avoid self-transfer issues (though logic allows)
        w_dst = await conn.fetchval("""
            INSERT INTO wallets (name, type, balance, currency, category, network)
            VALUES ('Test Exchange Dst', 'crypto', 0.00, 'USD', 'CeFi', 'EXCHANGE')
            RETURNING id
        """)
        
        print(f"   CREATED Wallets: Src (ID {w_src}, $1000), Dst (ID {w_dst}, $0)")

        # 2. Execute Transfer Logic (Simulating command)
        amount = 100.0
        fee = 5.0
        total_deduction = amount + fee
        
        # Transaction Context
        async with conn.transaction():
            # Deduct Src
            await conn.execute("UPDATE wallets SET balance = balance - $1 WHERE id = $2", total_deduction, w_src)
            # Add Dst
            await conn.execute("UPDATE wallets SET balance = balance + $1 WHERE id = $2", amount, w_dst)
            
            # Log
            tx_id = await conn.fetchval("""
                INSERT INTO transactions (type, amount, currency, wallet_id, dest_wallet_id, description, fee)
                VALUES ('transfer', $1, 'USD', $2, $3, 'Test Transfer', $4)
                RETURNING id
            """, amount, w_src, w_dst, fee)
            
            # Ledger
            # Debit Dest ($100)
            await conn.execute("INSERT INTO ledger (transaction_id, wallet_id, debit, credit) VALUES ($1, $2, $3, 0)", tx_id, w_dst, amount)
            # Credit Source ($105)
            await conn.execute("INSERT INTO ledger (transaction_id, wallet_id, debit, credit) VALUES ($1, $2, 0, $3)", tx_id, w_src, total_deduction)

        # 3. Verification
        bal_src = await conn.fetchval("SELECT balance FROM wallets WHERE id = $1", w_src)
        bal_dst = await conn.fetchval("SELECT balance FROM wallets WHERE id = $1", w_dst)
        
        print(f"   POST-TRANSFER: Src ${bal_src:,.2f} (Expected $895.00), Dst ${bal_dst:,.2f} (Expected $100.00)")
        
        if float(bal_src) == 895.0 and float(bal_dst) == 100.0:
            print("   ✅ Balances Correct.")
        else:
            print("   ❌ Balances Incorrect!")

        # Verify Ledger
        ledger_entries = await conn.fetch("SELECT * FROM ledger WHERE transaction_id = $1 ORDER BY id", tx_id)
        print("   Checking Ledger Entries:")
        for l in ledger_entries:
            print(f"      - Wallet {l['wallet_id']}: Debit {l['debit']}, Credit {l['credit']}")
        
        # Cleanup
        await conn.execute("DELETE FROM ledger WHERE transaction_id = $1", tx_id)
        await conn.execute("DELETE FROM transactions WHERE id = $1", tx_id)
        await conn.execute("DELETE FROM wallets WHERE id IN ($1, $2)", w_src, w_dst)
        print("   🧹 Cleanup Complete.")

    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(test_fees())
