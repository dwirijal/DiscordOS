import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Define MockCog BEFORE any imports
class MockCog:
    pass

# Setup mock for discord.ext.commands
mock_commands = MagicMock()
mock_commands.Cog = MockCog
mock_commands.command = MagicMock(side_effect=lambda **kwargs: lambda f: f)

# Setup mock for discord.ext
mock_ext = MagicMock()
mock_ext.commands = mock_commands

# Mock modules
sys.modules['discord'] = MagicMock()
sys.modules['discord.ext'] = mock_ext
sys.modules['discord.ext.commands'] = mock_commands
sys.modules['src.core.memory'] = MagicMock()
sys.modules['src.core.brain'] = MagicMock()
sys.modules['qdrant_client'] = MagicMock()
sys.modules['qdrant_client.models'] = MagicMock()

# Import the class under test
from src.cogs.ingestion import Ingestion, MAX_FILE_SIZE

class TestIngestionSecurity(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.cog = Ingestion(self.bot)

    async def test_memorize_large_file_rejected(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        ctx.typing.return_value.__aenter__ = AsyncMock()
        ctx.typing.return_value.__aexit__ = AsyncMock()

        large_attachment = MagicMock()
        large_attachment.filename = "large.txt"
        large_attachment.size = MAX_FILE_SIZE + 1
        large_attachment.read = AsyncMock()

        ctx.message.attachments = [large_attachment]

        await self.cog.memorize(ctx, content=None)

        # Verify large file was rejected
        ctx.send.assert_any_call(f"⚠️ large.txt is too large (max 5MB). Skipping.")
        large_attachment.read.assert_not_called()

    async def test_memorize_small_file_accepted(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        ctx.typing.return_value.__aenter__ = AsyncMock()
        ctx.typing.return_value.__aexit__ = AsyncMock()
        ctx.author = "testuser"

        small_attachment = MagicMock()
        small_attachment.filename = "small.txt"
        small_attachment.size = MAX_FILE_SIZE - 100
        small_attachment.read = AsyncMock(return_value=b"hello world")

        ctx.message.attachments = [small_attachment]

        # Patch brain and memory within the ingestion module
        with patch('src.cogs.ingestion.brain') as mock_brain, \
             patch('src.cogs.ingestion.memory') as mock_memory:

            mock_brain.embed_content = AsyncMock(return_value=[0.1, 0.2])
            mock_memory.client.upsert = AsyncMock()
            mock_memory.collection_name = "test_collection"

            await self.cog.memorize(ctx, content=None)

            # Verify small file was read and processed
            small_attachment.read.assert_called_once()
            mock_memory.client.upsert.assert_called_once()

if __name__ == '__main__':
    unittest.main()
