import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database
from services.finance_validator import FinanceValidator

async def test_strict_mode():
    print("🚀 Testing Strict Mode...")
    
    await database.Database.connect()
    
    # 1. Verify Schema & Backfill
    print("\n🔍 Verifying Wallet Metadata...")
    # Fetch a known wallet
    btc_wallet = await database.Database.pool.fetchrow("SELECT * FROM wallets WHERE name LIKE '%Bitcoin Cold Storage%'")
    if btc_wallet:
        print(f"   ✅ Found Bitcoin Wallet: Cat={btc_wallet['category']}, Net={btc_wallet['network']}")
        if btc_wallet['category'] != 'DeFi' or btc_wallet['network'] != 'BITCOIN':
            print("   ❌ Backfill Incorrect!")
    else:
        print("   ⚠️ Bitcoin wallet not found (Check seeding)")

    # 2. Test Validator Logic (Unit Test)
    print("\n🛡️ Testing Validator Rules...")
    
    tradfi = {'name': 'BCA', 'category': 'TradFi', 'network': 'BANK'}
    cefi = {'name': 'Binance', 'category': 'CeFi', 'network': 'EXCHANGE'}
    defi_eth = {'name': 'Metamask', 'category': 'DeFi', 'network': 'EVM'}
    defi_sol = {'name': 'Phantom', 'category': 'DeFi', 'network': 'SVM'}
    
    # CASE A: Bank -> Crypto (Should Fail)
    valid, msg = FinanceValidator.validate_transfer(tradfi, defi_eth)
    print(f"   Test Bank -> DeFi ({valid}): {msg}")
    if valid: print("   ❌ FAILURE: Bank -> DeFi should be BLOCKED")
    else: print("   ✅ SUCCESS: Bank -> DeFi Blocked")

    # CASE B: Bank -> Exchange (Should Pass)
    valid, msg = FinanceValidator.validate_transfer(tradfi, cefi)
    if valid: print(f"   ✅ SUCCESS: Bank -> Exchange Allowed")
    else: print(f"   ❌ FAILURE: Bank -> Exchange Blocked ({msg})")

    # CASE C: DeFi -> DeFi (Different Chain) (Should Fail)
    valid, msg = FinanceValidator.validate_transfer(defi_eth, defi_sol)
    print(f"   Test EVM -> SVM ({valid}): {msg}")
    if valid: print("   ❌ FAILURE: EVM -> SVM Cross-Chain should be BLOCKED")
    else: print("   ✅ SUCCESS: Cross-Chain Blocked")
    
    # 3. Test Ledger (Integration)
    print("\n📒 Testing Ledger Recording...")
    # We will simulate a trade/transfer manually via DB to see if Ledger triggers work (logic is in App Layer, not DB Trigger)
    # Since logic is in Python, we trust the code review or unit test the command handler. 
    # Here we just check if the TABLE exists and is queryable.
    try:
        count = await database.Database.pool.fetchval("SELECT COUNT(*) FROM ledger")
        print(f"   ✅ Ledger Table Exists. Current Entries: {count}")
    except Exception as e:
        print(f"   ❌ Ledger Table Missing or Error: {e}")

    await database.Database.close()

if __name__ == "__main__":
    asyncio.run(test_strict_mode())
