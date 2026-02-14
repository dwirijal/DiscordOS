from aiohttp import web
import json

async def handle(request):
    try:
        data = await request.json()
        print(f"📥 Received Paylod:\n{json.dumps(data, indent=2)}")
        
        # Simulate Gemini Response
        response_text = f"🤖 [Mock Gemini]: Hello {data.get('username')}, I received your query: '{data.get('query')}'."
        return web.json_response({"text": response_text})
    except Exception as e:
        print(f"❌ Error: {e}")
        return web.Response(status=500)

app = web.Application()
app.add_routes([web.post('/webhook/gemini-chat', handle)])

if __name__ == '__main__':
    print("🚀 Mock n8n Server running on http://localhost:5678")
    web.run_app(app, port=5678)
