from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import base64
from src.core.database import db

class GoogleManager:
    def __init__(self):
        self.creds = None
        self.service = None
        # Scopes for Contacts and potentially Drive/Sheets later
        self.SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']
        self.redirect_uri = "http://localhost:8080" # Default for local/desktop flow

    async def initialize(self):
        """Load credentials from DB/Env and refresh if needed"""
        print("🌐 Initializing Google Services...")
        await self.load_credentials()

    async def load_credentials(self):
        # Try to load token from DB
        token_json = await db.get_setting("google_token")

        if token_json:
            try:
                info = json.loads(token_json)
                self.creds = Credentials.from_authorized_user_info(info, self.SCOPES)
            except Exception as e:
                print(f"❌ Failed to load Google Token: {e}")
                self.creds = None

        # If no token in DB, check if we have client secrets to start flow later
        self.client_config = await self._get_client_config()

        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                await self.save_credentials()
                print("🔄 Google Token Refreshed")
            except Exception as e:
                print(f"❌ Failed to refresh Google Token: {e}")
                self.creds = None

        if self.creds:
            try:
                self.service = build('people', 'v1', credentials=self.creds)
                # print("✅ Google People API Connected")
            except Exception as e:
                print(f"❌ Google Service Build Error: {e}")
                self.service = None

    async def _get_client_config(self):
        """Retrieve client_id/secret from DB or Env"""
        client_id = await db.get_setting("google_client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = await db.get_setting("google_client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if client_id and client_secret:
            return {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        return None

    def get_auth_url(self):
        """Generate Authorization URL for user"""
        if not self.client_config:
            return None, "❌ Google Client ID/Secret not configured."

        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url, None
        except Exception as e:
            return None, f"❌ Auth URL Error: {e}"

    async def finish_auth(self, code):
        """Exchange code for token"""
        if not self.client_config:
            return False, "❌ Google Client Config missing."

        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            await self.save_credentials()

            # Re-init service
            self.service = build('people', 'v1', credentials=self.creds)
            return True, "✅ Google Authentication Successful!"
        except Exception as e:
            return False, f"❌ Token Exchange Error: {e}"

    async def save_credentials(self):
        if self.creds:
            await db.set_setting("google_token", self.creds.to_json())

    async def search_contacts(self, query):
        """Search contacts by name"""
        if not self.service:
            return []

        try:
            # People API search
            results = self.service.people().searchContacts(
                query=query,
                readMask='names,emailAddresses,phoneNumbers'
            ).execute()

            contacts = []
            if 'results' in results:
                for person in results['results']:
                    p = person.get('person', {})
                    name = p.get('names', [{}])[0].get('displayName')
                    resource_name = p.get('resourceName') # people/12345
                    if name:
                        contacts.append({
                            "name": name,
                            "id": resource_name
                        })
            return contacts
        except Exception as e:
            print(f"❌ Contact Search Error: {e}")
            return []

google_manager = GoogleManager()
