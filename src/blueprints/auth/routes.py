import logging

import google.auth.transport.requests as goo_request
from flask import redirect, render_template, request, session, url_for
from google_auth_oauthlib.flow import Flow

from apis.google.google_login_api import client_ifo, google_config
from src.controller.users.user_default import Create_Account, Login_Account, check_user
from extensions import make_session_from_dbuser, save_google_picture

from . import auth_bp


# ── Login / Logout ────────────────────────────────────────────────────────────

@auth_bp.route("/", methods=["GET"])
def root():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("name"):
        return redirect(url_for("contents.contents"))

    if request.method == "GET":
        return render_template("index.html")

    login_with = request.form.get("method")
    create_new_account = request.form.get("new_account")
    logging.info("método de login: %s", login_with)

    if login_with == "google":
        return redirect(url_for("auth.google_login"))

    if login_with == "local":
        account = {
            "name": request.form.get("name"),
            "password": request.form.get("password"),
        }
        userLoged, userAccount = Login_Account.login("local", account)
        if userLoged and userAccount:
            try:
                user_dict = userAccount.get_user()
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            if session.get("cred") == "aluno":
                return redirect(url_for("contents.contents"))
            if session.get("cred") == "admin":
                return redirect(url_for("admin.admin_page"))
        return render_template("index.html", error="credenciais incorretas")

    if create_new_account:
        return redirect(url_for("auth.create_account"))

    return render_template("index.html", error="Opção de login inválida.")


@auth_bp.route("/logout")
def logout():
    session.clear()
    logging.info("Usuário deslogado com sucesso")
    return redirect(url_for("auth.login"))


# ── Google OAuth ──────────────────────────────────────────────────────────────

@auth_bp.route("/login/google", methods=["GET"])
def google_login():
    authorization = google_config("auth.google_login_checkout")

    session["google_state"] = authorization["google_state"]
    session["google_client_config"] = authorization["client_config"]
    session["google_code_verifier"] = authorization["google_code_verifier"]
    
    return redirect(authorization["oauth_autho"])


@auth_bp.route("/login/google/checkin")
def google_login_checkout():
    from flask import current_app

    flow = Flow.from_client_config(
        session.get("google_client_config"),
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=url_for("auth.google_login_checkout", _external=True),
        state=session.get("google_state"),
    )
    flow.code_verifier = session["google_code_verifier"]
    flow.fetch_token(authorization_response=request.url)

    req = goo_request.Request()
    account = client_ifo(flow.credentials._id_token, req)

    if account:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        account["picture"] = save_google_picture(account.get("picture", ""), upload_folder)

        userLoged, userAccount = Login_Account.login("google", account)
        if userLoged and userAccount:
            try:
                user_dict = dict(userAccount)
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            return redirect(url_for("contents.contents"))

        logging.error("Login Google falhou durante Login_Account.login()")
        return redirect(url_for("auth.login"))

    logging.error("Erro: account info google não retornada")
    return redirect(url_for("auth.login"))


# ── Criar conta ───────────────────────────────────────────────────────────────

@auth_bp.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        name = request.form.get("name")
        password_1 = request.form.get("password_1")
        password_2 = request.form.get("password_2")

        if password_1 != password_2:
            return render_template("create_account.html", error="senhas não coincidem"), 400

        if check_user(name):
            return render_template(
                "create_account.html", error="O nome de usuário já está sendo utilizado"
            ), 400

        userLoged, userAccount = Create_Account.creator(
            creationMethod="local",
            userName=name,
            email=None,
            pass1=password_1,
            pass2=password_2,
        )

        if userLoged and userAccount:
            try:
                user_dict = userAccount.get_user()
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            return redirect(url_for("contents.contents"))

    return render_template("create_account.html")
