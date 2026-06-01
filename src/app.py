import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, send_from_directory
from extensions import load_g_user
from src.models.contents_models.rating_models import init_mongodb
from flask_cors import CORS

# Blueprints
from blueprints.auth import auth_bp
from blueprints.user import user_bp
from blueprints.user import inscriptions_bp
from blueprints.contents import contents_bp
from blueprints.admin import admin_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="view/templates",
        static_folder="view/static",
    )
    CORS(app)
    app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

    # 🌟 INICIALIZAÇÃO DO MONGO: Movido para dentro do ciclo de criação do App
    print("🔌 Conectando ao MongoDB e aplicando validadores...")
    init_mongodb()

    # ── Upload de imagens de perfil ───────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(app.static_folder, "profile_images")
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
    app.register_blueprint(user_bp)
    app.register_blueprint(inscriptions_bp)
    app.register_blueprint(contents_bp)
    app.register_blueprint(admin_bp)

    return app


if __name__ == "__main__":
    try:
        from src.models.database.creator_database import create_db
        from src.maker_admin import make_users

        create_db()
        make_users()
    except Exception as exc:
        logging.info("create_db não executado ou já existente: %s", exc)

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # create_app já vai rodar o init_mongodb() internamente agora!
    app = create_app()
    
    app.run(debug=True, port=8080, host="0.0.0.0")
