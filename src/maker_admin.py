from src.models.database import get_session as database
from src.models.db_execute import insert_info, select_info
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User, UserCred
from src.models.passwords import make_hash
from src.controller.storage.s3_content_storage import create_content_storage  # Novo
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_roles():
    """Converte papéis antigos (aluno/professor/admin) para os novos ENUMs."""
    from src.models.database import get_session
    from sqlalchemy import text

    s = get_session()
    try:
        s.execute(text("UPDATE usuarios SET cred = 'STUDENT' WHERE cred = 'aluno'"))
        s.execute(text("UPDATE usuarios SET cred = 'PROFESSOR' WHERE cred = 'professor'"))
        s.execute(text("UPDATE usuarios SET cred = 'ADMIN' WHERE cred = 'admin'"))
        s.commit()
        logger.info("Migração de papéis concluída!")
    except Exception as e:
        s.rollback()
        logger.error("Erro na migração de papéis: %s", e)
    finally:
        s.close()


def make_users():
    """Cria usuários de exemplo se não existirem."""
    session = database()

    users = [
        {
            "name": "JAYRON",
            "password": make_hash("1081514Jh"),
            "cred": UserCred.ADMIN,
            "picture": None
        },
        {
            "name": "Frederico",
            "password": make_hash("1081514Jh"),
            "cred": UserCred.PROFESSOR,
            "picture": None
        },
        {
            "name": "Bolsonaro",
            "password": make_hash("1081514Jh"),
            "cred": UserCred.STUDENT,
            "picture": None
        }
    ]

    cargos = [
        UserCred.ADMIN,
        UserCred.PROFESSOR,
        UserCred.STUDENT
    ]

    # Cria mais 40 usuários
    for i in range(1, 41):
        users.append({
            "name": f"Usuario{i}",
            "password": make_hash("1081514Jh"),
            "cred": cargos[(i - 1) % 3],
            "picture": None
        })

    for user in users:
        if select_info(session, User, "name", user["name"]):
            logger.info("Usuário %s já existe, pulando.", user["name"])
            continue

        insert_info(session, User, user)
        logger.info("Usuário %s criado.", user["name"])

    session.close()
    migrate_roles()

def make_contents():
    """Cria conteúdos de exemplo no banco e envia os PDFs para o S3."""
    session = database()

    # Caminho do PDF local (ajuste para o seu ambiente)
    pdf_path = "file:///home/Jwksjsjs/arte_fora_da_caixa/src/Modelagem_mtmtc.pdf"
    if not os.path.exists(pdf_path):
        logger.error("Arquivo PDF de exemplo não encontrado: %s", pdf_path)
        session.close()
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Usuários que serão publicadores
    user_fred = select_info(session, User, "name", "Frederico")
    user_jayron = select_info(session, User, "name", "JAYRON")
    if not user_fred or not user_jayron:
        logger.error("Usuários publicadores não encontrados.")
        session.close()
        return
    contents_data = []        
    for n in range(4):
    # Dados dos conteúdos (sem campo 'pdf')
        contents_data.append({
                "title": f"conteudo exemplo matemática {n}",
                "desc": f"conteúdo teste {n}",
                "banner": "matematica",           # ID do banner padrão
                "content_type": "Matemática",
                "author": "Frederico",
                "publisher_id": uuid.UUID(user_fred["id"])
            })
        contents_data.append({
                "title": f"conteudo exemplo Biologia {n}",
                "desc": f"conteúdo teste {n}",
                "banner": "biologia",
                "content_type": "Biologia",
                "author": "Frederico",
                "publisher_id": uuid.UUID(user_fred["id"])
            })
        contents_data.append({
                "title": f"conteudo exemplo História {n}",
                "desc": f"conteúdo teste {n}",
                "banner": "historia",
                "content_type": "História",
                "author": "JAYRON",
                "publisher_id": uuid.UUID(user_jayron["id"])
        })
        contents_data.append({
                "title": f"conteudo exemplo Português {n}",
                "desc": f"conteúdo teste {n}",
                "banner": "portugues",
                "content_type": "Português",
                "author": "JAYRON",
                "publisher_id": uuid.UUID(user_jayron["id"]) })
    
    for content in contents_data:
        # Verifica se conteúdo com mesmo título já existe
        if select_info(session, Contents, "title", content["title"]):
            logger.info("Conteúdo '%s' já existe, pulando.", content['title'])
            continue

        # Faz upload do PDF para o S3 e obtém os metadados
        logger.info("Enviando PDF para o S3 para o conteúdo '%s'...", content['title'])
        s3_result = create_content_storage(pdf_bytes)  # Usa o mesmo PDF para todos (exemplo)
        if not s3_result or not s3_result.get("s3_uuid"):
            logger.error("Falha no upload S3 para '%s', pulando.", content['title'])
            continue

        # Adiciona os campos do S3 ao dicionário
        content["s3_uuid"] = s3_result["s3_uuid"]
        content["total_paginas"] = s3_result["total_paginas"]

        # Insere no banco
        insert_info(session, Contents, content)
        logger.info("Conteúdo '%s' criado com sucesso (s3_uuid=%s).", content['title'], content['s3_uuid'])

    session.close()


if __name__ == "__main__":
    make_users()
    make_contents()