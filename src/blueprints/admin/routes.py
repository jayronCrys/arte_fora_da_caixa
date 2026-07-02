import logging

from flask import g, redirect, render_template, request, session, url_for, jsonify, flash

from src.controller.users.user_default import Create_Account, check_user

from . import admin_bp


def _is_admin():
    return session.get("cred") == "admin"


# ── Painel ────────────────────────────────────────────────────────────────────

@admin_bp.route("/admin/admin_page")
def admin_page():
    if not _is_admin():
        return render_template("index.html")
    
    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filtros
    name = request.args.get('name', None, type=str)
    permission = request.args.get('permission', None, type=str)
    has_email = request.args.get('has_email', None, type=str)
    sort_by = request.args.get('sort_by', 'name_asc', type=str)
    
    # Converte 'with'/'without' para boolean
    if has_email == 'with':
        has_email = True
    elif has_email == 'without':
        has_email = False
    else:
        has_email = None  # não filtra
    
    result = g.user.all_users(
        page=page,
        per_page=per_page,
        name=name if name else None,
        permission=permission if permission != 'all' else None,
        has_email=has_email,
        sort_by=sort_by
    )
    
    if not result:
        flash("Erro ao carregar usuários.", "error")
        return redirect(url_for('admin.admin_page'))
    
    role_counts = g.user.count_users_by_role()
    
    return render_template(
        "admin_page.html",
        users=result['users'],
        pagination=result,
        role_counts=role_counts,
        current_filters={
            'name': name or '',
            'permission': permission or 'all',
            'has_email': has_email if has_email is not None else 'all',
            'sort_by': sort_by
        }
    )
    
    
# ── CRUD de usuários pelo admin ───────────────────────────────────────────────
@admin_bp.route("/admin/admin_page/search")
def admin_search_users():
    if not _is_admin():
        return "Acesso negado", 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    name = request.args.get('name', None, type=str)
    permission = request.args.get('permission', None, type=str)
    has_email = request.args.get('has_email', None, type=str)
    sort_by = request.args.get('sort_by', 'name_asc', type=str)

    # Converte has_email
    if has_email == 'with':
        has_email = True
    elif has_email == 'without':
        has_email = False
    else:
        has_email = None
    print("PERMISSION>>>>>>>>>>>" , permission)
    result = g.user.all_users(
        page=page, per_page=per_page,
        name=name if name else None,
        permission=permission if permission != 'all' else None,
        has_email=has_email,
        sort_by=sort_by
    )
    if not result:
        return "Erro ao buscar usuários", 500

    # Retorna apenas o HTML parcial da tabela
    return render_template(
        "admin_users_table.html",
        users=result['users'],
        pagination=result
    )
    
@admin_bp.route("/admin/create", methods=["POST"])
def admin_create_user():
    if not _is_admin():
        return jsonify({"success": False, "error": "Acesso negado."}), 403

    nome = request.form.get("nome", "").strip()
    cred = request.form.get("cred")
    senha = request.form.get("password")
    confirm = request.form.get("confirm")

    if not nome or not senha or not confirm:
        return jsonify({"success": False, "error": "Todos os campos são obrigatórios."}), 400

    if senha != confirm:
        return jsonify({"success": False, "error": "As senhas não coincidem."}), 400

    if len(senha) < 6:
        return jsonify({"success": False, "error": "A senha deve ter no mínimo 6 caracteres."}), 400

    if check_user(nome):
        return jsonify({"success": False, "error": "O nome de usuário já está cadastrado."}), 400

    if not g.user.create_user_by_admin(nome, senha, cred):
        return jsonify({"success": False, "error": "Erro ao criar usuário. Tente novamente."}), 500

    logging.info("Usuário %s criado pelo admin", nome)
    return jsonify({"success": True, "message": f"Usuário '{nome}' criado com sucesso."}), 200


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
            g.user.update_user_by_admin("name", new_name, user_id)

        if new_pass and confirm_pass and new_pass == confirm_pass:
            g.user.update_user_by_admin("password", new_pass, user_id)

        if new_cred:
            g.user.update_user_by_admin("cred", new_cred, user_id)

        return redirect(url_for("admin.admin_page"))

    user = g.user.get_user_by_id(userId=user_id)
    inscrip = g.user.get_user_inscription_by_admin(userId=user_id)
    return render_template("admin_edit_user.html", user=user, inscrip=inscrip)


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
    return render_template("dashboard.html", user=g.user.userId)


@admin_bp.route("/admin/analytics", methods=["GET"])
def app_analytics():
    if not _is_admin():
        return redirect(url_for("auth.login"))

    analytics = g.user.get_plataform_analytics()
    if analytics:
        return jsonify(analytics), 200
        
    return redirect(url_for("admin.admin_page"))
    
    
@admin_bp.route("/admin/analytics/professor/<professor_name>", methods=["GET"])
def professor_analytics(professor_name):
    if not _is_admin():
        return redirect(url_for("auth.login"))
        
    analytic = g.user.get_professor_analytics(professor_name)
    if analytic:
        return jsonify(analytic), 200
    return redirect(url_for("admin.admin_page"))    
            

@admin_bp.route("/admin/analytics/contents_by_id/<content_id>", methods=["GET", "POST"])
def get_content_analytics(content_id):
    if not content_id or not _is_admin():
        return redirect(url_for("auth.login"))
                
    content = g.user.get_content_analytics_by_admin(content_id)
    print("<!>"*10, content_id, type(content_id))
    if content:
        return jsonify(content), 200
    return [], 404        
    
@admin_bp.route("/admin/analytics/contents_by_name/<content_name>", methods=["POST", "GET"])
def redirect_analytics_content_by_name(content_name):
    if not _is_admin():
        return redirect(url_for("auth.login"))
        
    print("CONTENT_NAME", {content_name})
    contents = g.user.get_content_by_name(content_name)
    
    if len(contents) == 1 and contents[0]["title"] == content_name:
        print("*"*10, type(contents[0]))
        return redirect(url_for("admin.get_content_analytics", content_id=contents[0]["id"]))
    
    # Adicionado: Retorno claro de erro caso o if não seja satisfeito
    return jsonify({"error": "Conteúdo não encontrado ou múltiplos resultados encontrados"}), 404
