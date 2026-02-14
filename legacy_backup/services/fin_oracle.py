import logging
import database

logger = logging.getLogger('oracle')

class FinanceOracle:
    def __init__(self):
        pass # No need to init CCXT
        
    async def close(self):
        pass

    async def get_price(self, symbol: str):
        """
        Fetch price for a symbol from REDIS (Oracle Microservice).
        """
        # 1. Map Common Symbols to CoinGecko IDs (used by Go Oracle)
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'SUI': 'sui',
            'DOGE': 'dogecoin'
        }
        
        # 2. Try Exact Match (Case Sensitive - Important for DexScreener/Addresses)
        price = await self._read_redis(symbol)
        if price: return price

        # 3. Try Mapped Symbol
        if symbol.upper() in mapping:
             price = await self._read_redis(mapping[symbol.upper()])
             if price: return price

        # 4. Try Uppercase
        price = await self._read_redis(symbol.upper())
        if price: return price
        
        # 5. Try Variants
        variants = [
             f"{symbol.upper()}USDT",       # BTCUSDT
             f"{symbol.upper()}/USDT",      # BTC/USDT
             symbol.lower()                 # bitcoin
        ]
        for v in variants:
             price = await self._read_redis(v)
             if price: return price
        
        return None

    async def _read_redis(self, key):
        try:
            # Check Redis Key set by Oracle Service
            # Oracle uses key format: price:{SYMBOL}
            # Go Oracle stores keys exactly as fetched/defined.
            val = await database.Database.redis.get(f"price:{key}")
            if val:
                return float(val)
            return None
        except Exception as e:
            logger.error(f"Redis Read Error for {key}: {e}")
            return None

# Global Instance
oracle = FinanceOracle()
