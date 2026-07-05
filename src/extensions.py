import os
import logging
import subprocess
import uuid
import requests

from flask import session, g
from src.controller.users.user_admin import Management_Admins
from src.controller.users.user_professor import Management_Professors
from src.controller.users.user_default import Management_User_Default
# extensions.py
from flask_mail import Mail
from storage.storage_host import upload_user_profile_image

mail = Mail()


def make_session_from_dbuser(db_user_dict):
    """Popula a sessão Flask a partir de um dict de usuário do banco."""
    if not db_user_dict:
        return
    session["user"] = {
        "id": str(db_user_dict.get("id")),
        "name": db_user_dict.get("name"),
        "email": db_user_dict.get("email"),
        "picture": db_user_dict.get("picture"),
        "creation_date": str(db_user_dict.get("creation_date")),
        "cred": db_user_dict.get("cred"),
    }
    session["name"] = session["user"]["name"]
    session["email"] = session["user"]["email"]
    session["picture"] = session["user"]["picture"]
    session["id"] = session["user"]["id"]
    session["cred"] = session["user"]["cred"]
    session.modified = True
    logging.info("Sessão criada/atualizada para %s", session.get("name"))


def load_g_user():
    """Reconstrói g.user a partir da sessão. Chamado em before_request."""
    if session.get("user"):
        user_data = session["user"]
        g.user = Management_User_Default(user_data)
        if user_data.get("cred") == "admin":
            g.user = Management_Admins(g.user.get_user())
        elif user_data.get("cred") == "professor":
            g.user = Management_Professors(g.user.get_user())


def save_google_picture(user_id: str, picture_url: str, image_name: str) -> str:
    """
    Baixa a foto de perfil do Google, salva localmente e retorna a URL pública.
    Retorna a URL original em caso de falha.
    """
    if not (picture_url and picture_url.startswith("http")):
        return picture_url
    try:
        img_bytes = requests.get(picture_url).content
        
        image_path = upload_user_profile_image(user_id, image_name, img_bytes)
        return image_path
    
    except Exception as exc:
        logging.error("Erro ao salvar foto de perfil do Google: %s", exc)
        return picture_url


def convert_heic_to_jpeg(source_path: str, dest_path: str, quality: int = 90) -> bool:
    """Converte HEIC -> JPEG usando heif-convert ou ImageMagick (fallback)."""
    try:
        subprocess.run(
            ["heif-convert", "-q", str(quality), source_path, dest_path],
            check=True, capture_output=True, timeout=30,
        )
        logging.info("HEIC convertido com heif-convert: %s -> %s", source_path, dest_path)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        logging.warning("heif-convert falhou ou não encontrado: %s", exc)

    try:
        subprocess.run(
            ["convert", source_path, "-quality", str(quality), dest_path],
            check=True, capture_output=True, timeout=30,
        )
        logging.info("HEIC convertido com ImageMagick: %s -> %s", source_path, dest_path)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        logging.error("ImageMagick também falhou: %s", exc)

    return False
