import logging
import os
import uuid

from flask import (
    current_app,
    flash, g,
    redirect,
    render_template,
    request, session,
    url_for
)

from src.controller.users.user_default import Login_Account, check_user
from src.extensions import convert_heic_to_jpeg, make_session_from_dbuser
from . import user_bp

logger = logging.getLogger(__name__)


def _require_login():
    """Retorna redirect se não houver sessão, None caso contrário."""
    if not session.get("user"):
        flash("Acesso negado.")
        return redirect(url_for("auth.login"))
    return None


# ── Perfil ────────────────────────────────────────────────────────────────────

@user_bp.route("/user")
def user():
    guard = _require_login()
    if guard:
        return guard

    if getattr(g, "user", None):
        try:
            user_data = g.user.get_user()
        except Exception:
            user_data = session.get("user")

        enrolled_courses = g.user.get_my_courses()
    else:
        user_data = session.get("user")
        enrolled_courses = None

    if not enrolled_courses:
        total_courses = 0
        enrolled_courses = []
    else:
        total_courses = len(enrolled_courses)

    return render_template(
        "user_page.html",
        session_user=user_data,
        total_courses=total_courses,
        enrolled_courses=enrolled_courses,
    )


@user_bp.route("/edit_user", methods=["POST"])
def edit_user():
    guard = _require_login()
    if guard:
        return guard

    new_name = request.form.get("new_name")
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
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        original_filename = f"{uuid.uuid4().hex}.jpg"
        is_heic = new_image.filename.lower().endswith((".heic", ".heif"))

        if is_heic:
            base, _ = os.path.splitext(original_filename)
            final_filename = base + ".jpg"
            final_path = os.path.join(upload_folder, final_filename)
            temp_path = os.path.join(upload_folder, "__heic_temp_" + original_filename)
            try:
                new_image.save(temp_path)
            except Exception as exc:
                logger.exception("Erro ao salvar HEIC temporário: %s", exc)
                flash("Erro ao processar imagem HEIC.")
                return redirect(url_for("user.user"))

            success = convert_heic_to_jpeg(temp_path, final_path)
            try:
                os.remove(temp_path)
            except OSError:
                pass

            if not success:
                flash("Erro ao converter HEIC. Envie JPEG ou PNG.")
                return redirect(url_for("user.user"))
            public_url = f"/profile_images/{final_filename}"
        else:
            filepath = os.path.join(upload_folder, original_filename)
            try:
                new_image.save(filepath)
            except Exception as exc:
                logger.exception("Erro ao salvar arquivo: %s", exc)
                flash("Erro ao salvar imagem.")
                return redirect(url_for("user.user"))
            public_url = f"/profile_images/{original_filename}"

        ok = g.user.update_user(field="picture", newValue1=public_url)
        if not ok:
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
    guard = _require_login()
    if guard:
        return guard

    img_path = session.get("picture")
    if not img_path or not img_path.startswith("/profile_images/"):
        return render_template("user_page.html")

    full_path = os.path.join(
        current_app.static_folder, "profile_images", os.path.basename(img_path)
    )
    if os.path.exists(full_path):
        os.remove(full_path)
        try:
            if g.user.update_user("picture", None):
                session["picture"] = g.user.picture
                return render_template("exito.html")
        except Exception as exc:
            logger.error("Erro ao apagar imagem: %s", exc)

    return render_template("user_page.html")


# ── Senha ─────────────────────────────────────────────────────────────────────

@user_bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    guard = _require_login()
    if guard:
        return guard

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
        updated = check_user(g.user.userId, column="id")
        updated_dict = dict(updated) if not isinstance(updated, dict) else updated
        make_session_from_dbuser(updated_dict)
    except Exception as exc:
        logger.error("Erro ao atualizar sessão após troca de senha: %s", exc)

    flash("Senha alterada com sucesso!")
    return redirect(url_for("user.user"))


# ── Excluir conta ─────────────────────────────────────────────────────────────

@user_bp.route("/delete_account", methods=["GET", "POST"])
def delete_account_page():
    guard = _require_login()
    if guard:
        return guard

    if request.method == "GET":
        return render_template("delete_account.html")

    password = request.form.get("password")
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