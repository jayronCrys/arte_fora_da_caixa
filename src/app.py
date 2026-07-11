import sys
import os
import logging
from flask_wtf import CSRFProtect
from src.extensions import load_g_user, mail
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, send_from_directory
from src.models.mongo_models.rating_models import init_mongodb
from flask_cors import CORS
# Blueprints

from src.blueprints.auth import    auth_bp
from src.blueprints.auth import forg_pass_bp
from src.blueprints.user import user_bp
from src.blueprints.user import inscriptions_bp
from src.blueprints.contents import contents_bp
from src.blueprints.admin import admin_bp
from src.blueprints.professor import professor_bp

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder = "view/templates",
        static_folder   = "view/static",
    )
    CORS(app)

    app.config['MAIL_SERVER']         = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT']           = os.environ.get('MAIL_PORT')
    app.config['MAIL_USE_TLS']        = os.environ.get('MAIL_USE_TLS')
    app.config['MAIL_USERNAME']       = os.environ.get('EMAIL')
    app.config['MAIL_PASSWORD']       = os.environ.get('MAIL_PASS')   # senha de app, não a normal
    app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get('MAIL_NAME'), os.environ.get('EMAIL'))


    
    app.secret_key = os.environ.get("FLASK_SECRET")

    csrf = CSRFProtect()
    csrf.init_app(app)
    mail.init_app(app)
    init_mongodb()

    # ── Upload de imagens de perfil ───────────────────────────────────────────
    UPLOAD_FOLDER               = os.path.join(app.static_folder, "profile_images")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # ── Hooks globais ─────────────────────────────────────────────────────────
    app.before_request(load_g_user)

    # ── Servir imagens de perfil ──────────────────────────────────────────────
    @app.route("/profile_images/<filename>")
    def profile_images(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    # ── Registro dos blueprints ───────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(forg_pass_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(inscriptions_bp)
    app.register_blueprint(contents_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(professor_bp)

    return app


if __name__ == "__main__":
    try:
        from src.models.database.creator_database import create_db
        from src.maker_admin import make_users, make_contents

        
        make_users()
        make_contents()
        create_db()

    except Exception as exc:
        logging.info("create_db não executado ou já existente: %s", exc)

    load_dotenv()
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app = create_app()
    app.run(debug=True, port=8080, host="0.0.0.0")
