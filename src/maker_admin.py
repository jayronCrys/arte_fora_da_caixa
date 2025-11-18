
from src.models.database import get_session as database
from src.models.db_execute import insert_info, select_info
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User, UserCred
from src.models.relationships_models.inscriptions import Subs

from src.models.passwords import make_hash
banco = database()
from src.models.database import get_session

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
    