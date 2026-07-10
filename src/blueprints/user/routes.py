import logging

from Configs.profile_images import profile_image_save
from flask import (
    flash, g,
    redirect,
    render_template,
    request, session,
    url_for
)
from storage.storage_host import delete_user_profile_image
from src.controller.users.user_default import Login_Account, check_user
from src.extensions import make_session_from_dbuser
from . import user_bp

logger = logging.getLogger(__name__)


def _require_login():
    if not session.get("user"):
        flash("Acesso negado.")
        return redirect(url_for("auth.login"))
    return None


# ── Perfil ────────────────────────────────────────────────────────────────────

@user_bp.route("/user")
def user():

    if guard := _require_login():
        return guard

    if getattr(g, "user", None):
        try:
            user_data    = g.user.get_user()
        except Exception:
            user_data    = session.get("user")

        enrolled_courses = g.user.get_my_courses()
    else:
        user_data        = session.get("user")
        enrolled_courses = None

    if not enrolled_courses:
        total_courses    = 0
        enrolled_courses = []
    else:
        total_courses    = len(enrolled_courses)

    return render_template(
        "user_page.html",
        session_user     = user_data,
        total_courses    = total_courses,
        enrolled_courses = enrolled_courses,
    )


@user_bp.route("/edit_user", methods=["POST"])
def edit_user():

    if guard := _require_login(): return guard

    new_name  = request.form.get("new_name")
    new_image = request.files.get("profile_image")

    # ── Atualizar nome ────────────────────────────────────────────────────────
    if new_name and new_name.strip():
        ok = False
        try:
            ok = g.user.update_user(field="name", newValue1=new_name.strip())
        except Exception as exc:
            logger.exception("Erro ao atualizar nome: %s", exc)
        if not ok:
            flash("Erro ao atualizar nome.")
            return redirect(url_for("user.user"))
        session["name"] = g.user.get_user_name()
        return render_template("user_page.html")

    # ── Atualizar imagem ──────────────────────────────────────────────────────
    if new_image and new_image.filename != "":
        image_name = new_image.filename
        image_file = new_image.read()
        is_heic    = new_image.filename.lower().endswith((".heic", ".heif"))

        if is_heic:
            flash("formato de imagem inválido, envie uma imagem nos formatos: jpg, png, jpeg.")

        else:
            
            try:
                image_path = profile_image_save(session["id"], session["picture"], image_name, image_file)

            except Exception as exc:
                logger.exception("Erro ao salvar arquivo: %s", exc)
                flash("Erro ao salvar imagem.")
                return redirect(url_for("user.user"))
            
            public_url = f"/profile_images/{image_name}"


        if not g.user.update_user(field="picture", newValue1=image_path):
            flash("Erro ao salvar imagem no perfil.")
            return redirect(url_for("user.user"))

        session["picture"] = g.user.picture
        flash("Perfil atualizado com sucesso.")
        return render_template("user_page.html")

    # Nem nome nem imagem foram enviados.
    flash("Nenhuma alteração enviada.")
    return redirect(url_for("user.user"))

@user_bp.route("/edit_user/delete_picture", methods=["POST"])
def delete_picture():

    if guard := _require_login(): return guard

    img_path = session.get("picture")
    if not img_path:
        flash("Nenhuma imagem de perfil para remover.")
        return redirect(url_for("user.user"))
    
    try:
        # Tenta deletar a imagem do storage
        delete_success = delete_user_profile_image(session['id'], img_path)
        
        if delete_success:
            # Atualiza o registro no banco de dados
            update_success = g.user.update_user("picture", None)
            
            if update_success:
                # Atualiza a sessão com o novo estado
                session["picture"] = g.user.picture
                flash("Foto de perfil removida com sucesso!")
                return redirect(url_for("user.user"))
            else:
                # Falha ao atualizar o banco, mas a imagem já foi deletada
                logger.error(f"Imagem deletada do storage mas falha ao atualizar banco para usuário {session['id']}")
                flash("Erro ao atualizar registro. A imagem foi removida, mas pode ser necessário recarregar a página.")
                return redirect(url_for("user.user"))
        else:
            # Falha ao deletar a imagem
            flash("Não foi possível remover a imagem. Tente novamente.")
            return redirect(url_for("user.user"))
            
    except Exception as exc:
        logger.error(f"Erro ao apagar imagem do usuário {session.get('id')}: {exc}")
        flash("Houve um erro ao tentar remover sua imagem. Por favor, tente novamente.")
        return redirect(url_for("user.user"))
# ── Senha ─────────────────────────────────────────────────────────────────────

@user_bp.route("/change_password", methods=["GET", "POST"])
def change_password():

    if guard := _require_login(): return guard

    if request.method == "GET":
        return render_template("change_password.html")

    new_password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not new_password or not confirm_password:
        flash("Todos os campos são obrigatórios.")
        return redirect(url_for("user.change_password"))

    if new_password != confirm_password:
        flash("As novas senhas não coincidem.")
        return redirect(url_for("user.change_password"))

    ok = False
    try:
        ok = g.user.update_user(field="password", newValue1=new_password, newValue2=confirm_password)
    except Exception as exc:
        logger.exception("Erro ao atualizar senha: %s", exc)
        flash("Erro ao atualizar senha.")
        return redirect(url_for("user.change_password"))

    if not ok:
        flash("Erro ao atualizar senha.")
        return redirect(url_for("user.change_password"))

    try:
        updated      = check_user(g.user.userId, column="id")
        updated_dict = dict(updated) if not isinstance(updated, dict) else updated
        make_session_from_dbuser(updated_dict)
    except Exception as exc:
        logger.error("Erro ao atualizar sessão após troca de senha: %s", exc)

    flash("Senha alterada com sucesso!")
    return redirect(url_for("user.user"))


# ── Excluir conta ─────────────────────────────────────────────────────────────

@user_bp.route("/delete_account", methods=["GET", "POST"])
def delete_account_page():

    if guard := _require_login(): return guard

    if request.method == "GET":
        return render_template("delete_account.html")

    password         = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not password or not confirm_password:
        flash("Preencha todos os campos.")
        return redirect(url_for("user.delete_account_page"))

    if password != confirm_password:
        flash("As senhas não coincidem.")
        return redirect(url_for("user.delete_account_page"))

    try:
        account = {"name": g.user.get_user_name(), "password": password}
        userLoged, userAccount = Login_Account.login("local", account)
        if not userLoged or not userAccount:
            flash("Senha incorreta.")
            return redirect(url_for("user.delete_account_page"))
    except AttributeError:
        return redirect(url_for("user.delete_account_page"))

    try:
        g.user.delete_user()
        session.clear()
        flash("Conta excluída com sucesso.")
        return redirect(url_for("auth.login"))
    
    except Exception as exc:
        logger.exception("Erro ao excluir conta: %s", exc)
        flash("Erro ao excluir conta. Tente novamente.")
        return redirect(url_for("user.delete_account_page"))