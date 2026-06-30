import logging
import os
from datetime import datetime

from flask import (
    abort, current_app, g, redirect, render_template,
    request, send_file, session, url_for, jsonify
)

from src.models.database import get_session
from . import contents_bp
from src.view.configs.statics_configs import CONTENT_TYPES, DEFAULT_BANNERS




from functools import lru_cache
from datetime import datetime, timedelta

# Cache simples em memória (pode ser substituído por Redis/Flask-Caching depois)
_cache = {}

def _cache_get(key, ttl_seconds=300):
    """Retorna valor do cache se não expirado."""
    if key in _cache:
        value, timestamp = _cache[key]
        if (datetime.now() - timestamp).seconds < ttl_seconds:
            return value
        del _cache[key]
    return None

def _cache_set(key, value):
    _cache[key] = (value, datetime.now())
@contents_bp.route("/contents/", defaults={"publications": None})
@contents_bp.route("/contents/<publications>", methods=["GET", "POST"])
def contents(publications):
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 12, type=int)
        active_tab = request.args.get("tab", "all-courses")

        # ── Novos filtros ────────────────────────
        search = request.args.get("search", None, type=str)
        content_type = request.args.get("type", "all", type=str)
        popularity = request.args.get("popularity", "all", type=str)
        sort = request.args.get("sort", "recent", type=str)

        result = g.user.GET_FULL_CONTENT(
            all_contents=True,
            content_to_select=None,
            review=True,
            limit=per_page,
            offset=(page - 1) * per_page,
            search=search if search else None,
            content_type=content_type,
            popularity=popularity,
            sort=sort
        )
        if not result:
            return "Erro ao carregar conteúdos", 500

        items = result["items"]
        total_items = result["total"]
        total_pages = max(1, (total_items + per_page - 1) // per_page)

        # Comentários são carregados apenas na página individual do curso (content_buss),
        # não na listagem — evita N queries desnecessárias ao MongoDB.

        enrolled_contents = g.user.get_my_courses_cached() if hasattr(g.user, 'get_my_courses_cached') else g.user.get_my_courses() or []

        last_accessed = None
        last_id = session.get("last_accessed_id")
        if last_id:
            last_accessed = {
                "id": last_id,
                "title": session.get("last_accessed_title", ""),
                "banner": session.get("last_accessed_banner", ""),
                "content_type": session.get("last_accessed_type", ""),
            }

        pub_items = []
        if _cred() in _PUBLISHER_CREDS:
            pub_items = _pub_items()

        if publications is None:
            publications = pub_items

        return render_template(
            "contents.html",
            contents=items,
            enrolled_contents=enrolled_contents,
            publications=publications,
            pub_items=pub_items,
            last_accessed=last_accessed,
            active_tab=active_tab,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_items=total_items,
            **tpl_ctx,
        )
    except Exception as exc:
        logging.error("Erro na rota principal: %s", exc)
        return f"Erro ao carregar conteúdos: {exc}", 500
        
# Constantes
_PUBLISHER_CREDS = ("admin", "professor")
_VALID_CREDS = ("admin", "professor", "aluno")
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

def _return_comment_by_cred(contentId):
    try:
        if _cred() == "aluno":
            return g.user.get_content_comment(contentId), []
        if _cred() == "professor":
            return g.user.get_comment_by_professor(contentId)
        if _cred() == "admin":
            return g.user.get_comment_by_admin(contentId)
        return []
    except Exception as e:
        logging.error("Erro ao obter comentários: %s", e)
        return []

def _render_contents_error(msg, active_tab="publish-content-view"):
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
    print("PASSO EM HOME")
    return redirect(url_for("contents.contents"))

@contents_bp.route("/contents/search/<courses>", methods=["GET"])
def seach_contents(courses):
    title = request.args.get("title", " ").strip()
    if not title:
        return jsonify([]), 200
    results = g.user.get_content_by_name(title)
    return jsonify(results), 200

@contents_bp.route("/professors/search/<professors>", methods=["GET"])
def seach_professors(professors):
    name = request.args.get("name", " ").strip()
    if not name:
        return jsonify([]), 200
    results = g.user.search_users_by_name(name)
    return jsonify(results), 200

@contents_bp.route("/redirect_publish_content", methods=["POST", "GET"])
def redirect_publish_content():
    return redirect(url_for("contents.contents", tab="publish-content-view",
                            _anchor="publications-section"))

@contents_bp.route("/contents/redirect_publications", methods=["GET"])
def redirect_get_publications():
    return redirect(url_for("contents.contents", tab="my-publications-view",
                            _anchor="publications-section"))

# ── ROTA PRINCIPAL (SPA) ─────────────────────────────────────────────────────


# ── CONTEÚDO INDIVIDUAL (PRÉ‑VISUALIZAÇÃO / EDIÇÃO) ─────────────────────────

@contents_bp.route("/contents/publications", methods=["GET"])
def get_publications():
    if _cred() not in _VALID_CREDS:
        return redirect(url_for("auth.login"))
    publications = _pub_items()
    return redirect(url_for("contents.contents", tab="my-publications-view",
                            _anchor="publications-section",
                            publications=publications))

@contents_bp.route("/contents/content/<content_id>", methods=["GET", "POST"])
def content_buss(content_id):
    if not content_id:
        abort(404)

    try:
        my_courses = g.user.get_my_courses()
    except Exception as exc:
        logging.error("Erro ao obter cursos do usuário: %s", exc)
        abort(500)

    if request.method == "GET":
        content = g.user.GET_FULL_CONTENT(all_contents=False, content_to_select=content_id, review=True)
        if not content:
            abort(404)
        content = content[0]
        content["comments"], content["moderated_comments"] = _return_comment_by_cred(content_id)
        # Dentro de content_buss ou select_content, após carregar o conteúdo:
        session["last_accessed_id"] = content["id"]
        session["last_accessed_title"] = content.get("title", "")
        session["last_accessed_banner"] = content.get("banner", "")
        session["last_accessed_type"] = content.get("content_type", "")
        session.modified = True
        return render_template("content_preview.html", content=content, my_courses=my_courses)

    if request.method == "POST":
        content = g.user.GET_FULL_CONTENT(all_contents=False, content_to_select=content_id, review=True)
        if not content:
            abort(404)
        content = content[0]
        content["comments"], content["moderated_comments"] = _return_comment_by_cred(content_id)
        return render_template("edit_content.html", content=content, **tpl_ctx)

    abort(404)

# ── VISUALIZAÇÃO DO CONTEÚDO (LEITURA / FLIPBOOK) ────────────────────────────
@contents_bp.route("/contents/publications/selec_content/<content_id>", methods=["POST", "GET"])
def select_content(content_id):
    if _cred() not in _VALID_CREDS:
        return redirect(url_for("auth.login"))

    # Obtém o conteúdo enriquecido (já com url_base_s3) usando a nova camada
    content = g.user.GET_FULL_CONTENT(all_contents=False, content_to_select=content_id, review=False)
    if not content:
        return redirect(url_for("contents.get_publications"))

    content = content[0]

    # No novo fluxo, se o conteúdo estiver no S3, url_base_s3 já foi injetado por GET_FULL_CONTENT.
    # Fallback para HTML legado (apenas se não houver S3 e existir campo 'pdf' – raro)
    if not content.get("s3_uuid") and content.get("pdf"):
        from pdf_to_html import pdf_bytes_to_html
        content["html_body"] = pdf_bytes_to_html(content.get("pdf") or b"")

    return render_template("content_view.html", content=content)

# ── DOWNLOAD SEGURO DO PDF ───────────────────────────────────────────────────
@contents_bp.route("/contents/download/<content_id>", methods=["GET"])
def download(content_id):
    if not g.user:
        return redirect(url_for("auth.login"))

    my_courses = g.user.get_my_courses() or []
    is_enrolled = any(str(c.get("id")) == str(content_id) for c in my_courses)
    if _cred() in _PUBLISHER_CREDS:
        is_enrolled = True

    if not is_enrolled:
        abort(403)

    download_url = g.user.get_content_download_url(content_id)
    if download_url:
        return redirect(download_url)

    abort(404)

# ── VISUALIZAÇÃO INTERNA DO PDF (EMBED NO NAVEGADOR) ─────────────────────────
@contents_bp.route("/contents/view/<content_id>", methods=["GET"])
def get_file(content_id):
    view_url = g.user.get_content_view_url(content_id)
    if view_url:
        return redirect(view_url)
    abort(404)

# ── BANNER ────────────────────────────────────────────────────────────────────
@contents_bp.route("/contents/banner/<content_id>")
def get_banner(content_id):
    content = g.user.get_content_by_id(content_id)
    if not content or not content.get("banner"):
        abort(404)

    banner = content["banner"]
    if banner.startswith(("http://", "https://")):
        return redirect(banner)   # o banner já é uma URL completa do S3

    # fallback local (banners estáticos)
    if "/" not in banner:
        return redirect(url_for("contents.get_banner_default", banner_id=banner))

    static_dir = os.path.join(current_app.root_path, "view/static")
    full_path = os.path.join(static_dir, banner)
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
            if os.path.exists(path):
                return send_file(path, mimetype="image/jpg")
    abort(404)

# ── PUBLICAÇÃO DE CONTEÚDO (ADMIN / PROFESSOR) ───────────────────────────────
@contents_bp.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    if request.method == "GET":
        return redirect(url_for("contents.contents", tab="publish-content-view",
                                _anchor="publications-section"))

    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    # Validações iniciais dos campos
    content_name = request.form.get("content_name", "").strip()
    description  = request.form.get("description", "").strip()
    content_type = request.form.get("content_type", "other")
    banner_id    = request.form.get("banner_id")
    banner_file  = request.files.get("banner_file")
    pdf_file     = request.files.get("file")

    if len(content_name) < 15:
        return _render_contents_error("Nome de conteúdo muito curto (mínimo 15 caracteres)")
    if len(description) < 50:
        return _render_contents_error("Descrição de conteúdo muito curta (mínimo 50 caracteres)")
    if not pdf_file or not pdf_file.filename:
        return _render_contents_error("Nenhum documento PDF selecionado")
    if not banner_file and not banner_id:
        return _render_contents_error("Nenhum banner selecionado")

    if not pdf_file.filename.lower().endswith(".pdf"):
        return _render_contents_error("O arquivo enviado precisa ser um PDF válido.")

    pdf_bytes = pdf_file.read()

    # 1) Upload do PDF para o S3 (retorna metadados s3_uuid, total_paginas, url_base_s3)
    upload_result = None
    if _cred() == "admin":
        upload_result = g.user.upload_content_pdf_by_admin(pdf_bytes)
    else:
        upload_result = g.user.upload_content_pdf_by_professor(pdf_bytes)

    if not upload_result or not upload_result.get("s3_uuid"):
        return _render_contents_error("Erro no processamento/upload do PDF para a nuvem.")

    # 2) Upload do banner (se arquivo enviado) – a função já salva a URL no banco, mas aqui precisamos
    #    apenas do valor para passar ao conteúdo. A URL será definitiva após a publicação.
    banner_url = banner_id
    if banner_file and banner_file.filename:
        try:
            if _cred() == "admin":
                # Apenas obtemos a URL, a persistência final virá com publish_content_by_...
                banner_url = g.user.upload_content_banner_by_admin(
                    None,  # conteúdo ainda não tem ID, mas podemos passar content_id=None? 
                           # A função original espera contentId existente, isso precisa de ajuste.
                           # Como não temos ID ainda, vamos chamar diretamente o helper de storage.
                    banner_file.filename, banner_file.read()
                )
            else:
                banner_url = g.user.upload_content_banner_by_professor(
                    None,
                    banner_file.filename, banner_file.read()
                )
        except Exception as e:
            logging.error("Erro ao fazer upload do banner: %s", e)
            return _render_contents_error("Falha ao enviar o banner personalizado.")

    # 3) Monta o dicionário de conteúdo (sem campo "pdf")
    content = {
        "title":         content_name,
        "desc":          description,
        "banner":        banner_url,
        "content_type":  content_type,
        "s3_uuid":       upload_result["s3_uuid"],
        "total_paginas": upload_result["total_paginas"],
    }

    # 4) Persiste no banco relacional
    author = None
    if _cred() == "admin":
        author_name = request.form.get("author")
        author_obj = g.user.get_user_by_username(author_name)
        if author_obj and author_obj.get("name") == author_name:
            author = author_obj["name"]
            upload = g.user.publish_content_by_admin(content, author)
    else:
        author = g.user.get_user_name()
        if author == session.get("name"):
            upload = g.user.publish_content_by_professor(content, author)

    if not author:
        return _render_contents_error("Nome de autor não encontrado no banco de dados.")
    if not upload:
        return _render_contents_error("Não foi possível salvar no banco de dados. Tente novamente.")

    # 5) Se o banner foi um arquivo novo, precisamos atualizar a URL definitiva no registro recém-criado.
    #    Como upload_content_banner_by_* tenta atualizar o banco, mas não temos ID antes da publicação,
    #    fazemos uma segunda chamada agora com o content_id real.
    content_id = upload if isinstance(upload, str) else (upload.get("id") if hasattr(upload, "get") else str(upload))
    if banner_file and banner_file.filename:
        # Reabre o arquivo (pois já lemos) ou usa o bytes guardado
        banner_file.seek(0)
        if _cred() == "admin":
            g.user.upload_content_banner_by_admin(content_id, banner_file.filename, banner_file.read())
        else:
            g.user.upload_content_banner_by_professor(content_id, banner_file.filename, banner_file.read())

    return redirect(url_for("contents.content_buss", content_id=content_id))


# ── EDIÇÃO DE CONTEÚDO ───────────────────────────────────────────────────────
@contents_bp.route("/contents/publications/selec_content/edit/<content_id>", methods=["POST", "GET"])
def edit_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    # Obtém o conteúdo existente
    if _cred() == "admin":
        content = g.user.get_content_by_admin(content_id)
    else:
        content = g.user.professor_get_content_by_id(content_id)

    if not content:
        return redirect(url_for("contents.get_publications"))

    def _update(field, value):
        if _cred() == "professor":
            return g.user.update_contents_by_id(field, content["id"], value)
        return g.user.update_contents_by_admin(field, content["id"], value)

    def _render_edit(error=None):
        return render_template("edit_content.html", content=content, error=error, **tpl_ctx)

    action = False

    # Atualizações de texto/tipo
    new_title = request.form.get("new_title")
    if new_title:
        if len(new_title.strip()) <= 15:
            return _render_edit("Título muito curto")
        action = _update("title", new_title)

    new_desc = request.form.get("new_desc")
    if new_desc:
        if len(new_desc.strip()) <= 50:
            return _render_edit("Descrição muito curta")
        action = _update("desc", new_desc)

    new_type = request.form.get("content_type")
    valid_types = [v for v, _, _ in CONTENT_TYPES]
    if new_type and new_type in valid_types:
        action = _update("content_type", new_type)

    # Atualização de banner
    banner_file = request.files.get("banner_file")
    if banner_file and banner_file.filename:
        try:
            if _cred() == "admin":
                g.user.upload_content_banner_by_admin(content_id, banner_file.filename, banner_file.read())
            else:
                g.user.upload_content_banner_by_professor(content_id, banner_file.filename, banner_file.read())
            action = True
        except Exception as e:
            logging.error("Erro ao atualizar banner: %s", e)
            return _render_edit("Erro ao salvar banner na nuvem")

    # Substituição do PDF (gera novo fatiamento e atualiza metadados no banco)
    new_pdf_file = request.files.get("file")
    if new_pdf_file and new_pdf_file.filename.lower().endswith(".pdf"):
        pdf_bytes = new_pdf_file.read()
        try:
            if _cred() == "admin":
                g.user.replace_content_pdf_by_admin(content_id, pdf_bytes)
            else:
                g.user.replace_content_pdf_by_professor(content_id, pdf_bytes)
            action = True
        except Exception as e:
            logging.error("Erro ao substituir PDF: %s", e)
            return _render_edit("Formato indevido ou erro ao processar o novo PDF.")

    if action:
        get_session().expire_all()
        return render_template("exito.html")

    return _render_edit()


# ── EXCLUIR CONTEÚDO ─────────────────────────────────────────────────────────
@contents_bp.route("/delete_content/<content_id>", methods=["POST"])
def delete_content(content_id):
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    action = (
        g.user.delete_contents_by_id(content_id)
        if _cred() == "professor"
        else g.user.delete_contents_by_admin(content_id)
    )

    if not action:
        return render_template(
            "edit_content.html",
            content={"id": content_id},
            error="Não foi possível excluir conteúdo",
        )
    return redirect(url_for("contents.redirect_get_publications"))


# ── REVIEWS / COMENTÁRIOS (inalterados, já usam os métodos corretos) ─────────
# (mantidos os mesmos endpoints: set_review, edit_review, ocult_user_review,
#  delete_my_review, delete_user_review – omitidos por brevidade, mas permanecem iguais)
#── REVIEWS ────────────────────────────────────────────────────────────────────

@contents_bp.route("/contents/set_review/", methods=["POST"])
def set_review():
    if not _cred():
        return redirect(url_for("auth.login"))

    course_request = request.get_json()
    course_id = course_request.get("course_id")
        
    if not course_id:
        return False
        
    rating = course_request.get("rating")
    comment = course_request.get("comment")
     
    if g.user.get_my_comment(course_id):
        print("JA TENHO COMENTARIOS")
        g.user.update_my_comment(course_id, rating, comment)
        
    else:
        print("NAO TENHO COMENTARIOS")
        g.user.set_content_review(contentId=course_id, rating=rating,comment=comment)
    
    return redirect(url_for("contents.content_buss", content_id=course_id))
    
    
@contents_bp.route("/contents/edit_review/<content_id>/", methods=["POST"])
def edit_review(content_id):
    if not content_id:
        abort(404)
    g.user.update_my_comment(content_id)

@contents_bp.route("/contents/ocult_user_review/<content_id>/<comment_id>", methods=["POST"])        
def ocult_user_review(content_id, comment_id):
    if _cred() not in ["admin", "professor"]:
        return redirect(url_for("auth.login"))
        
    if not comment_id or not content_id:
        return False
    print(f"[OCULT_REVIEW]: content id {content_id} %%% comment id {comment_id}")        
    if _cred() == "admin":
        susp = g.user.suspended_comment_by_admin(content_id, comment_id)
        
    if _cred() == "professor":
        susp = g.user.suspended_comment_by_professor(content_id, comment_id)
        
    if susp:
        return redirect(url_for("contents.content_buss", content_id=content_id))

    return redirect(url_for("contents.content_buss", content_id=content_id)), 404


@contents_bp.route("/contents/delete_my_review/<content_id>/<comment_id>", methods=["POST"])
def delete_my_review(content_id, comment_id):
    
    if not _cred():
        return redirect(url_for("auth.login"))
    
    if not comment_id or not content_id:
        return False
        
    if g.user.delete_my_comment(comment_id, content_id):
        return redirect(url_for("contents.content_buss", content_id=content_id))
            
    return redirect(url_for("contents.content_buss", content_id=content_id))


@contents_bp.route("/contents/delete_user_review/<content_id>/<comment_id>", methods=["POST"])
def delete_user_review(content_id, comment_id):    
    if _cred() not in ["admin", "professor"]:
        return redirect(url_for("auth.login"))
        
    if not comment_id or not content_id:
        return False
        
    if _cred() == "admin":
        delete = g.user.delete_comment_by_admin(content_id, comment_id)
        
    if _cred() == "professor":
        delete = g.user.delete_comment_by_professor(content_id, comment_id)
        
    if delete:
        return redirect(url_for("contents.content_buss", content_id=content_id))
        
    return redirect(url_for("contents.content_buss", content_id=content_id)), 404