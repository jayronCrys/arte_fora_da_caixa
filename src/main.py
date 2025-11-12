import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#Para login
from pip._vendor import cachecontrol
import google.auth.transport.requests as goo_request
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as goo_request
from src.controller.apis.google.google_login_api import client_ifo
from src.controller.apis.google.google_login_api import google_config

#Users
from src.controller.users.user_admin import Management_Admins
from src.controller.users.user_default import Create_Account, Login_Account, Management_User_Default

#servidor
from flask import Flask, render_template, redirect, request, url_for, session
import requests 
import logging


print("Caminho atual:", os.getcwd())
print("Templates:", os.path.exists("src/view/templates/home_page.html"))


# Cria uma instância da aplicação Flask
app = Flask(__name__, template_folder="view/templates", static_folder="view/static")
app.secret_key = "12434"#os.environ.get("FLASK_SECRET", "dev-secret")





@app.route('/login', methods=["GET", "POST"])
def login():
    if "name" in session:
        return redirect(url_for("home_page"))

    if request.method == "GET":
        return render_template("index.html")

    login_with = request.form.get("method")
    create_new_account = request.form.get("new_account")
    logging.info(f"medos de login: {login_with}")
    if login_with == "google":
        logging.info("login usando google")
        return redirect(url_for("google_login"))

    if login_with == "local":
        logging.info("login local")
        account = {
            "name": request.form.get("name"),
            "password": request.form.get("password")
        }
        userLoged, userAccount = Login_Account.login(login_with, account)
        if userLoged and userAccount:
            session["name"] = userAccount.get("name")
            session["email"] = userAcccount.get("email")
            session["picture"] = userAccount.get("picture")
            session["cred"] = userAccount.get("cred")
            return redirect(url_for("home_page"))
        return render_template("index.html", error="credenciais incorretas")

    if create_new_account:
        return redirect(url_for("create_account"))

    return render_template("index.html", error="Opção de login inválida.")





@app.route("/login/google", methods=["GET"])
def google_login():
    authorization = google_config(redirect_by="google_login_checkout")
    
    if authorization:
        session["google_state"] = authorization.get("google_state")
        session["google_client_config"] = authorization.get("client_config")
        print("pego flow")
        
        return redirect(authorization.get("oauth_autho"))
    return redirect(url_for("login"))




@app.route("/login/google/checkin")
def google_login_checkout():
    
    flow = Flow.from_client_config(
    session.get("google_client_config"),
    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_uri=url_for("google_login_checkout", _external=True),
    state=session.get("google_state")
)

    flow.fetch_token(authorization_response=request.url)
    req = goo_request.Request()
    account = client_ifo(flow.credentials._id_token, req)
   
    if account:
        userLoged, userAccount = Login_Account.login("google", account)
        if userLoged and userAccount:
            session["name"] = userAccount.get("name")
            session["email"] = userAccount.get("email")
            session["picture"] = userAccount.get("picture")
            session["cred"] = userAccount.get("cred")
            return redirect(url_for("home_page"))
                    
        return redirect(url_for("login"))
    
    return render_template("index.html")

from flask import request, redirect, url_for, session



@app.route("/create_account", methods=["GET", "POST"])
def create_account():
  
    if request.method == "POST":
        
      
        name = request.form.get("name")
        password_1 = request.form.get("password_1")
        password_2 = request.form.get("password_2") 
        
        if password_1 != password_2:
            # Retornar uma mensagem de erro ao usuário (melhor seria renderizar o template com erro)
            return "Erro: As senhas não coincidem.", 400 
        creation_method = "local"
        
        user_logged, user_account = Create_Account.creator(
            creationMethod = creation_method,
            userName = name,
            email = None, 
            pass1 = password_1,
            pass2 = password_2
        )
        
        if user_logged and user_account:             
            session["name"] = user_account.get("name")
            session["email"] = user_account.get("email")
            session["picture"] = user_account.get("picture")
            session["cred"] = user_account.get("cred")
            return redirect(url_for("home_page"))
        else:
            return name
              
    return render_template("create_account.html")
    
@app.route("/home")
def home_page():
    user_name = session.get("name", "Visitante")
    user_email = session.get("email", "não informado")
    
    return render_template(
        "home_page.html",
        user_name=user_name,
        user_email=user_email
    )

@app.route("/logout")
def logout():
    session.clear()
    app.logger.info("Usuário deslogado com sucesso")
    return redirect(url_for("login"))


if __name__ == '__main__':
    try:
        from models.database.creator_database import create_db
        create_db()
    except Exception:
        close()

    app.run(debug=True, port=8080)