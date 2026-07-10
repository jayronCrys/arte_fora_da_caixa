import logging

import google.auth.transport.requests as goo_request
from google_auth_oauthlib.flow import Flow

from apis.google.google_login_api import client_ifo, google_config
from src.controller.users.user_default import Create_Account, Login_Account, check_user
from src.extensions import make_session_from_dbuser, save_google_picture

from flask import (
    current_app,
    flash, g, redirect,
    render_template, request,
    session, url_for)

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

    login_with         = request.form.get("method")
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

            cred = session.get("cred")
            if cred == "aluno":
                return redirect(url_for("contents.contents"))
            if cred == "admin":
                return redirect(url_for("admin.admin_page"))
            if cred == "professor":
                # contents.html já contém o painel do professor (abas de
                # publicações e "Minha análise", carregada via fetch), então
                # é o destino correto — evita cair na rota de API que só
                # devolve JSON cru (professor.profille_analytics_professor).
                return redirect(url_for("contents.contents"))

            # Cred desconhecida: não deixa a view sem retorno.
            logging.warning("Login bem-sucedido com cred não mapeada: %s", cred)
            return redirect(url_for("contents.contents"))

        return render_template("index.html", error="credenciais incorretas")

    if create_new_account:
        return redirect(url_for("auth.create_account"))

    return render_template("index.html", error="Opção de login inválida.")


@auth_bp.route("/logout")
def logout():
    session.clear()
    logging.info("Usuário deslogado com sucesso")
    return redirect(url_for("auth.login"))


# ── Google OAuth (login) ───────────────────────────────────────────────────────

@auth_bp.route("/login/google", methods=["GET"])
def google_login():
    # Garante que um link malsucedido anterior não deixe a próxima tentativa
    # de login normal sendo tratada como vinculação por engano.
    session.pop("google_link_mode", None)

    authorization = google_config("auth.google_login_checkout")

    session["google_state"]         = authorization["google_state"]
    session["google_client_config"] = authorization["client_config"]
    session["google_code_verifier"] = authorization["google_code_verifier"]

    return redirect(authorization["oauth_autho"])


# ── Google OAuth (vincular e-mail a uma conta já existente) ───────────────────

@auth_bp.route("/link/google", methods=["GET"])
def link_google_account():
    """
    Permite que um usuário já logado (criado via conta local) vincule um
    e-mail do Google à própria conta, sem sobrescrever nome, senha ou foto
    já cadastrados. Reaproveita o mesmo fluxo OAuth e o mesmo callback do
    login (/login/google/checkin), diferenciando o comportamento via a flag
    de sessão "google_link_mode".
    """
    if not session.get("user"):
        flash("Faça login para vincular uma conta Google.")
        return redirect(url_for("auth.login"))

    authorization = google_config("auth.google_login_checkout")

    session["google_state"]         = authorization["google_state"]
    session["google_client_config"] = authorization["client_config"]
    session["google_code_verifier"] = authorization["google_code_verifier"]
    session["google_link_mode"]     = True

    return redirect(authorization["oauth_autho"])


@auth_bp.route("/login/google/checkin")
def google_login_checkout():
    link_mode = session.pop("google_link_mode", False)
    flow      = Flow.from_client_config(
        session.get("google_client_config"),
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri   =  url_for("auth.google_login_checkout", _external=True),
        state          = session.get("google_state"),
    )
    flow.code_verifier = session["google_code_verifier"]
    flow.fetch_token(authorization_response=request.url)

    req = goo_request.Request()
    account = client_ifo(flow.credentials._id_token, req)

    if not account:
        logging.error("Erro: account info google não retornada")
        return redirect(url_for("auth.login"))

    if link_mode:
        return _link_google_to_current_user(account)

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    userLoged, userAccount = Login_Account.login("google", account)
    if userLoged and userAccount:
        try:
            save_google_picture(userLoged.userId, account.get("picture", ""), upload_folder)


            user_dict = dict(userAccount)
        except Exception:
            user_dict = userAccount
        make_session_from_dbuser(user_dict)
        return redirect(url_for("contents.contents"))

    logging.error("Login Google falhou durante Login_Account.login()")
    return redirect(url_for("auth.login"))


def _link_google_to_current_user(account: dict):
    """
    Vincula e-mail (e foto, se ausente) do Google à conta atualmente logada.
    Nunca sobrescreve nome, senha ou foto/e-mail já cadastrados.
    """
    if not getattr(g, "user", None):
        flash("Sessão expirada. Faça login novamente para vincular sua conta Google.")
        return redirect(url_for("auth.login"))

    current = g.user.get_user()
    if not current:
        flash("Não foi possível carregar os dados da sua conta.")
        return redirect(url_for("user.user"))

    updated_any = False

    if not current.get("email"):
        if g.user.update_user(field="email", newValue1=account.get("email")):
            updated_any = True
        else:
            logging.error("Falha ao vincular e-mail Google ao usuário %s", g.user.userId)
            flash("Não foi possível vincular o e-mail do Google a esta conta.")
            return redirect(url_for("user.user"))
    else:
        logging.info(
            "Usuário %s já possui e-mail cadastrado; e-mail do Google ignorado.",
            g.user.userId,
        )

    if not current.get("picture"):
        upload_folder   = current_app.config["UPLOAD_FOLDER"]
        google_picture  = save_google_picture(account.get("picture", ""), upload_folder)
        if google_picture and g.user.update_user(field="picture", newValue1=google_picture):
            updated_any = True

    if updated_any:
        try:
            updated      = check_user(g.user.userId, column="id")
            updated_dict = dict(updated) if not isinstance(updated, dict) else updated
            make_session_from_dbuser(updated_dict)
        except Exception as exc:
            logging.error("Erro ao atualizar sessão após vincular Google: %s", exc)
        flash("Conta Google vinculada com sucesso.")
    else:
        flash("Sua conta já possui e-mail e foto cadastrados; nada foi alterado.")

    return redirect(url_for("user.user"))


# ── Criar conta ───────────────────────────────────────────────────────────────

@auth_bp.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        name         = request.form.get("name")
        password_1   = request.form.get("password_1")
        password_2   = request.form.get("password_2")

        if password_1 != password_2:
            return render_template("create_account.html", error="senhas não coincidem"), 400

        if check_user(name):
            return render_template(
                "create_account.html", error="O nome de usuário já está sendo utilizado"
            ), 400
 
        userLoged, userAccount = Create_Account.creator(
            creationMethod ="local",
            userName       = name,
            email          = None,
            pass1          = password_1,
            pass2          = password_2,
        )

        if userLoged and userAccount:
            try:
                user_dict = userAccount.get_user()
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            return redirect(url_for("contents.contents"))

    return render_template("create_account.html")