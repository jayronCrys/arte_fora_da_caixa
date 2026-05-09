import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Para PDF
from io import BytesIO

# Para atualizar o Banco
from src.maker_admin import make_users
from src.models.database import get_session
import uuid
# Para login
import logging
from pip._vendor import cachecontrol
import google.auth.transport.requests as goo_request
from google_auth_oauthlib.flow import Flow
from src.controller.apis.google.google_login_api import client_ifo, google_config

# Users / controllers
from src.controller.users.user_admin import Management_Admins
from src.controller.users.user_professor import Management_Professors 
from src.controller.users.user_default import Create_Account, Login_Account, Management_User_Default, check_user

# servidor
from flask import Flask, render_template, redirect, request, url_for, session, g, flash, send_from_directory, Response, abort, send_file
from werkzeug.utils import secure_filename
import requests
import uuid

# app
app = Flask(__name__, template_folder="view/templates", static_folder="view/static")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

# constantes e pasta de uploads
UPLOAD_FOLDER = os.path.join(app.static_folder, "profile_images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def make_session_from_dbuser(db_user_dict):
   
    if not db_user_dict:
        return
    session["user"] = {
        "id": str(db_user_dict.get("id")),
        "name": db_user_dict.get("name"),
        "email": db_user_dict.get("email"),
        "picture": db_user_dict.get("picture"),
        "creation_date": str(db_user_dict.get("creation_date")),
        "cred": db_user_dict.get("cred")
    }
    # extras para acesso rápido
    session["name"] = session["user"]["name"]
    session["email"] = session["user"]["email"]
    session["picture"] = session["user"]["picture"]
    session["id"] = session["user"]["id"]
    session["cred"] = session["user"]["cred"]
    session.modified = True
    
    logging.info("Sessão criada/atualizada para %s", session.get("name"))


@app.before_request
def load_user():
    
    if session.get("user"):
        user_data = session.get("user")
        if user_data:
            g.user = Management_User_Default(user_data)
        else:
            g.user = type("Anon", (), {})()  # objeto vazio ao invés de None
        if user_data.get("cred") == "admin":
            g.user = Management_Admins(g.user.get_user())
        if user_data.get("cred") == "professor":
            g.user = Management_Professors(g.user.get_user())
                     
                     
@app.route("/", methods = ["GET"])
def get_app():
    return redirect(url_for("login"))
    
    
@app.route('/login', methods=["GET", "POST"])
def login():
    if session.get("name"):
        return redirect(url_for("home_page"))

    if request.method == "GET":
        return render_template("index.html")

    login_with = request.form.get("method")
    create_new_account = request.form.get("new_account")
    logging.info("método de login: %s", login_with)

    if login_with == "google":
        return redirect(url_for("google_login"))

    if login_with == "local":
        account = {
            "name": request.form.get("name"),
            "password": request.form.get("password")
        }
        userLoged, userAccount = Login_Account.login("local", account)
        if userLoged and userAccount:
            
            try:
                user_dict = userAccount.get_user()
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            if session.get("cred") == "aluno":
                return redirect(url_for("home_page"))
            if session.get("cred") == "admin":
                return redirect(url_for("admin_page"))       
        return render_template("index.html", error="credenciais incorretas")

    if create_new_account:
        return redirect(url_for("create_account"))

    return render_template("index.html", error="Opção de login inválida.")


@app.route("/logout")
def logout():
    session.clear()
    app.logger.info("Usuário deslogado com sucesso")
    return redirect(url_for("login"))


@app.route("/login/google", methods=["GET"])
def google_login():
    authorization = google_config(redirect_by="google_login_checkout")
    if authorization:
        session["google_state"] = authorization.get("google_state")
        session["google_client_config"] = authorization.get("client_config")
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
        picture_url = account.get("picture")
    
        if picture_url and picture_url.startswith("http"):
            try:
               
                img_bytes = requests.get(picture_url).content
                
                unique_name = f"{uuid.uuid4()}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, unique_name)
    
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
    
                
                public_url = f"/profile_images/{unique_name}"
    
                print("Foto original do Google:", picture_url)
                print("Salva como:", filepath)
    
                account["picture"] = public_url
    
            except Exception as E:
                logging.error(f"Erro ao salvar foto de perfil do usuário: {E}")
        userLoged, userAccount = Login_Account.login("google", account)
        if userLoged and userAccount:
            try:
                user_dict = dict(userAccount)
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            return redirect(url_for("home_page"))
        logging.error("Login Google falhou durante Login_Account.login()")
        return redirect(url_for("login"))

    logging.error("Erro: account info google não retornada")
    return redirect(url_for("login"))


@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        name = request.form.get("name")
        password_1 = request.form.get("password_1")
        password_2 = request.form.get("password_2")
        
        checker = Create_Account()
        
        if password_1 != password_2:
                        
            return render_template("create_account.html", error="senhas não coencidem"), 400
            
        if check_user(name):
            return render_template("create_account.html", error="O nome de usuário já está sendo utilizado"), 400
        creation_method = "local"
        
        
        userLoged, userAccount = Create_Account.creator(
            creationMethod=creation_method,
            userName=name,
            email=None,
            pass1=password_1,
            pass2=password_2
        )

        if userLoged and userAccount:
            try:
                user_dict = userAccount.get_user()
            except Exception:
                user_dict = userAccount
            make_session_from_dbuser(user_dict)
            return redirect(url_for("home_page"))

    return render_template("create_account.html")


@app.route("/home")
def home_page():
    return redirect(url_for("contents"))
    """user_name = session.get("name", "Visitante")
    user_email = session.get("email", "não informado")
    return render_template("home_page.html", user_name=user_name, user_email=user_email) --> decidindo como migrar isso pra contents"""



@app.route("/user")
def user():
    total_courses = 0
    enrolled_courses = []
    if getattr(g, "user", None):
        try:
            user_data = g.user.get_user()
        except Exception:
            user_data = session.get("user")
    else:
        user_data = session.get("user")

    return render_template("user_page.html", session_user=user_data, total_courses=total_courses, enrolled_courses=enrolled_courses)


import subprocess
import os
import logging

def convert_heic_to_jpeg(source_path, dest_path, quality=90):
    """
    Converte HEIC -> JPEG usando heif-convert ou ImageMagick (fallback).
    Retorna True se bem‑sucedido.
    """
    # Tenta heif-convert (rápido e leve)
    try:
        subprocess.run(
            ["heif-convert", "-q", str(quality), source_path, dest_path],
            check=True,
            capture_output=True,
            timeout=30
        )
        logging.info(f"HEIC convertido com heif-convert: {source_path} -> {dest_path}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logging.warning(f"heif-convert falhou ou não encontrado: {e}")

    # Fallback: ImageMagick (convert)
    try:
        subprocess.run(
            ["convert", source_path, "-quality", str(quality), dest_path],
            check=True,
            capture_output=True,
            timeout=30
        )
        logging.info(f"HEIC convertido com ImageMagick: {source_path} -> {dest_path}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logging.error(f"ImageMagick também falhou: {e}")

    return False
        
@app.route("/edit_user", methods=["POST"])
def edit_user():
    if not session.get("user"):
        logging.info("Acesso negado - sem sessão")
        flash("Acesso negado.")
        return redirect("/login")

    logging.info("Processando edição de usuário")
    new_name = request.form.get("new_name")
    new_image = request.files.get("profile_image")

    # Atualização do nome
    if new_name and new_name.strip():
        ok = False
        try:
            ok = g.user.update_user(field="name", newValue1=new_name.strip())
        except Exception as e:
            logging.exception("Erro ao atualizar nome: %s", e)
            ok = False
        if not ok:
            flash("Erro ao atualizar nome.")
            return redirect("/user")
            
                    
        session["name"] = g.user.get_user_name()
        return render_template("user_page.html")             
            
    if new_image and new_image.filename != "":
        original_filename = f"{uuid.uuid4().hex}.jpg"
        is_heic = original_filename.lower().endswith(('.heic', '.heif'))
    
        if is_heic:
            # Nome final .jpg
            base, _ = os.path.splitext(original_filename)
            final_filename = base + ".jpg"
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
    
            # Salva temporário HEIC
            temp_filename = "__heic_temp_" + original_filename
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            try:
                new_image.save(temp_path)
            except Exception as e:
                logging.exception("Erro ao salvar HEIC temporário: %s", e)
                flash("Erro ao processar imagem HEIC.")
                return redirect("/user")

        # Converte HEIC -> JPEG (função externa)
            success = convert_heic_to_jpeg(temp_path, final_path)

        # Remove temporário
            try:
                os.remove(temp_path)
            except OSError:
                pass
    
            if not success:
                flash("Erro ao converter imagem HEIC. O servidor pode não ter suporte. Envie JPEG ou PNG.")
                return redirect("/user")
    
            public_url = f"/profile_images/{final_filename}"
        else:
            # Formatos comuns
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            try:
                new_image.save(filepath)
            except Exception as e:
                logging.exception("Erro ao salvar arquivo: %s", e)
                flash("Erro ao salvar imagem.")
                return redirect("/user")
            public_url = f"/profile_images/{original_filename}"
    
        # Atualiza 'picture' no banco
        ok = g.user.update_user(field="picture", newValue1=public_url)
        if not ok:
            flash("Erro ao salvar imagem no perfil.")
            return redirect("/user")
        
        session["picture"] = g.user.picture
        flash("Perfil atualizado com sucesso.")
        return render_template("user_page.html")
            
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if not session.get("user"):
        flash("Acesso negado.")
        return redirect("/login")

    if request.method == "GET":
        # A tela pronta (change_password.html) já deve existir
        return render_template("change_password.html")

    # POST: processa a troca de senha
    new_password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not new_password or not confirm_password:
        flash("Todos os campos são obrigatórios.")
        return redirect("/change_password")

    if new_password != confirm_password:
        flash("As novas senhas não coincidem.")
        return redirect("/change_password")


    # Atualiza a senha usando o método existente (newValue1 = nova senha, newValue2 = confirmação)
    ok = False
    try:
        ok = g.user.update_user(field="password", newValue1=new_password, newValue2=confirm_password)
    except Exception as e:
        logging.exception("Erro ao atualizar senha: %s", e)
        flash("Erro ao atualizar senha.")
        return redirect("/change_password")

    if not ok:
        flash("Erro ao atualizar senha.")
        return redirect("/change_password")

    # Recarrega sessão (se necessário)
    try:
        updated = check_user(g.user.userId, collumn="id")
        updated_dict = dict(updated) if not isinstance(updated, dict) else updated
        make_session_from_dbuser(updated_dict)
    except Exception:
        pass

    flash("Senha alterada com sucesso!")
    return redirect("/user")    
    

@app.route("/edit_user/delete_picture", methods=["POST", "GET"])
def delete_picture():
    print(session.get("picture"))
    if not session.get("picture"):
        return render_template("user_page.html")
    img = session.get("picture")
    if not img.startswith("/profile_images/"):
        return render_template("user_page.html")
    img = os.path.join(app.static_folder, "profile_images", os.path.basename(img))
    print(img)
   
    # Apaga o arquivo se existir
    if os.path.exists(img):
        print("agora entra")
        os.remove(img)
        try:
            print("antiga", g.user.picture)
            if g.user.update_user("picture", None):
                
                session["picture"] = g.user.picture
                
                
                return render_template("exito.html")
        except Exception as E:
            logging.error(f"erro ao tentar apagar imagem {E}")
            return render_template("user_page.html")
    
    return render_template("user_page.html")


@app.route("/delete_account", methods=["GET", "POST"])
def delete_account_page():
    if not session.get("user"):
        flash("Acesso negado.")
        return redirect("/login")

    if request.method == "GET":
        return render_template("delete_account.html")

    # POST: processa a exclusão
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not password or not confirm_password:
        flash("Preencha todos os campos.")
        return redirect("/delete_account")

    if password != confirm_password:
        flash("As senhas não coincidem.")
        return redirect("/delete_account")

    # Verifica se a senha está correta (implementação depende do seu modelo)
    try:
        print("entro??????????????")
        account = {
            "name": g.user.get_user_name(),
            "password": request.form.get("password")
        }
        userLoged, userAccount = Login_Account.login("local", account)
        if not userLoged or not userAccount:
            
            flash("Senha incorreta.")
            return redirect("/delete_account")
    except AttributeError:
        
            return redirect("/delete_account")

    # Exclui o usuário (supondo que exista um método delete())
    try:
        g.user.delete_user()
        
        session.clear()
        flash(">>>>>>>***(Conta excluída com sucesso.")
        return redirect("/login")
    except Exception as e:
        logging.exception("Erro ao excluir conta: %s", e)
        flash("Erro ao excluir conta. Tente novamente.")
        return redirect("/delete_account")


    print("aaaaa")        

@app.route("/contents", methods = ["GET", "POST"])
def contents():
    
    try:
        contents = g.user.get_all_contents()
        return render_template("contents.html", contents = contents)
        
    except Exception as e:
        return f"Erro ao carregar conteúdos: {e}", 500  
@app.route("/contents/view/<content_id>", methods=["GET"])
def get_file(content_id):

    content = g.user.get_content_by_id(content_id)
    
    if not content:
        abort(404)

    return send_file(
        BytesIO(content.get("pdf")),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{content.get('title')}.pdf"
    )


@app.route("/contents/content/<content_id>", methods=["GET"])
def content_buss(content_id):
    
    try:
        content = g.user.get_content_by_id(content_id)
    except Exception as e:
        logging.error("Erro ao buscar conteúdo individual: %s", e)
        abort(404)

    if not content:
        abort(404)
    return render_template("content_view.html", content=content)

                
@app.route("/admin")
def admin_page():
    if session.get("cred")== "admin":
        users = g.user.all_users()
        
        return render_template("admin_page.html", users=users)
    return render_template("index.html")

#MELHORAR NOME DA ROTA
@app.route("/admin/create", methods=["POST"])
def admin_create_user():
    nome = request.form.get("nome")
    cred = request.form.get("cred")
    senha = request.form.get("password")
    confirm = request.form.get("confirm")
    checker = Create_Account()
    if checker:
        if senha != confirm:
                        
            return render_template("admin_page.html", error="senhas não coencidem"), 400
            
        if check_user(nome):
            return render_template("admin_page.html", error="O nome de usuário já está sendo utilizado"), 400
        
        user ={
            "name":nome,
            "cred":cred,
            "password": senha,
            "confirm": confirm}
        print(user)
        if g.user.create_user_by_admin(user.get("name"), user.get("password"), user.get("confirm"), user.get("cred")):
            logging.info("ação bem sucedida")
        
    return redirect(url_for("admin_page"))

#MELHAR NOME DA ROTA
@app.route("/admin/edit/<user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):

    if request.method == "POST":
        
        new_name = request.form.get("nome")
        print(new_name)
        new_pass = request.form.get("senha")
        confirm_pass = request.form.get("confirm_pass")
        new_cred = request.form.get("cred")
        if new_name.strip() == "":
            logging.info("Nome não pode ser um espaço em branco")
            return redirect(url_for("admin_page"))
            
        if new_name:
            g.user.update_user_by_admin("name", new_name, None, user_id)
            
            
        if (new_pass and confirm_pass) and (new_pass == confirm_pass):
            g.user.update_user_by_admin("password", new_pass, confirm_pass, user_id)      
        if new_cred:
            g.user.update_user_by_admin("cred", new_cred, None, user_id)
            print(session.get("cred"))
        return redirect(url_for("admin_page"))
    
    user = g.user.get_user_by_admin(userId = user_id)
    print(user)
    return render_template("admin_edit_user.html", user=user.get("name"))

#MELHORAR NOME DA ROTA
@app.route("/admin/delete/<user_id>", methods=["POST"])
def admin_delete_user(user_id):
        
    g.user.delete_user_by_admin(user_id)
    return redirect(url_for("admin_page"))
    
    
@app.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    if request.method == "POST":
        if session.get("cred") in ("admin", "professor"):
            
            content_name = request.form.get("content_name", "").strip()
            description = request.form.get("description", "").strip()
            file = request.files.get("file")
            
            
            print("FILES RECEBIDOS:", request.files)
            
            if len(content_name) < 15:
                content_name = None
                return render_template("publish_content.html", error = "Nome de conteúdo muito curto")
    

            if len(description) < 50:
                description = None
                return render_template("publish_content.html", error = "Descrição de conteúdo muito curtq")
            pdf_bytes = None

            if not file:
                description = None
                return render_template("publish_content.html", error = "Nenhuk documento selecionado")
                
            if file and file.filename.lower().endswith(".pdf"):
                pdf_bytes = file.read()

            if pdf_bytes and description and content_name:

                content = {
                    "title": content_name,
                    "desc": description,
                    "pdf": pdf_bytes
                }
                upload = False
                author = False
                if session.get("cred") == "admin":
                    author = request.form.get("author")
                    author = g.user.get_user_by_admin(author)
                    if author and author.get("name"):
                        upload = g.user.publish_content_by_admin(content, author.get("name"))
                
                elif session.get("cred") == "professor":
                    
                    author = g.user.get_user_name()
                    if author == session.get("name"):
                        if author:
                            upload = g.user.publish_content_by_professor(content, author)
                    else:
                        author = False
                       
                if not author:
                   
                    return render_template("publish_content.html", error = "Nome de autor não existe")
                
                if not pdf_bytes:
                    return render_template("publish_content.html", error = "Formato inválido para documento")
                                                
                if not upload:
                    print(upload)                                
                    return render_template("publish_content.html", error = "Não foi possível fazer upload do conteúdo, tente novamente.")
                                   
            return render_template("exito.html")
                
                
    return render_template("publish_content.html")
            
    
@app.route("/contents/publications", methods = ["GET"])
def get_publications():
    if session.get("cred") == "professor" or session.get("cred") == "admin":
        if session.get("cred") == "professor":
            publications = g.user.select_contents_by_publisher_id()
        if session.get("cred") == "admin":
            publications = g.user.get_all_contents()
        return render_template("my_publications.html", publications = publications)


@app.route("/contents/publications/selec_content/<content_id>", methods=["POST", "GET"])
def select_content(content_id):
    if session.get("cred") != "professor" and session.get("cred") != "admin" :
        return redirect(url_for("login"))
    if session.get("cred") == "professor":
        content = g.user.professor_get_content_by_id(content_id)
    if session.get("cred") == "admin":
        content = g.user.get_content_by_admin(content_id)
    if not content:
        return redirect(url_for("get_publications"))

    return render_template("edit_content.html", content=content)


@app.route("/contents/publications/selec_content/edit/<content>", methods = ["POST", "GET"])
def edit_content(content):
    print("credencial:", session.get("cred"))
    if session.get("cred") == "professor" or session.get("cred") == "admin":
        if session.get("cred") == "admin":
            content = g.user.get_content_by_admin(content)
        if session.get("cred") == "professor":
            content = g.user.professor_get_content_by_id(content)
            
        
        if content:                    
            new_content_title = request.form.get("new_title")
            new_content_desc = request.form.get("new_desc")
            new_content_file = request.files.get("file")
            
            action = False        
            if new_content_title:
                if new_content_title.strip() != "" or len(new_content_title) > 15:
                    if content.get("id"):
                        if session.get("cred") == "professor":
                            action = g.user.update_contents_by_id("title", content.get("id"), new_content_title)
                        if session.get("cred") == "admin":
                            action = g.user.update_contents_by_admin("title", content.get("id"), new_content_title)
                if not action:
                    print("título muito curto")
                    return render_template("edit_content.html", content = content, error = "título muito curto")                  
                        
            if new_content_desc:
                action = False
                if new_content_desc.strip() != "" or len(new_content_desc) > 50:
                    if content.get("id"):
                        if session.get("cred") == "professor":
                            action = g.user.update_contents_by_id("desc", content.get("id"), new_content_desc)
                        if session.get("cred") == "admin":
                            action = g.user.update_contents_by_admin("desc", content.get("id"), new_content_desc)         
                if not action:
                    print("descrucao curta")
                    return render_template("edit_content.html", content = content, error = "descrição muito curta")
                
            if new_content_file:
                pdf_bytes = None
                action = False
                if new_content_file and new_content_file.filename.lower().endswith(".pdf"):
                    pdf_bytes = new_content_file.read()
                    if session.get("cred") == "professor":
                        action = g.user.update_contents_by_id("pdf", content.get("id"), pdf_bytes)
                    if session.get("cred") == "admin":
                            action = g.user.update_contents_by_admin("pdf", content.get("id"), pdf_bytes)                                                            
                if not action: return render_template("edit_content.html", content = content, error = "Formato indevido para pdf")
            if action:
                get_session().expire_all()
                return render_template("exito.html")
    return redirect(url_for("login"))

        
@app.route("/delete_content/<content_id>", methods = ["POST"])
def delete_content(content_id):
    if session.get("cred") == "professor" or session.get("cred") == "admin":
        if content_id:
            if session.get("cred") == "professor":
                action = g.user.delete_contents_by_id(content_id)
            if session.get("cred") == "admin":
                action = g.user.delete_contents_by_admin(content_id)
            if not action:
                return render_template("edit_content.html",content=content_id, error = "não foi possível excluir arquivo")
        return redirect(url_for("get_publications"))
    return redirect(url_for("login"))
   


if __name__ == '__main__':
    
    try:
        from src.models.database.creator_database import create_db
        create_db()
        make_users()#--> insere 3 usuarios:
        """
            admin : JAYRON,
            professor: Frederico
            aluno: bolsonaro
            todas as senhas são 1081514Jh
            só é possível criar novos admins e novos professores com a conta de admin 
            account = {
            "name": request.form.get("name"),
            "password": request.form.get("password")
        } -> cria outro usuario usando o nome do logado e a senha que ele digitou, se os dois combinarem entao passa.
            
            """
            
    except Exception as E:
        logging.info(f"create_db não executado ou já existente: {E}")
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app.run(debug=True, port=8080, host = "0.0.0.0")