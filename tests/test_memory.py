import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import sys

# Mock dependencies before importing src.core.memory
mock_qdrant = MagicMock()
sys.modules['qdrant_client'] = mock_qdrant
sys.modules['qdrant_client.models'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Add the project root to sys.path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMemoryCore(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We patch AsyncQdrantClient in the memory module
        self.patcher = patch('src.core.memory.AsyncQdrantClient')
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value

        # Mock get_collections to avoid error in initialize if it's called
        self.mock_client.get_collections = AsyncMock()

        from src.core.memory import MemoryCore
        self.memory_core = MemoryCore()
        # Ensure the instance uses a mock client for search calls
        self.memory_core.client = AsyncMock()

    def tearDown(self):
        self.patcher.stop()

    async def test_recall_empty_vector(self):
        # Test with empty list
        result = await self.memory_core.recall([])
        self.assertEqual(result, [])

        # Test with None
        result = await self.memory_core.recall(None)
        self.assertEqual(result, [])

        # Ensure search was NOT called
        self.memory_core.client.search.assert_not_called()

    async def test_recall_valid_vector(self):
        # Mock search return value
        mock_results = [AsyncMock(), AsyncMock()]
        self.memory_core.client.search = AsyncMock(return_value=mock_results)

        query_vector = [0.1, 0.2, 0.3]
        result = await self.memory_core.recall(query_vector)

        self.assertEqual(result, mock_results)
        self.memory_core.client.search.assert_called_once_with(
            collection_name=self.memory_core.collection_name,
            query_vector=query_vector,
            limit=3
        )

    async def test_recall_exception_handling(self):
        # Mock search to raise an exception
        self.memory_core.client.search = AsyncMock(side_effect=Exception("Search failed"))

        query_vector = [0.1, 0.2, 0.3]
        result = await self.memory_core.recall(query_vector)

        # Should return empty list on exception
        self.assertEqual(result, [])
        self.memory_core.client.search.assert_called_once()

if __name__ == '__main__':
    unittest.main()
