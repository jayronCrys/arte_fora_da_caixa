from .user_default import Management_User_Default, Login_Account, check_user, Create_Account
from ...models.db_execute import insert_info, select_info, delete_info, update_info
from ...models.database import get_session as databas
from ...models.users_models.user_models import User

import logging

logger = logging.getLogger(__name__)

class Management_Admins(Management_User_Default):
    def __init__(self, Account, database):
        super().__init__(Account, database)
        self.validFields = ["name", "email", "password", "cred"]
        # assume que self.user é um dict vindo do select_info
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None

    @staticmethod
    @Login_Account.is_loged
    def is_admin(func):
        def wrapper(self, *args, **kwargs):
            if self.userRole and (str(self.userRole).lower().endswith("admin") or str(self.userRole).lower() == "admin"):
                return func(self, *args, **kwargs)
            return False
        return wrapper

    @is_admin
    def create_user_by_admin(self, userName, userPass, userCred):
        #--> hole deve ser um campo selecionável e não digitável
        if not userName or not userPass:
            return False

        conn = self.dataBase()
        try:
            ok = insert_info(conn, User, {
                "name": userName,
                "email": None, #--> não é permitido o método de email por usuários criados por admins
                "password": userPass,
                "picture": None,
                "cred": userCred
            })
            if not ok:
                return False
            user = select_info(conn, User, "name", userName, None)
            return True if user else None
        except Exception as e:
            logging.error(f"Erro ao adicionar usuário, motivo {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()

    @is_admin
    def get_user_by_admin(self, userName):
        conn = self.dataBase()
        try:
            db_task = select_info(conn, User, "name", userName)
            return db_task
        finally:
            conn.close()

    @is_admin
    def delete_user_by_admin(self, userName):
        conn = self.dataBase()
        try:
            db_task = delete_info(conn, User, "name", userName)
            return db_task
        finally:
            conn.close()

    @is_admin
    def update_user_by_admin(self, field, newValue, userName):
        if field not in self.validFields:
            return False
        conn = self.dataBase()
        try:
            db_task = update_info(conn, User, field, newValue, "name", userName)
            return db_task
        finally:
            conn.close()

    @is_admin
    def publish_content_by_admin(self, content, authorName):
        conn = self.dataBase()
        try:
            if content:
                author = select_info(conn, User, "name", authorName)
                if author:
                    # use objetos reais (publisher receberá objeto User ORM)
                    db_task = insert_info(conn, User, {})  # <-- aqui ajusta se você inserir na tabela Contents (corrigir modelo/params)
                    # OBS: no seu design, você deveria chamar insert_info(conn, Contents, {..., "publisher": author})
                    return True
            return False
        finally:
            conn.close()