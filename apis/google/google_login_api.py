from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from flask import url_for
import logging
import os
"""from dotenv import load_dotenv
load_dotenv()"""

logger = logging.getLogger(__name__)
CLIENT_SECRET = os.getenv("GOOGLE_KEY")
CLIENT_ID = os.getenv("GOOGLE_USER")

def google_config(redirect_by):
    print("GOOGLE_KEY:", CLIENT_SECRET)
    print("GOOGLE_USER:", CLIENT_ID)
    try:
        
        SCOPES = ["https://www.googleapis.com/auth/userinfo.email",
                  "https://www.googleapis.com/auth/userinfo.profile",
                  "openid"]

        if CLIENT_SECRET and CLIENT_ID:
            redirect_uri = url_for(redirect_by, _external=True)
            client_config = {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "userinfo_uri": "https://www.googleapis.com/oauth2/v3/userinfo",
                    "redirect_uris": [redirect_uri],
                }
            }
            redirect_uri = url_for("auth.google_login_checkout", _external=True)
            print("Redirect URI:", repr(redirect_uri))
            flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
            oauth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true"
            )
            
            return {
                "oauth_autho": oauth_url,
                "google_state": state,
                "google_code_verifier": flow.code_verifier,
                "client_config": client_config
            }

        logging.error("Erro interno nas credenciais")
        return False

    except Exception as e:
        logging.error(f"Erro: {e}")
        return False


def client_ifo(token, req):
    try:
        info_id = id_token.verify_oauth2_token(token, req, CLIENT_ID)
        print("passo?")
        return {"name": info_id.get("name"),
                "email": info_id.get("email"),
                "picture": info_id.get("picture")}
    except Exception as e:
        logging.error(f"Erro oauth: {e}")
        return False
    
print("GOOGLE_KEY:", CLIENT_SECRET)
print("GOOGLE_USER:", CLIENT_ID)