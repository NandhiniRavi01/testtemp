# config.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

# Remove hardcoded Zoho credentials - these will be provided by users
ZOHO_CLIENT_ID = None
ZOHO_CLIENT_SECRET = None
ZOHO_REDIRECT_URI = None
ZOHO_ACCESS_TOKEN = None
ZOHO_REFRESH_TOKEN = None
ZOHO_API_DOMAIN = os.getenv("ZOHO_API_DOMAIN")

def get_redirect_uri():
    # In production, this should be your AWS domain
    if os.getenv('FLASK_ENV') == 'production':
        return "https://your-aws-domain.com/zoho-callback"
    else:
        return "http://13.232.64.40:3000/zoho-callback"


# Global runtime state
class AppState:
    def __init__(self):
        self.progress = {"sent": 0, "total": 0, "status": "idle"}
        self.email_content = {"subject": "", "body": "", "sender_name": ""}
        self.zoho_status = {"connected": False, "message": "Not connected to Zoho CRM"}
        # Store user-specific Zoho credentials
        self.user_zoho_credentials = {}  # Format: {user_id: {client_id, client_secret, redirect_uri, access_token, refresh_token}}
        self.user_data = {}  # Format: {user_id: {email_content, zoho_status, progress, etc.}}


# Create a singleton instance
app_state = AppState()
