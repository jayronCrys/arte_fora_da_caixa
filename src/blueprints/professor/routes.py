import logging

from flask import g, redirect, render_template, request, session, url_for, jsonify

from src.controller.users.user_default import Create_Account, check_user

from . import professor_bp


def _is_professor():
    return session.get("cred") == "professor"


# ── Painel ────────────────────────────────────────────────────────────────────
@professor_bp.route("/professor/my_analytics")
def profille_analytics_professor():
    if not _is_professor():
        return redirect(url_for("auth.login"))
        
    my_analytics = g.user.get_my_analytics()
    
    if not my_analytics:
        return render_template("user_page.html", error="não foi possível exibir sua análise de perfil"), 400
    #pesquisar se a lista de é tratada no front ou nos endpoints        
    return jsonify(my_analytics), 200

                                  
@professor_bp.route("/professor/analytics/contents/<content_id>")
def content_analytics_professor(content_id):
    
    if not _is_professor():
        return redirect(url_for("auth.login"))
        
    if content_id:
        content_analytics = g.user.get_content_analytics_by_admin(content_id)
        #pesquisar se a lista de é tratada no front ou nos endpoints        
        return jsonify(content_analytics), 200
        
    return render_template("contents.html", error="não foi possível exibir análise desse conteúdo"), 400

                                               