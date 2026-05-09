import logging
from io import BytesIO

from flask import abort, g, redirect, render_template, request, send_file, session, url_for

from src.models.database import get_session

from . import contents_bp

_PUBLISHER_CREDS = ("admin", "professor")


def _cred():
    return session.get("cred")


# ── Listagem ──────────────────────────────────────────────────────────────────

@contents_bp.route("/home")
def home_page():
    return redirect(url_for("contents.contents"))


@contents_bp.route("/contents", methods=["GET", "POST"])
def contents():
    try:
        items = g.user.get_all_contents()
        return render_template("contents.html", contents=items)
    except Exception as exc:
        return f"Erro ao carregar conteúdos: {exc}", 500


@contents_bp.route("/contents/view/<content_id>", methods=["GET"])
def get_file(content_id):
    content = g.user.get_content_by_id(content_id)
    if not content:
        abort(404)
    return send_file(
        BytesIO(content.get("pdf")),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{content.get('title')}.pdf",
    )


@contents_bp.route("/contents/content/<content_id>", methods=["GET"])
def content_buss(content_id):
    try:
        content = g.user.get_content_by_id(content_id)
    except Exception as exc:
        logging.error("Erro ao buscar conteúdo: %s", exc)
        abort(404)
    if not content:
        abort(404)
    return render_template("content_view.html", content=content)


# ── Publicar ──────────────────────────────────────────────────────────────────

@contents_bp.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    if request.method == "POST":
        if _cred() not in _PUBLISHER_CREDS:
            return redirect(url_for("auth.login"))

        content_name = request.form.get("content_name", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("file")

        if len(content_name) < 15:
            return render_template("publish_content.html", error="Nome de conteúdo muito curto")
        if len(description) < 50:
            return render_template("publish_content.html", error="Descrição de conteúdo muito curta")
        if not file:
            return render_template("publish_content.html", error="Nenhum documento selecionado")

        pdf_bytes = None
        if file and file.filename.lower().endswith(".pdf"):
            pdf_bytes = file.read()

        if not (pdf_bytes and description and content_name):
            return render_template("publish_content.html", error="Formato inválido para documento")

        content = {"title": content_name, "desc": description, "pdf": pdf_bytes}
        upload = False
        author = False

        if _cred() == "admin":
            author_id = request.form.get("author")
            author_obj = g.user.get_user_by_admin(author_id)
            if author_obj and author_obj.get("name"):
                author = author_obj.get("name")
                upload = g.user.publish_content_by_admin(content, author)

        elif _cred() == "professor":
            author = g.user.get_user_name()
            if author == session.get("name"):
                upload = g.user.publish_content_by_professor(content, author)
            else:
                author = False

        if not author:
            return render_template("publish_content.html", error="Nome de autor não existe")
        if not upload:
            return render_template("publish_content.html", error="Não foi possível fazer upload do conteúdo, tente novamente.")

        return render_template("exito.html")

    return render_template("publish_content.html")


# ── Minhas publicações ────────────────────────────────────────────────────────

@contents_bp.route("/contents/publications", methods=["GET"])
def get_publications():
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    if _cred() == "professor":
        publications = g.user.select_contents_by_publisher_id()
    else:
        publications = g.user.get_all_contents()

    return render_template("my_publications.html", publications=publications)


@contents_bp.route("/contents/publications/selec_content/<content_id>", methods=["POST", "GET"])
def select_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    if _cred() == "professor":
        content = g.user.professor_get_content_by_id(content_id)
    else:
        content = g.user.get_content_by_admin(content_id)

    if not content:
        return redirect(url_for("contents.get_publications"))

    return render_template("edit_content.html", content=content)


# ── Editar / Excluir conteúdo ─────────────────────────────────────────────────

@contents_bp.route("/contents/publications/selec_content/edit/<content_id>", methods=["POST", "GET"])
def edit_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    content = (
        g.user.get_content_by_admin(content_id)
        if _cred() == "admin"
        else g.user.professor_get_content_by_id(content_id)
    )

    if not content:
        return redirect(url_for("contents.get_publications"))

    def _update(field, value):
        if _cred() == "professor":
            return g.user.update_contents_by_id(field, content["id"], value)
        return g.user.update_contents_by_admin(field, content["id"], value)

    action = False

    new_title = request.form.get("new_title")
    if new_title:
        if not new_title.strip() or len(new_title) <= 15:
            return render_template("edit_content.html", content=content, error="Título muito curto")
        action = _update("title", new_title)
        if not action:
            return render_template("edit_content.html", content=content, error="Título muito curto")

    new_desc = request.form.get("new_desc")
    if new_desc:
        if not new_desc.strip() or len(new_desc) <= 50:
            return render_template("edit_content.html", content=content, error="Descrição muito curta")
        action = _update("desc", new_desc)
        if not action:
            return render_template("edit_content.html", content=content, error="Descrição muito curta")

    new_file = request.files.get("file")
    if new_file and new_file.filename.lower().endswith(".pdf"):
        pdf_bytes = new_file.read()
        action = _update("pdf", pdf_bytes)
        if not action:
            return render_template("edit_content.html", content=content, error="Formato indevido para pdf")

    if action:
        get_session().expire_all()
        return render_template("exito.html")

    return redirect(url_for("auth.login"))


@contents_bp.route("/delete_content/<content_id>", methods=["POST"])
def delete_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    if _cred() == "professor":
        action = g.user.delete_contents_by_id(content_id)
    else:
        action = g.user.delete_contents_by_admin(content_id)

    if not action:
        content = {"id": content_id}
        return render_template("edit_content.html", content=content, error="Não foi possível excluir arquivo")

    return redirect(url_for("contents.get_publications"))
