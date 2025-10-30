import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pip._vendor import cachecontrol
import google.auth.transport.requests as goo_request
import requests # Usada aqui para demonstrar o request.post/get de tokens

from apis.google.google_loggin_api import client_ifo as token
from apis.google.google_loggin_api import google_config
from users_manager.users.user_admin import Management_Admins
from users_manager.users.user_default import Create_Account, Login_Account, Management_user
from flask import Flask, render_template, redirect, request, url_for, session

# Cria uma instância da aplicação Flask
app = Flask(__name__)


# Define uma rota para a URL raiz ("/")
@app.route('/loggin', methods = ["GET", "POST"])
def loggin():

    if "user_name" in session:
        return redirect(url_for("/home"))
        
    if request.method == ["GET"]:
        return render_template("index.html")
    
    loggin_with = request.form["method"]
    create_new_account = request.get["new_account"]

    if loggin_with == "google":
        return redirect(url_for("/login/google"))
    
    if loggin_with == "loccal":
#--->loccal é um valor padrão
        account = {
        "user_name": request.get["user_name"],
        "password": request.get["password"]}
        userLoged, userAccount = Login_Account.login(loggin_with, account)
        if userLoged and userAccount:
            session["user_name"] = userAccount.get("user_name")
            return redirect("/home")
        render_template("index.html", error = "senha incorreta" if not userAccount["password"] else "nome de usuário incorreto")
    
    if create_new_account:
        return redirect(url_for("/create_account"))
    
    return render_template("index.html", error="Opção de login inválida.")
    
@app.route("/login/google", methods = ["GET"])
def google_login():
    #==================================== 
    authorization = google_config(redirect_by = "/home")
    if authorization:
        session["google_state"] = authorization.get("state")
        return redirect(url_for(authorization.get("oauth_autho")))
    
    return redirect(url_for("/login", error = "erro ao tentar logar com google"))
    #==================================== 

@app.route("/login/google/checkin", method = ["GET", "POST"])
def google_login_checkout():

    if request.method == "GET":
        render_template("google_login .html")

    cred = request.json.get("credential")
    
    authorization = google_config(redirect_by = "/home")
    if authorization:
        session["google_state"] = authorization.get("state")
        flow = authorization.get("flow")
        try:
            # Pede os tokens ao Google, usando o código recebido na URL
            flow.fetch_token(authorization_response=request.url)
            # Obtém o ID Token (token JWT com as informações do usuário)
            credentials = flow.credentials
            # Pede a ID do usuário para o Google
            req = goo_request.Request(session=cachecontrol.CacheControl(requests.session()))
            # O id_token contém dados seguros como email e ID do usuário
            account = token(credentials.id_token, req)

            if account:
                userLoged, userAccount = Login_Account.login("google", account)
            
            if userLoged and userAccount:
                session["user_name"] = userAccount.get("user_name")
                return redirect(url_for("/home"))
                
            return redirect(url_for("/loggin", erro = "ocorreu um erro ao tentar entrar com google"))
        
        except Exception as e:
            loggin.error("erro ao tentar usar a credencial para login")
            return False
        
    return redirect(url_for("/login", error = "erro ao tentar logar com google"))
    

@app.route("/create_account", methods = ["POST"])
def create_account():
    pass


@app.route("/home")
def home_page():
    redirect(url_for("home_page.html", session['user_name']))


@app.route("/select/<ele>")
def retornar_elementi(ele):
    pass


@app.route("/delete/<ele>")
def deletar_elemento(ele):
    pass
    
    
@app.route("/up/<ele1>/<ele2>")
def update(ele1, ele2):
    pass
    
@app.route("/add/<ele1>/<ele2>")
def insert(ele1, ele2):
    pass
    

# Inicia o servidor de desenvolvimento
if __name__ == '__main__':
    app.run(debug=True, port = 8080)