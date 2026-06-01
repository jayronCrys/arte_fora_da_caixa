import logging

from flask import g, redirect, render_template, request, session, url_for, jsonify

from src.controller.users.user_default import Create_Account, check_user

from . import admin_bp


def _is_admin():
    return session.get("cred") == "admin"


# ── Painel ────────────────────────────────────────────────────────────────────

@admin_bp.route("/admin")
def admin_page():
    if not _is_admin():
        return render_template("index.html")
    users = g.user.all_users()
    return render_template("admin_page.html", users=users)


# ── CRUD de usuários pelo admin ───────────────────────────────────────────────

@admin_bp.route("/admin/create", methods=["POST"])
def admin_create_user():
    if not _is_admin():
        return redirect(url_for("auth.login"))

    nome = request.form.get("nome")
    cred = request.form.get("cred")
    senha = request.form.get("password")
    confirm = request.form.get("confirm")
    
    if not senha or not nome:
        return render_template("admin_page.html", error="todos os campos são obrigatórios"), 400
        
    if senha != confirm:
        return render_template("admin_page.html", error="senhas não coincidem"), 400

    if check_user(nome):
        return render_template("admin_page.html", error="O nome de usuário já está sendo utilizado"), 400

    if g.user.create_user_by_admin(nome, senha, confirm, cred):
        logging.info("Usuário %s criado pelo admin", nome)

    return redirect(url_for("admin.admin_page"))


@admin_bp.route("/admin/edit/<user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
    if not _is_admin():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        new_name = request.form.get("nome", "")
        new_pass = request.form.get("senha")
        confirm_pass = request.form.get("confirm_pass")
        new_cred = request.form.get("cred")

        if new_name.strip() == "":
            logging.info("Nome não pode ser espaço em branco")
            return redirect(url_for("admin.admin_page"))

        if new_name:
            g.user.update_user_by_admin("name", new_name, None, user_id)

        if new_pass and confirm_pass and new_pass == confirm_pass:
            g.user.update_user_by_admin("password", new_pass, user_id)

        if new_cred:
            g.user.update_user_by_admin("cred", new_cred, None, user_id)

        return redirect(url_for("admin.admin_page"))

    user = g.user.get_user_by_admin(userId=user_id)
    return render_template("admin_edit_user.html", user=user.get("name"))


@admin_bp.route("/admin/delete/<user_id>", methods=["POST"])
def admin_delete_user(user_id):
    
    if not _is_admin():
        return redirect(url_for("auth.login"))

    delete = g.user.delete_user_by_admin(user_id)
    if not delete:
        return render_template("admin_edit_user.html", error = "erro ao excluir usuário"), 404
        
    return redirect(url_for("admin.admin_page"))




#── STATISTICAS PELO ADMIN ───────────────────────────────────────────────
@admin_bp.route("/admin/redirector", methods=["GET"])
def redirector():
    return render_template("dashboard.html")
@admin_bp.route("/admin/analytics", methods=["GET"])
def app_analytics():
    if not _is_admin():
        return redirect(url_for("auth.login"))

    analytics = g.user.get_plataform_analytics()
    if analytics:
        return jsonify(analytics), 200
        
    return redirect(url_for("admin.admin_page"))
    
    
@admin_bp.route("/admin/analytics/professor/<professor_id>", methods=["GET"])
def professor_analytics(professor_id):
    if not _is_admin():
        return redirect(url_for("auth.login"))
        
    analytic = g.user.get_professor_analytics(professor_id)
    if analytic:
        return jsonify(analytic), 200
    return redirect(url_for("admin.admin_page"))    
            
@admin_bp.route("/admin/analytics/content/<content_id>", methods=["GET"])
def content_analytics(content_id):
    if not _is_admin():
        return redirect(url_for("auth.login"))
        
    content_analytics = g.user.get_content_analytics_by_admin(content_id)
    if content_analytics:
          return jsonify(content_analytics), 200
    return redirect(url_for("admin.admin_page"))              
              