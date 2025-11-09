from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from flask import url_for
 # Usada aqui para demonstrar o request.post/get de tokens

import logging
import os

CLIENT_ID = [os.environ.get("GOOGLE_CLIENT_ID",
                            "PUBLIC_CLIENT_ID.apps.google.usercontent.com")]


def google_config(redirect_by):
    
    try:
        CLIENT_SECRET = os.environ.get("client_secret")
        CLIENT_ID = os.environ.get("client_id")
        SCOPES = SCOPES = ["https://www.googleapis.com/auth/userinfo.email", 
        "https://www.googleapis.com/auth/userinfo.profile", 
        "openid"]
 #====================================
        
        if CLIENT_SECRET and CLIENT_ID:
            redirect_uri = url_for(redirect_by , _external = True)
            try:
                client_config = {"web": {
                "client_id" : CLIENT_ID,
                "client_secret" : CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "userinfo_uri": "https://www.googleapis.com/oauth2/v3/userinfo",
                "redirect_uris" : [redirect_uri],}
                }
                
                flow = Flow.from_client_config(
                client_config, scope = SCOPES, redirect_uri = redirect_uri)
                
                oauth_url, state = flow.authorization_url(
                acess_type = "offline", include_grated_scope = "true")
                
                return {"oauth_autho":oauth_url,
                "google_state": state,
                "flow": flow}
                
            except Exception as e:
                logging.error(f"Erro de autenticação no google oauth : {e}")
                return False
                
        logging.erro("Erro interno nas credenciais")
        return False
        
    except Exception as e:
        logging.erro(f"Erro: {e}")
        return False
        
                
def client_ifo(token,req):

   try: 
        info_id = id_token.verify_oauth2_token(token, req, CLIENT_ID[0])
        return {"user_name": info_id["name"],
                "email": info_id["email"],

                "picture": info_id["picture"]}#--->acho que essas informações já basta
   except Exception as e:
        logging.error(f"Erro oauth: {e}")
        return False
    
