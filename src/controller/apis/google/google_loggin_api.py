from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from flask import url_for

# Usada aqui para demonstrar o request.post/get de tokens

import logging
import os

logger = logging.getLogger(__name__)

CLIENT_ID = [os.environ.get("GOOGLE_CLIENT_ID", "PUBLIC_CLIENT_ID.apps.googleusercontent.com")]

def google_config(redirect_by):
    try:
        CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
        CLIENT_ID_ENV = os.environ.get("GOOGLE_CLIENT_ID")
        SCOPES = ["https://www.googleapis.com/auth/userinfo.email",
                  "https://www.googleapis.com/auth/userinfo.profile",
                  "openid"]

        if CLIENT_SECRET and CLIENT_ID_ENV:
            redirect_uri = url_for(redirect_by, _external=True)
            try:
                client_config = {"web": {
                    "client_id": CLIENT_ID_ENV,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "userinfo_uri": "https://www.googleapis.com/oauth2/v3/userinfo",
                    "redirect_uris": [redirect_uri],
                }}
                flow = Flow.from_client_config(client_config, scope=SCOPES, redirect_uri=redirect_uri)
                oauth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
                return {"oauth_autho": oauth_url, "google_state": state, "flow": flow}
            except Exception as e:
                logging.error(f"Erro de autenticação no google oauth : {e}")
                return False

        logger.error("Erro interno nas credenciais")
        return False

    except Exception as e:
        logger.error(f"Erro: {e}")
        return False


def client_ifo(token, req):
    try:
        info_id = id_token.verify_oauth2_token(token, req, CLIENT_ID[0])
        return {"userName": info_id.get("name"),
                "email": info_id.get("email"),
                "picture": info_id.get("picture")}
    except Exception as e:
        logging.error(f"Erro oauth: {e}")
        return False