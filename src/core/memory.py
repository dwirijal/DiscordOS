from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

class MemoryCore:
    def __init__(self):
        self.client = AsyncQdrantClient(url=os.getenv("QDRANT_URL"))
        self.collection_name = "second_brain"

    async def initialize(self):
        try:
            # Cek apakah koleksi memori sudah ada, jika belum, buat baru
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE) 
                    # Size 768 cocok untuk model embedding standard (misal Gemini Embedding)
                )
                print("✅ Qdrant Collection Created")
            else:
                print("✅ Qdrant Connected (Long-term Memory)")
        except Exception as e:
            print(f"❌ Qdrant Connection Error: {e}")

    async def recall(self, query_vector, limit=3):
        # Cari data yang relevan
        if not query_vector:
            return []

        try:
            return await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
        except Exception as e:
            print(f"⚠️ Memory Recall Error: {e}")
            return []

    async def remember(self, user_id, vector, payload):
        # Simpan data ke memori jangka panjang
        if not vector:
            return False

        try:
            point_id = str(uuid.uuid4())
            # Pastikan payload menyertakan user_id agar bisa difilter nanti jika perlu
            payload['user_id'] = str(user_id)

            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"⚠️ Memory Store Error: {e}")
            return False

memory = MemoryCore()
