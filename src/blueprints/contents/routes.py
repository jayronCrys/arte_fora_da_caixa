import logging
from io import BytesIO
from datetime import datetime
from flask import abort, g, redirect, render_template, request, send_file, session, url_for

from src.models.database import get_session

from . import contents_bp
_PUBLISHER_CREDS = ("admin", "professor")

from src.view.configs.statics_configs import CONTENT_TYPES, DEFAULT_BANNERS
def _cred():
    return session.get("cred")


# ── Listagem ──────────────────────────────────────────────────────────────────

@contents_bp.route("/home")
def home_page():
    return redirect(url_for("contents.contents"))


@contents_bp.route("/contents/content/<content_id>", methods=["GET"])
def content_buss(content_id):
    
    print("=====> passo em content buss")
    try:
        content = g.user.get_content_by_id(content_id)
    except Exception as exc:
        logging.error("Erro ao buscar conteúdo: %s", exc)
        abort(404)

    if not content:
        abort(404)

    # Extrai HTML do PDF em tempo de execução
    # (rápido o suficiente: ~50–200ms por PDF normal)
    from pdf_to_html import pdf_bytes_to_html
    html_body = pdf_bytes_to_html(content.get("pdf") or b"")
    content["html_body"] = html_body  # None se falhar → template usa fallback

    return render_template("content_view.html", content=content)


@contents_bp.route("/contents", methods=["GET", "POST"])
def contents():
    print("tenho que pegar todos os contwudosz")
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
    
from io import BytesIO
from flask import abort, redirect, url_for, send_file, send_from_directory
import base64

@contents_bp.route("/contents/banner/<content_id>")
def get_banner(content_id):
    print("entra em get_banner")              # agora vai aparecer!
    content = g.user.get_content_by_id(content_id)
    if not content or not content.get("banner"):
        abort(404)

    banner = content["banner"]

    # Caso 1: bytes puros da imagem
    if isinstance(banner, bytes):
        # Se já é imagem, serve direto; se for base64 codificado em bytes, vai quebrar.
        # Por segurança, podemos tentar decodificar se começar com caracteres de base64.
        if banner[:4] == b'\xff\xd8\xff\xe0' or banner[:4] == b'\x89PNG':
            return send_file(BytesIO(banner), mimetype="image/jpeg")
        else:
            # Tenta interpretar como base64
            try:
                img_data = base64.b64decode(banner)
                return send_file(BytesIO(img_data), mimetype="image/jpeg")
            except Exception:
                abort(404)

    # Caso 2: string -> pode ser base64 ou ID de banner padrão
    elif isinstance(banner, str):
        if banner.startswith("data:image"):
            # data URI
            img_data = base64.b64decode(banner.split(",")[1])
            return send_file(BytesIO(img_data), mimetype="image/jpeg")
        elif len(banner) > 200:  # provavelmente base64
            try:
                img_data = base64.b64decode(banner)
                return send_file(BytesIO(img_data), mimetype="image/jpeg")
            except Exception:
                abort(404)
        else:
            # ID curto -> redireciona para banner padrão
            return redirect(url_for("contents.get_banner_default", banner_id=banner))

    abort(404)


# ── Publicar ──────────────────────────────────────────────────────────────────

@contents_bp.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    tpl_ctx = dict(
        content_types=CONTENT_TYPES,
        default_banners=DEFAULT_BANNERS,
        now=datetime.now().strftime("%d/%m/%Y"),
    )
    if request.method == "POST":
        if _cred() not in _PUBLISHER_CREDS:
            return redirect(url_for("auth.login"))

        content_name = request.form.get("content_name", "").strip()
        description = request.form.get("description", "").strip()
        content_type = request.form.get("content_type", "other")
        banner_file = request.form.get("banner_file")
        banner_id = request.form.get("banner_id")
        file = request.files.get("file")
        

        if len(content_name) < 15:
            return render_template("publish_content.html", error="Nome de conteúdo muito curto")
        if len(description) < 50:
            return render_template("publish_content.html", error="Descrição de conteúdo muito curta")
        if not file:
            return render_template("publish_content.html", error="Nenhum documento selecionado")
        if not (banner_file or banner_id):
            return render_template("publish_content.html", error="Nenhum banner selecionado")
            
        pdf_bytes = None
        if file and file.filename.lower().endswith(".pdf"):
            pdf_bytes = file.read()
            logging.warning("Pdf Lido")
        
        banner_bytes = None
        if banner_file or banner_id:
           
            banner_bytes = banner_file.read() if banner_file else banner_id # salvar no banco como bytes (coluna banner)
            logging.warning("Banner Lido")
            banner_id    = None
            
        if not (pdf_bytes and description and content_name and banner_bytes):
            return render_template("publish_content.html", error="Formato inválido para documento")

        content = { 
        "title": content_name, 
        "desc": description,
        "banner": banner_bytes,
        "content_type": content_type,
        "pdf": pdf_bytes 
        }
        
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

    return render_template("publish_content.html", **tpl_ctx)
    
@contents_bp.route("/contents/banner/default/<banner_id>")
def get_banner_default(banner_id):
    from src.view.configs.statics_configs import DEFAULT_BANNERS
    for b in DEFAULT_BANNERS:
        if b["id"] == banner_id:
            # ajuste o caminho onde os arquivos ficam armazenados
            

            return send_from_directory("static/Banners", banner_id, mimetype="image/jpeg")
    abort(404)

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


# ── Editar / Excluir conteúdo ───────────────────────────────────@contents_bp.route("/contents/publications/selec_content/edit/<content_id>", methods=["POST", "GET"])
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

    from src.config.content_config import CONTENT_TYPES, DEFAULT_BANNERS

    def _update(field, value):
        if _cred() == "professor":
            return g.user.update_contents_by_id(field, content["id"], value)
        return g.user.update_contents_by_admin(field, content["id"], value)

    def _render_edit(error=None):
        return render_template(
            "edit_content.html",
            content=content,
            content_types=CONTENT_TYPES,
            default_banners=DEFAULT_BANNERS,
            error=error,
        )

    action = False

    # ── Título ────────────────────────────────────────────────────────────────
    new_title = request.form.get("new_title")
    if new_title:
        if not new_title.strip() or len(new_title) <= 15:
            return _render_edit("Título muito curto")
        action = _update("title", new_title)
        if not action:
            return _render_edit("Título muito curto")

    # ── Descrição ─────────────────────────────────────────────────────────────
    new_desc = request.form.get("new_desc")
    if new_desc:
        if not new_desc.strip() or len(new_desc) <= 50:
            return _render_edit("Descrição muito curta")
        action = _update("desc", new_desc)
        if not action:
            return _render_edit("Descrição muito curta")

    # ── Tipo de conteúdo ──────────────────────────────────────────────────────
    new_type = request.form.get("content_type")
    valid_types = [v for v, _, _ in CONTENT_TYPES]
    if new_type and new_type in valid_types:
        action = _update("content_type", new_type)
        if not action:
            return _render_edit("Erro ao atualizar tipo de conteúdo")

    # ── Banner ────────────────────────────────────────────────────────────────
    new_banner_file = request.files.get("banner_file")
    if new_banner_file and new_banner_file.filename:
        banner_bytes = new_banner_file.read()
        if banner_bytes:
            action = _update("banner", banner_bytes)
            if not action:
                return _render_edit("Erro ao salvar banner")

    # ── PDF ───────────────────────────────────────────────────────────────────
    new_file = request.files.get("file")
    if new_file and new_file.filename.lower().endswith(".pdf"):
        pdf_bytes = new_file.read()
        action = _update("pdf", pdf_bytes)
        if not action:
            return _render_edit("Formato indevido para pdf")

    if action:
        get_session().expire_all()
        return render_template("exito.html")

    # GET ou nenhum campo enviado → exibe formulário
    return _render_edit()


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
