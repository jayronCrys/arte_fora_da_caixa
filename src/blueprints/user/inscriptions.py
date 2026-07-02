import logging
from flask import abort, g, redirect, render_template, request, send_file, session, url_for, jsonify, Blueprint
from . import inscriptions_bp
from src.blueprints.contents.routes import get_banner

logger = logging.getLogger(__name__)


def _is_logged_in():
    return getattr(g, "user", None) is not None


@inscriptions_bp.route('/subscribe/<content_id>', methods=['POST'])
def subscribe(content_id):
    """
    Consumida via fetch() pelo botão de inscrição (handleSubscribeToggle).
    Sempre retorna JSON — nunca redirect() — pois um redirect() vira apenas
    o corpo textual da resposta do fetch, não uma navegação real do
    navegador (é isso que causava a página "Redirecting..." aparecendo crua).
    A navegação real, se necessária, deve ser feita pelo JS usando o
    campo `redirect_url` da resposta.
    """
    if not _is_logged_in():
        return jsonify({'error': 'É necessário estar logado para se inscrever.'}), 401

    try:
        if g.user.new_inscription(content_id):
            return jsonify({
                'success': True,
                'redirect_url': url_for("contents.content_buss", content_id=content_id),
            }), 200
        return jsonify({'error': 'Conteúdo não encontrado'}), 404
    except Exception as e:
        logger.error(f"Erro ao inscrever usuário no conteúdo {content_id}: {e}")
        return jsonify({'error': 'Conteúdo não encontrado'}), 404


def unsubscribe(content_id):
    try:
        if g.user.remove_inscription(content_id):
            return True
        return False
    except Exception as e:
        logger.error(f"Erro em unsubscribe para o conteúdo {content_id}: {e}")
        return False


@inscriptions_bp.route('/user/unsubscribe/<content_id>', methods=['DELETE', 'POST'])
def unsubscribe_by_my_content_pages(content_id):
    """Usada a partir de 'Meus Cursos' (my_courses.html) — mantém render direto."""
    if not _is_logged_in():
        return jsonify({'error': 'É necessário estar logado para se desinscrever.'}), 401

    if unsubscribe(content_id):
        return render_template("contents.my_inscriptions.html")
    return redirect(url_for("manager_course", course=content_id))


@inscriptions_bp.route('/unsubscribe/<content_id>', methods=['DELETE', 'POST'])
def unsubscribe_preview(content_id):
    """
    Consumida via fetch() pelo mesmo botão de toggle de inscrição — mesmo
    motivo do 'subscribe': sempre JSON, nunca redirect().
    """
    if not _is_logged_in():
        return jsonify({'error': 'É necessário estar logado para se desinscrever.'}), 401

    if not content_id:
        return jsonify({'error': 'Conteúdo não encontrado'}), 404

    if not unsubscribe(content_id):
        return jsonify({'error': 'Não foi possível se desinscrever do conteúdo'}), 404

    return jsonify({
        'success': True,
        'redirect_url': url_for("contents.content_buss", content_id=content_id),
    }), 200


def get_my_courses():
    inscriptions = g.user.my_inscriptions()
    courses = []
    try:
        for inscription in inscriptions:
            course = g.user.get_content_by_id(inscription["content_id"])
            course["banner"] = get_banner(inscription["content_id"])
            courses.append(course)
        return courses
    except Exception as e:
        logger.error(f"Erro ao montar lista de cursos do usuário: {e}")
        return None


@inscriptions_bp.route('/my-courses', methods=['GET'])
def my_courses():
    if not _is_logged_in():
        return redirect(url_for("auth.login"))

    try:
        courses = get_my_courses()
        return render_template("my_courses.html", courses=courses)
    except Exception as e:
        logger.error(f"Erro ao listar inscrições: {e}")
        return jsonify({'error': 'Erro ao recuperar suas inscrições.'}), 500


@inscriptions_bp.route('/is-subscribed/<content_id>', methods=['GET'])
def check_subscription(content_id):
    if not _is_logged_in():
        return jsonify({'error': 'É necessário estar logado.'}), 401

    result = g.user.check_inscription(content_id)
    return jsonify({'subscribed': bool(result)}), 200