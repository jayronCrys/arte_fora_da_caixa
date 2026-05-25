import logging
from io import BytesIO
from datetime import datetime
from flask import abort, g, redirect, render_template, request, send_file, session, url_for

from src.models.database import get_session

from . import contents_bp
_PUBLISHER_CREDS = ("admin", "professor")

from src.view.configs.statics_configs import CONTENT_TYPES, DEFAULT_BANNERS

tpl_ctx = dict(
        content_types=CONTENT_TYPES,
        default_banners=DEFAULT_BANNERS,
        now=datetime.now().strftime("%d/%m/%Y"),
    )
    
def _cred():
    return session.get("cred")


# ── Listagem ──────────────────────────────────────────────────────────────────

@contents_bp.route("/home")
def home_page():
    return redirect(url_for("contents.contents"))


@contents_bp.route("/contents/content/<content_id>", methods=["GET", "POST"])
def content_buss(content_id):
    
    print("=====> passo em content buss <======")
    try:
        content = g.user.get_content_by_id(content_id)
    except Exception as exc:
        logging.error("Erro ao buscar conteúdo: %s", exc)
        abort(404)

    if not content:
        abort(404)
    print("REQUEST", request.method)
    return render_template("content_preview.html", content=content) if request.method == "GET" else render_template("edit_content.html", content = content, **tpl_ctx)

@contents_bp.route("/contents/", defaults={"publications":None})
@contents_bp.route("/contents/<publications>", methods=["GET", "POST"])
def contents(publications):
    print("Acessando a central de conteúdos da SPA...")
    try:
        # 1. Busca todos os conteúdos para a listagem principal
        items = g.user.get_all_contents()
        
        # 2. Captura o parâmetro 'tab' enviado via redirecionamento (?tab=...)
        # Se não houver nada na URL, ele assume 'my-publications-view' por padrão
        active_tab = request.args.get("tab", "my-publications-view")
        
        # 3. Busca publicações específicas se o usuário for um publicador logado
        pub_items = []
        if _cred() in _PUBLISHER_CREDS:
            try:
                pub_items = g.user.select_contents_by_publisher_id() if _cred() == "professor" else items
            except Exception:
                pub_items = []

        # Envia TODAS as variáveis de controle que o front-end precisa para decidir o que exibir e marcar
        return render_template(
            "contents.html", 
            contents=items, 
            publications=publications, # mantém a compatibilidade com o que você já tinha
            pub_items=pub_items,       # a lista de publicações do professor/admin
            active_tab=active_tab,     # Diz EXATAMENTE qual sub-aba (label) deve vir ativa
            **tpl_ctx                  # Injeta os tipos de conteúdos, banners default e data atual
        )
        
    except Exception as exc:
        logging.error("Erro na rota principal de conteúdos: %s", exc)
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
    
import os
from flask import current_app, send_file, redirect, url_for, abort, g

@contents_bp.route("/contents/banner/<content_id>")
def get_banner(content_id):
    print("chegou o id", content_id)
    print("a raiz dos caminhos é", current_app.root_path)
    content = g.user.get_content_by_id(content_id)
    content_i = content
    content_i["pdf"] = "mudei"
    print("essa é a porra do conteudo", content_i)
    if not content or not content.get("banner"):
        print("nao tem banner nesse krl")
        abort(404)

    banner = content["banner"]
    if "/" not in banner:
        return redirect(url_for("contents.get_banner_default", banner_id=banner))

    print("a raiz dos caminhos é", current_app.root_path)
    static_dir = os.path.join(current_app.root_path, "view/static")
    full_path  = os.path.join(static_dir, banner)

    print(f"[get_banner] Servindo: {full_path}, existe: {os.path.exists(full_path)}")

    if not os.path.exists(full_path):
        abort(404)

    return send_file(full_path, mimetype="image/jpeg")


# ── Publicar ──────────────────────────────────────────────────────────────────

import os
import uuid

BANNERS_BASE_DIR = "/storage/emulated/0/arte_fora_da_caixa/src/view/static/Banners/by_user"
# ── Publicar ──────────────────────────────────────────────────────────────────

# ── Publicar ──────────────────────────────────────────────────────────────────

@contents_bp.route("/redirect_publish_content", methods=["POST", "GET"])
def redirect_publish_content():
    # Garante que o redirecionamento jogue o usuário de volta para a SPA com a âncora certa
    return redirect(url_for("contents.contents", _anchor="publications-section", tab="publish-content-view"))
    
@contents_bp.route("/publish_content", methods=["POST", "GET"])
def publish_content():
    # Se o usuário tentar acessar via GET diretamente (ex: recarregar a página),
    # nós apenas mandamos ele de volta para a rota principal dos conteúdos
    if request.method == "GET":
        return redirect(url_for("contents.contents", _anchor="publications-section", tab="publish-content-view"))

    if request.method == "POST":
        if _cred() not in _PUBLISHER_CREDS:
            return redirect(url_for("auth.login"))

        content_name = request.form.get("content_name", "").strip()
        description  = request.form.get("description", "").strip()
        content_type = request.form.get("content_type", "other")
        banner_id    = request.form.get("banner_id")    
        banner_file  = request.files.get("banner_file")
        file         = request.files.get("file")

        # Função auxiliar para recarregar a SPA mantendo os dados da listagem vivos em caso de erro
        def _render_error(msg):
            try:
                items = g.user.get_all_contents()
                pub_items = g.user.select_contents_by_publisher_id() if _cred() == "professor" else items
            except Exception:
                items, pub_items = [], []
            return render_template("contents.html", error=msg, contents=items, publications=pub_items, **tpl_ctx)

        # Validações rígidas
        if len(content_name) < 15:
            return _render_error("Nome de conteúdo muito curto (mínimo 15 caracteres)")
        if len(description) < 50:
            return _render_error("Descrição de conteúdo muito curta (mínimo 50 caracteres)")
        if not file:
            return _render_error("Nenhum documento PDF selecionado")
        if not banner_file and not banner_id:
            return _render_error("Nenhum banner selecionado")

        # ── PDF ──────────────────────────────────────────────────────────────
        pdf_bytes = None
        if file and file.filename.lower().endswith(".pdf"):
            pdf_bytes = file.read()

        # ── Banner ───────────────────────────────────────────────────────────
        banner_path = None
        if banner_id:
            banner_path = banner_id
        if banner_file and banner_file.filename:
            banners_dir = os.path.join(current_app.root_path, "view", "static", "Banners", "by_user")
            os.makedirs(banners_dir, exist_ok=True)
            ext       = banner_file.filename.rsplit(".", 1)[-1].lower()
            filename  = f"{uuid.uuid4().hex}.{ext}"
            full_path = os.path.join(banners_dir, filename)
            banner_file.save(full_path)
            banner_path = f"Banners/by_user/{filename}"
    
        if not (pdf_bytes and description and content_name and banner_path):
            return _render_error("Formato inválido ou arquivos corrompidos")
            
        upload = False
        author = False
        content = {
            "title":        content_name,
            "desc":         description,
            "banner":       banner_path,
            "content_type": content_type,
            "pdf":          pdf_bytes
        }
        
        if _cred() == "admin":
            author_id   = request.form.get("author")
            author_obj  = g.user.get_user_by_admin(author_id)
            if author_obj and author_obj.get("name"):
                author  = author_obj.get("name")
                upload  = g.user.publish_content_by_admin(content, author)

        elif _cred() == "professor":
            author = g.user.get_user_name()
            if author == session.get("name"):
                upload = g.user.publish_content_by_professor(content, author)
            else:
                author = False

        if not author:
            return _render_error("Nome de autor não existe no banco de dados")
        if not upload:
            return _render_error("Não foi possível salvar no banco de dados. Tente novamente.")
        
        # SUCESSO TOTAL: Redireciona para a rota principal (/contents) forçando a hashtag no navegador
        return redirect(url_for("contents.contents", _anchor="publications-section", tab = "publish-content-view"))


import os
from flask import current_app

@contents_bp.route("/contents/banner/default/<banner_id>")
def get_banner_default(banner_id):
    
    for b in DEFAULT_BANNERS:
        print("o B é", banner_id, "o default é", b)
        if b["id"] == banner_id:
            # monta o caminho absoluto a partir da raiz do app
            path = os.path.join(current_app.root_path,"view", "static", "Banners", b["name"].split("/")[-1])
            print(f"[get_banner_default] Servindo: {path}, existe: {os.path.exists(path)}")
            if not os.path.exists(path):
                abort(404)
            return send_file(path, mimetype="image/jpg")
    abort(404)
    
# ── Minhas publicações ────────────────────────────────────────────────────────
@contents_bp.route("/contents/redirect_publications", methods=["GET"])
def redirect_get_publications():
    return redirect(url_for("contents.contents", _anchor="publications-section", tab="my-publications-view"))
    
    
@contents_bp.route("/contents/publications", methods=["GET"])
def get_publications():
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    if _cred() == "professor":
        publications = g.user.select_contents_by_publisher_id()
    else:
        publications = g.user.get_all_contents()

    return redirect(url_for("contents.contents", _anchor = "publications-section" , tab = "my-publications-view", publications=publications))


@contents_bp.route("/contents/publications/selec_content/<content_id>", methods=["POST", "GET"])
def select_content(content_id):
    
    if _cred() not in _PUBLISHER_CREDS:
        return redirect(url_for("auth.login"))

    if _cred() == "professor":
        content = g.user.professor_get_content_by_id(content_id)
    else:
        content = g.user.get_content_by_admin(content_id)

    if not content_id:
        return redirect(url_for("contents.get_publications"))
        
    from pdf_to_html import pdf_bytes_to_html
    html_body = pdf_bytes_to_html(content.get("pdf") or b"")
    content["html_body"] = html_body 
    print("\n\n eu existo" if content["html_body"] else "")
    return render_template("content_view.html",content = content)


# ── Editar / Excluir conteúdo ─────────────────────────────

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
        return render_template(
            "edit_content.html",
            content=content,
            **tpl_ctx,
            error=error
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
