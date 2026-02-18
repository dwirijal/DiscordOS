import asyncpg
import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.pg_pool = None
        self.dragonfly = None

    async def connect(self):
        # 1. Connect PostgreSQL
        try:
            dsn = os.getenv("POSTGRES_DSN")
            if not dsn:
                print("⚠️ POSTGRES_DSN not found in .env. Structured data will be unavailable.")
            else:
                self.pg_pool = await asyncpg.create_pool(dsn)
                print("✅ PostgreSQL Connected (Structured Data)")
                await self.initialize_health_tables()
                await self.initialize_rss_tables()
        except Exception as e:
            print(f"❌ Postgres Error: {e}")

        # 2. Connect Dragonfly (Redis Protocol)
        try:
            url = os.getenv("DRAGONFLY_URL")
            if not url:
                print("⚠️ DRAGONFLY_URL not found in .env")
                return

            self.dragonfly = redis.from_url(url)
            await self.dragonfly.ping()
            print("✅ Dragonfly Connected (Short-term Memory)")
        except Exception as e:
            print(f"❌ Dragonfly Error: {e}")

    async def close(self):
        if self.pg_pool: 
            await self.pg_pool.close()
            print("🔒 PostgreSQL Connection Closed")
        if self.dragonfly: 
            await self.dragonfly.close()
            print("🔒 Dragonfly Connection Closed")

    async def initialize_health_tables(self):
        if not self.pg_pool: return
        query = """
        CREATE TABLE IF NOT EXISTS health_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            metric_type VARCHAR(50) NOT NULL,
            data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_health_logs_user_type ON health_logs(user_id, metric_type);
        """
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query)
                print("✅ Health Tables Initialized")
        except Exception as e:
            print(f"❌ Database Init Error: {e}")

    async def initialize_rss_tables(self):
        if not self.pg_pool: return
        query = """
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            category VARCHAR(50),
            added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS rss_logs (
            id SERIAL PRIMARY KEY,
            feed_id INTEGER REFERENCES rss_feeds(id),
            article_url TEXT UNIQUE NOT NULL,
            title TEXT,
            summary TEXT,
            published_at TIMESTAMP WITH TIME ZONE
        );
        CREATE INDEX IF NOT EXISTS idx_rss_logs_feed ON rss_logs(feed_id);
        """
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query)
                print("✅ RSS Tables Initialized")
        except Exception as e:
            print(f"❌ Database RSS Init Error: {e}")

    async def add_rss_feed(self, url, category="general"):
        if not self.pg_pool: return False
        query = "INSERT INTO rss_feeds (url, category) VALUES ($1, $2) ON CONFLICT (url) DO NOTHING RETURNING id"
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, url, category)
                return row['id'] if row else None
        except Exception as e:
            print(f"❌ Add RSS Feed Error: {e}")
            return None

    async def get_rss_feeds(self):
        if not self.pg_pool: return []
        query = "SELECT id, url, category FROM rss_feeds"
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Get RSS Feeds Error: {e}")
            return []

    async def is_article_processed(self, article_url):
        if not self.pg_pool: return False
        query = "SELECT 1 FROM rss_logs WHERE article_url = $1 LIMIT 1"
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, article_url)
                return row is not None
        except Exception as e:
            return False

    async def log_rss_article(self, feed_id, article_url, title, summary, published_at=None):
        if not self.pg_pool: return False
        query = """
            INSERT INTO rss_logs (feed_id, article_url, title, summary, published_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (article_url) DO NOTHING
        """
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query, feed_id, article_url, title, summary, published_at)
            return True
        except Exception as e:
            print(f"❌ Log RSS Article Error: {e}")
            return False

    async def log_health_data(self, user_id, metric_type, data):
        if not self.pg_pool: return False
        query = "INSERT INTO health_logs (user_id, metric_type, data) VALUES ($1, $2, $3)"
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query, user_id, metric_type, json.dumps(data))
            return True
        except Exception as e:
            print(f"❌ Log Health Error: {e}")
            return False

    async def get_recent_health_logs(self, user_id, metric_type, limit=10):
        if not self.pg_pool: return []
        query = """
            SELECT data, created_at FROM health_logs
            WHERE user_id = $1 AND metric_type = $2
            ORDER BY created_at DESC LIMIT $3
        """
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, metric_type, limit)
                # Convert Record to dict, parse JSONB string back to dict
                result = []
                for row in rows:
                    entry = dict(row)
                    if isinstance(entry['data'], str):
                        entry['data'] = json.loads(entry['data'])
                    result.append(entry)
                return result
        except Exception as e:
            print(f"❌ Get Health Logs Error: {e}")
            return []

# Singleton Instance
db = DatabaseManager()
