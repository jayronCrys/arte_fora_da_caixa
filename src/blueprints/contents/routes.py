import logging
import os
import uuid
from io import BytesIO
from datetime import datetime

from flask import (
    abort, current_app, g, redirect, render_template,
    request, send_file, session, url_for,
)

from src.models.database import get_session
from . import contents_bp
from src.view.configs.statics_configs import CONTENT_TYPES, DEFAULT_BANNERS

# ── Constantes ────────────────────────────────────────────────────────────────
_PUBLISHER_CREDS = ("admin", "professor")

tpl_ctx = dict(
    content_types=CONTENT_TYPES,
    default_banners=DEFAULT_BANNERS,
    now=datetime.now().strftime("%d/%m/%Y"),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cred():
    return session.get("cred")


def _pub_items():
    """Retorna a lista de publicações do usuário logado (professor ou admin)."""
    if _cred() == "professor":
        return g.user.select_contents_by_publisher_id()
    return g.user.get_all_contents()


def _render_contents_error(msg, active_tab="publish-content-view"):
    """Re-renderiza a SPA principal com uma mensagem de erro."""
    try:
        items = g.user.get_all_contents()
        publications = _pub_items() if _cred() in _PUBLISHER_CREDS else []
    except Exception:
        items, publications = [], []
    return render_template(
        "contents.html",
        error=msg,
        contents=items,
        publications=publications,
        active_tab=active_tab,
        **tpl_ctx,
    )


# ── Redirecionamentos simples ─────────────────────────────────────────────────

@contents_bp.route("/home")
def home_page():
    return redirect(url_for("contents.contents"))


@contents_bp.route("/redirect_publish_content", methods=["POST", "GET"])
def redirect_publish_content():
    return redirect(url_for("contents.contents", tab="publish-content-view",
                            _anchor="publications-section"))


@contents_bp.route("/contents/redirect_publications", methods=["GET"])
def redirect_get_publications():
    return redirect(url_for("contents.contents", tab="my-publications-view",
                            _anchor="publications-section"))


# ── Rota principal (SPA) ──────────────────────────────────────────────────────
@contents_bp.route("/contents/set_review/", methods=["POST"])
def set_review():
    
    course_request = request.get_json()
    course_id = course_request.get("course_id")
    
    if not course_id:
        return False
        
    rating = course_request.get("rating")
    comment = course_request.get("comment")
    print("ADD_REVIEW TEM COMO ENTRADA", rating, comment)
    add_review = g.user.set_content_review(contentId=course_id, rating=rating, comment=comment)
    print("RESULTADO DE ADD_REVIEW", add_review)
    return redirect(url_for("contents.content_buss", content_id=course_id))
    
@contents_bp.route("/contents/", defaults={"publications": None})
@contents_bp.route("/contents/<publications>", methods=["GET", "POST"])
def contents(publications):
    try:

        items = g.user.GET_FULL_CONTENT(all_contents=True, content_to_select=None, review=True)
        active_tab = request.args.get("tab", "all-courses")
        print("Resultado de GET_FULL_CONYENY", items[0]["rating"]["average_rating"])
        enrolled_contents = g.user.get_my_courses()
        
        if not enrolled_contents:
            enrolled_contents = []
            
        pub_items = []
        if _cred() in _PUBLISHER_CREDS:
            try:
                pub_items = _pub_items()
            except Exception:
                pub_items = []

        if publications is None:
            publications = pub_items

        return render_template(
            "contents.html",
            contents=items,
            enrolled_contents=enrolled_contents,
            publications=publications,
            pub_items=pub_items,
            active_tab=active_tab,
            **tpl_ctx,
        )
    except Exception as exc:
        logging.error("Erro na rota principal de conteúdos: %s", exc)
        return f"Erro ao carregar conteúdos: {exc}", 500


# ── Publicar conteúdo ─────────────────────────────────────────────────────────

@contents_bp.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    if request.method == "GET":
        return redirect(url_for("contents.contents", tab="publish-content-view",
                                _anchor="publications-section"))

    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    content_name = request.form.get("content_name", "").strip()
    description  = request.form.get("description", "").strip()
    content_type = request.form.get("content_type", "other")
    banner_id    = request.form.get("banner_id")
    banner_file  = request.files.get("banner_file")
    file         = request.files.get("file")

    # ── Validações ────────────────────────────────────────────────────────────
    if len(content_name) < 15:
        return _render_contents_error("Nome de conteúdo muito curto (mínimo 15 caracteres)")
    if len(description) < 50:
        return _render_contents_error("Descrição de conteúdo muito curta (mínimo 50 caracteres)")
    if not file or not file.filename:
        return _render_contents_error("Nenhum documento PDF selecionado")
    if not banner_file and not banner_id:
        return _render_contents_error("Nenhum banner selecionado")

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf_bytes = None
    if file.filename.lower().endswith(".pdf"):
        pdf_bytes = file.read()

    # ── Banner ────────────────────────────────────────────────────────────────
    banner_path = banner_id  # pode ser None se só vier o arquivo
    if banner_file and banner_file.filename:
        banners_dir = os.path.join(
            current_app.root_path, "view", "static", "Banners", "by_user"
        )
        os.makedirs(banners_dir, exist_ok=True)
        ext       = banner_file.filename.rsplit(".", 1)[-1].lower()
        filename  = f"{uuid.uuid4().hex}.{ext}"
        full_path = os.path.join(banners_dir, filename)
        banner_file.save(full_path)
        banner_path = f"Banners/by_user/{filename}"

    if not all([pdf_bytes, description, content_name, banner_path]):
        return _render_contents_error("Formato inválido ou arquivos corrompidos")

    # ── Montar payload ────────────────────────────────────────────────────────
    content = {
        "title":        content_name,
        "desc":         description,
        "banner":       banner_path,
        "content_type": content_type,
        "pdf":          pdf_bytes,
    }

    # ── Persistir conforme credencial ─────────────────────────────────────────
    upload = False
    author = False

    if _cred() == "admin":
        author_id  = request.form.get("author")
        author_obj = g.user.get_user_by_admin(author_id)
        if author_obj and author_obj.get("name"):
            author = author_obj["name"]
            upload = g.user.publish_content_by_admin(content, author)
            
    elif _cred() == "professor":
        author = g.user.get_user_name()
        if author == session.get("name"):
            upload = g.user.publish_content_by_professor(content, author)
            
        else:
            author = False

    if not author:
        return _render_contents_error("Nome de autor não existe no banco de dados")
    if not upload:
        return _render_contents_error("Não foi possível salvar no banco de dados. Tente novamente.")

    # ── Sucesso: redireciona para visualização do conteúdo publicado ──────────
    # `upload` deve ser o ID do conteúdo recém-criado (ou o objeto que o contém)
    content_id = upload if isinstance(upload, str) else upload.get("id") if hasattr(upload, "get") else str(upload)
    return redirect(url_for("contents.content_buss", content_id=content_id))


# ── Servir arquivos ───────────────────────────────────────────────────────────

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


@contents_bp.route("/contents/banner/<content_id>")
def get_banner(content_id):
    content = g.user.get_content_by_id(content_id)
    if not content or not content.get("banner"):
        abort(404)

    banner = content["banner"]
    if "/" not in banner:
        return redirect(url_for("contents.get_banner_default", banner_id=banner))

    static_dir = os.path.join(current_app.root_path, "view/static")
    full_path  = os.path.join(static_dir, banner)
    if not os.path.exists(full_path):
        abort(404)
    return send_file(full_path, mimetype="image/jpeg")


@contents_bp.route("/contents/banner/default/<banner_id>")
def get_banner_default(banner_id):
    for b in DEFAULT_BANNERS:
        if b["id"] == banner_id:
            path = os.path.join(
                current_app.root_path, "view", "static", "Banners",
                b["name"].split("/")[-1],
            )
            if not os.path.exists(path):
                abort(404)
            return send_file(path, mimetype="image/jpg")
    abort(404)


# ── Visualização / edição de conteúdo individual ──────────────────────────────

@contents_bp.route("/contents/content/<content_id>", methods=["GET", "POST"])
def content_buss(content_id):
    try:
        print("\n\n\ntipo meu", content_id)
        
        my_courses = g.user.get_my_courses()
        
    except Exception as exc:
        logging.error("Erro ao buscar conteúdo: %s", exc)
        
        abort(404)
    if not content_id:
        abort(404)
        
    if request.method == "GET":
        
        content = g.user.GET_FULL_CONTENT( all_contents=False, content_to_select=content_id, review=True, comments=True)
        
        print(f"[RETORNO DE CONTENT_BUSS de tipo {type(content)}<0>\n", content)
        
        content = content[0] if content[0]["id"] == content_id else False
        
        if not content:
            abort(404)
            
        print(f"[RETORNO DE CONTENT_BUSS de tipo {type(content)}<1>\n", content)
        return render_template("content_preview.html", content=content, my_courses=my_courses)
        
    content = content[0] if content[0]["id"] == content_id else False
    print(f"[RETORNO DE CONTENT_BUSS de tipo {type(content)}", content)
    if not content:
        abort(404)        
    content = g.user.GET_FULL_CONTENT( all_contents=False, content_to_select=content_id, review=True, comments=False)        
        
    return render_template("edit_content.html", content=content, **tpl_ctx)


# ── Minhas publicações / select_content ───────────────────────────────────────

@contents_bp.route("/contents/publications", methods=["GET"])
def get_publications():
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))
    publications = _pub_items()
    return redirect(url_for("contents.contents", tab="my-publications-view",
                            _anchor="publications-section",
                            publications=publications))


@contents_bp.route("/contents/publications/selec_content/<content_id>", methods=["POST", "GET"])
def select_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    content = (
        g.user.get_content_by_admin(content_id)
        if _cred() == "admin"
        else g.user.professor_get_content_by_id(content_id)
    )

    if not content:
        return redirect(url_for("contents.get_publications"))

    from pdf_to_html import pdf_bytes_to_html
    content["html_body"] = pdf_bytes_to_html(content.get("pdf") or b"")
    return render_template("content_view.html", content=content)


# ── Editar conteúdo ───────────────────────────────────────────────────────────

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

    def _render_edit(error=None):
        return render_template("edit_content.html", content=content, error=error, **tpl_ctx)

    action = False

    new_title = request.form.get("new_title")
    if new_title:
        if len(new_title.strip()) <= 15:
            return _render_edit("Título muito curto")
        action = _update("title", new_title)
        if not action:
            return _render_edit("Erro ao atualizar título")

    new_desc = request.form.get("new_desc")
    if new_desc:
        if len(new_desc.strip()) <= 50:
            return _render_edit("Descrição muito curta")
        action = _update("desc", new_desc)
        if not action:
            return _render_edit("Erro ao atualizar descrição")

    new_type = request.form.get("content_type")
    valid_types = [v for v, _, _ in CONTENT_TYPES]
    if new_type and new_type in valid_types:
        action = _update("content_type", new_type)
        if not action:
            return _render_edit("Erro ao atualizar tipo de conteúdo")

    new_banner_file = request.files.get("banner_file")
    if new_banner_file and new_banner_file.filename:
        banner_bytes = new_banner_file.read()
        if banner_bytes:
            action = _update("banner", banner_bytes)
            if not action:
                return _render_edit("Erro ao salvar banner")

    new_file = request.files.get("file")
    if new_file and new_file.filename.lower().endswith(".pdf"):
        pdf_bytes = new_file.read()
        action = _update("pdf", pdf_bytes)
        if not action:
            return _render_edit("Formato indevido para pdf")

    if action:
        get_session().expire_all()
        return render_template("exito.html")

    return _render_edit()


# ── Excluir conteúdo ──────────────────────────────────────────────────────────

@contents_bp.route("/delete_content/<content_id>", methods=["POST"])
def delete_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    action = (
        g.user.delete_contents_by_id(content_id)
        if _cred() == "professor"
        else g.user.delete_contents_by_admin(content_id)
    )
    print("\n\n\nresultado de deletar\n\n\n", action)
    if not action:
        return render_template(
            "edit_content.html",
            content={"id": content_id},
            error="Não foi possível excluir arquivo",
        )
    return redirect(url_for("contents.redirect_get_publications"))
