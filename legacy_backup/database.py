import asyncpg
import config
import logging
import redis.asyncio as redis

logger = logging.getLogger('database')

class Database:
    pool = None

    redis = None

    @classmethod
    async def connect(cls):
        try:
            # Postgres Connection
            cls.pool = await asyncpg.create_pool(
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                database=config.POSTGRES_DB,
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT
            )
            logger.info("✅ Connected to PostgreSQL")
            
            # Redis Connection
            cls.redis = redis.from_url(config.REDIS_URL, decode_responses=True)
            if await cls.redis.ping():
                 logger.info("✅ Connected to Dragonfly (Redis)")
            
            await cls.create_tables()
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise e

    @classmethod
    async def close(cls):
        if cls.pool:
            await cls.pool.close()
            logger.info("❌ Database connection closed")

    @classmethod
    async def create_tables(cls):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP,
                message_id BIGINT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS wallets (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL, -- 'bank', 'crypto', 'cash', 'temp'
                balance DECIMAL(32, 8) DEFAULT 0,
                currency TEXT DEFAULT 'IDR',
                account_info TEXT, -- Account Number / Address
                -- STRICT MODE COLUMNS
                category TEXT DEFAULT 'Personal', -- TradFi, CeFi, DeFi
                network TEXT DEFAULT 'Unknown', -- EVM, SVM, BANK, CASH
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS ledger (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER REFERENCES transactions(id),
                wallet_id INTEGER REFERENCES wallets(id),
                debit DECIMAL(32, 8) DEFAULT 0,
                credit DECIMAL(32, 8) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL, -- 'income', 'expense', 'buy', 'sell', 'transfer'
                category TEXT DEFAULT 'Uncategorized',
                description TEXT,
                
                -- Fiat Fields
                amount DECIMAL(18, 8) DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                
                -- Wallet Links
                wallet_id INTEGER REFERENCES wallets(id),
                dest_wallet_id INTEGER REFERENCES wallets(id), -- For Transfers
                
                -- Asset Fields (For Trading)
                asset_symbol TEXT,
                quantity DECIMAL(18, 8),
                price_per_unit DECIMAL(18, 8),
                fee DECIMAL(18, 8) DEFAULT 0,
                platform TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(100) NOT NULL UNIQUE,
                base_asset VARCHAR(20) NOT NULL,
                quote_asset VARCHAR(20) NOT NULL,
                asset_type VARCHAR(20) NOT NULL, -- Enum in DB, Text here to avoid complexity
                description TEXT,
                is_active BOOLEAN DEFAULT true,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            -- Oracle uses raw_prices (TimescaleDB), we generally read Redis.
            -- But we can keep market_data for local caching if needed, or remove it.
            -- Let's keep a simplified version compatible with Oracle's raw_prices if we wanted to query history.
            -- For now, just leave it out to avoid confusion.
            CREATE TABLE IF NOT EXISTS raw_prices_stub (
                id SERIAL PRIMARY KEY
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                last_completed TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        
        async with cls.pool.acquire() as conn:
            for query in queries:
                await conn.execute(query)
            
            # Migration: Ensure columns exist if table already exists (Naive approach for dev)
            # ... (Existing migration logic) ...
            migration_queries = [
                # ... existing ...
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS dest_wallet_id INTEGER REFERENCES wallets(id);"
            ]
            for q in migration_queries:
                try:
                    await conn.execute(q)
                except Exception:
                    pass

            logger.info("✅ Database tables verified/created (Schema V4 - KV Store)")

    # --- Helper Functions ---
    @classmethod
    async def get_config(cls, key: str):
        async with cls.pool.acquire() as conn:
            val = await conn.fetchval("SELECT value FROM kv_store WHERE key = $1", key)
            return val

    @classmethod
    async def set_config(cls, key: str, value: str):
        async with cls.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO kv_store (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
            """, key, str(value))

    @classmethod
    async def add_task(cls, content, priority='medium', due_date=None):
        async with cls.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tasks (content, priority, due_date) VALUES ($1, $2, $3) RETURNING id",
                content, priority, due_date
            )
            return row['id']

    @classmethod
    async def log_transaction(cls, amount, type, category, description, wallet_id=None):
        async with cls.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO transactions (amount, type, category, description, wallet_id) 
                VALUES ($1, $2, $3, $4, $5)
                """,
                amount, type, category, description, wallet_id
            )
            
            # Update Wallet Balance
            if wallet_id:
                if type == 'income':
                    await conn.execute("UPDATE wallets SET balance = balance + $1 WHERE id = $2", amount, wallet_id)
                elif type == 'expense':
                    await conn.execute("UPDATE wallets SET balance = balance - $1 WHERE id = $2", amount, wallet_id)

    @classmethod
    async def get_wallets_simple(cls):
        """Returns list of dicts: id, name, type"""
        async with cls.pool.acquire() as conn:
            return await conn.fetch("SELECT id, name, type, currency FROM wallets WHERE is_active = TRUE")

    @classmethod
    async def add_note(cls, content):
        async with cls.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO notes (content) VALUES ($1)",
                content
            )
