
from src.models.database import get_session as database
from src.models.db_execute import insert_info, select_info
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User, UserCred
from src.models.relationships_models.inscriptions import Subs

from src.models.passwords import make_hash
banco = database()
from src.models.database import get_session
import uuid
# src/maker_admin.py

from sqlalchemy import text

def migrate_roles():
    s = get_session()
    
    try:
        s.execute(text("UPDATE usuarios SET cred = 'STUDENT' WHERE cred = 'aluno'"))
        s.execute(text("UPDATE usuarios SET cred = 'PROFESSOR' WHERE cred = 'professor'"))
        s.execute(text("UPDATE usuarios SET cred = 'ADMIN' WHERE cred = 'admin'"))
        s.commit()
        print("Migração concluída!")
    except Exception as e:
        s.rollback()
        print("Erro:", e)
    finally:
        s.close()
        
def make_contents():
    session = database()
        
        
    pdf_path = "/storage/emulated/0/arte_fora_da_caixa/src/Modelagem_mtmtc.pdf"

    with open(pdf_path, "rb") as pdf:
        pdf = pdf.read()        
    user = select_info(session, User, "name", "Frederico")
    user_ = select_info(session, User, "name", "JAYRON")
    if not user or not user_:
        return "ERRO AO BUSCAR PELO USUÁRIO GERADOR"
    
    contents = [{"title": "conteudo exemplo matemática 2",
    "pdf": pdf,
    "desc": "conteúdo teste 1-1",
    "banner" :"matematica" ,
    "content_type" : "Matemática",
    "author": "Frederico",
    "publisher_id" : uuid.UUID(user["id"])
    },
    {"title": "conteudo exemplo Biologia 2",
    "pdf": pdf,
    "desc": "conteúdo teste 2-2",
    "banner" :"biologia" ,
    "content_type" : "Biologia",
    "author": "Frederico",
    "publisher_id" : uuid.UUID(user["id"])
    },
    
    {"title": "conteudo exemplo História 2",
    "pdf": pdf,
    "desc": "conteúdo teste 3-1",
    "banner" :"historia" ,
    "content_type" : "História",
    "author": "JAYRON",    
    "publisher_id" : uuid.UUID(user_["id"]),
    },
    {"title": "conteudo exemplo Português 2",
    "pdf": pdf,
    "desc": "conteúdo teste 4-1",
    "banner" : "portugues",
    "content_type" : "Português",
    "author": "JAYRON",
    "publisher_id" : uuid.UUID(user_["id"])
    }]
    for c in contents:
        print(c["banner"])
        
        if select_info(session, Contents, "title", c.get("title")):
            print("informação já existe no banco")
            continue
            
        print("inserindo")
        insert_info(session, Contents, c)
    session.close()
    
def make_users():
    session = database()
    users = [ {"name": "JAYRON",
    "password": make_hash("1081514Jh"),
    "cred" : UserCred.ADMIN,
    "picture" : None},  {"name": "Frederico",
    "password": make_hash("1081514Jh"),
    "cred" : UserCred.PROFESSOR,
    "picture" : None},  {"name": "Bolsonaro",
    "password": make_hash("1081514Jh"),
    "cred" : UserCred.STUDENT,
    "picture" : None}]
    for user in users:
        
        
        if select_info(session, User, "name", user.get("name")):
            print("informação já existe no banco")
            continue
            
        print("inserindo")
        insert_info(session, User, user)
    session.close()
    migrate_roles()
    
if __name__ == "__main__":
    make_users()
    make_contents()
    