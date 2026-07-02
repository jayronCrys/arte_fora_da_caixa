import logging
from functools import wraps

from flask import flash, g, redirect, session, url_for, jsonify

from . import professor_bp

logger = logging.getLogger(__name__)


def _is_professor():
    return session.get("cred") == "professor"


def professor_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _is_professor():
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper


# ── Painel ────────────────────────────────────────────────────────────────────
@professor_bp.route("/professor/my_analytics", methods=["GET"])
@professor_required
def profille_analytics_professor():
    my_analytics = g.user.get_my_analytics()

    if not my_analytics:
        # Evita renderizar user_page.html sem o contexto completo que ela
        # espera (session_user, total_courses, enrolled_courses) — o que
        # gera UndefinedError no Jinja. Redireciona para a rota que monta
        # esse contexto corretamente.
        flash("Não foi possível exibir sua análise de perfil.")
        return redirect(url_for("user.user"))

    return jsonify(my_analytics), 200


@professor_bp.route("/professor/analytics/contents/<content_id>")
@professor_required
def content_analytics_professor(content_id):
    if not content_id:
        # Mesmo motivo: contents.html não pode ser renderizado com contexto
        # parcial. Redireciona para a rota principal, que já monta o
        # contexto completo (enrolled_contents, total_pages, publications...).
        flash("Não foi possível exibir análise desse conteúdo.")
        return redirect(url_for("contents.contents"))

    try:
        content_analytics = g.user.get_content_analytics(content_id)
    except Exception as exc:
        logger.error("Erro ao obter analytics do conteúdo %s: %s", content_id, exc)
        flash("Não foi possível exibir análise desse conteúdo.")
        return redirect(url_for("contents.contents"))

    # TODO: confirmar se a filtragem/tratamento da lista de analytics
    # acontece no front-end ou deveria ser feita aqui antes do jsonify.
    return jsonify(content_analytics), 200