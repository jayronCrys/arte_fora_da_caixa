import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pip._vendor import cachecontrol
import google.auth.transport.requests as goo_request
import requests 


from apis.google.google_loggin_api import client_ifo as token
from apis.google.google_loggin_api import google_config
from controller.users.user_admin import Management_Admins
from controller.users.user_default import Create_Account, Login_Account, Management_User_Default
from flask import Flask, render_template, redirect, request, url_for, session

# Cria uma instância da aplicação Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

@app.route('/loggin', methods=["GET", "POST"])
def loggin():
    if "user_name" in session:
        return redirect(url_for("home_page"))

    if request.method == "GET":
        return render_template("index.html")

    loggin_with = request.form.get("method")
    create_new_account = request.form.get("new_account")

    if loggin_with == "google":
        return redirect(url_for("google_login"))

    if loggin_with == "local":
        account = {
            "name": request.form.get("user_name"),
            "password": request.form.get("password")
        }
        userLoged, userAccount = Login_Account.login(loggin_with, account)
        if userLoged and userAccount:
            session["user_name"] = userAccount.get("name") if isinstance(userAccount, dict) else getattr(userAccount, "name", None)
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
        return redirect(authorization.get("oauth_autho"))
    return redirect(url_for("loggin"))

@app.route("/login/google/checkin", methods=["GET", "POST"])
def google_login_checkout():
    # Esta rota é chamada pelo Google após o consent screen, ou usada para validar token recebido no front
    if request.method == "POST":
        cred = request.json.get("credential")
        req = goo_request.Request(session=cachecontrol.CacheControl(requests.session()))
        account = token(cred, req)
        if account:
            userLoged, userAccount = Login_Account.login("google", account)
            if userLoged and userAccount:
                session["user_name"] = userAccount.get("name")
                return redirect(url_for("home_page"))
        return redirect(url_for("loggin"))

    # GET - mostrar página de confirmação
    return render_template("google_login.html")

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    # implementar formulário logica de criação usa Create_Account.creator
    return "rota create_account (implementar)"

@app.route("/home")
def home_page():
    user = session.get('user_name')
    return render_template("home_page.html", user_name=user)

@app.route("/select/<ele>")
def retornar_elementi(ele):
    return f"select {ele}"

@app.route("/delete/<ele>")
def deletar_elemento(ele):
    return f"delete {ele}"

@app.route("/up/<ele1>/<ele2>")
def update(ele1, ele2):
    return f"update {ele1} -> {ele2}"

@app.route("/add/<ele1>/<ele2>")
def insert(ele1, ele2):
    return f"insert {ele1} -> {ele2}"

# Inicia o servidor de desenvolvimento
if __name__ == '__main__':
    try:
        from models.database.creator_database import create_db
        # se quiser automatizar: create_db()
    except Exception:
        pass

    app.run(debug=True, port=8080)