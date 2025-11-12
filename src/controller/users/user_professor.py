from src.controller.users.user_default import Management_User_Default, Login_Account
from src.models.db_execute import insert_info
from src.models.contents_models.content_models import Contents

class Management_Professors(Management_User_Default):
    def __init__(self, account, dataBase):
        super().__init__(account, dataBase)
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None

    @staticmethod
    @Login_Account.is_loged
    def is_professor(func):
        def wrapper(self, *args, **kwargs):
            if self.userRole and (str(self.userRole).lower().endswith("professor") or str(self.userRole).lower() == "professor"):
                return func(self, *args, **kwargs)
            return False
        return wrapper

    @is_professor
    def publish_content_by_professor(self, content):
        conn = self.dataBase()
        try:
            if content:
                # publisher pode ser o objeto ORM do user ou seu id; aqui passamos o objeto self.user (se for ORM)
                db_task = insert_info(conn, Contents, {
                    "title": content.get("fileName"),
                    "desc": content.get("description"),
                    "pdf": content.get("file"),
                    "author": self.user.get("name") if isinstance(self.user, dict) else getattr(self.user, "name", None),
                    "publisher": self.user  # funciona se insert_info e Contents aceitarem objeto relacionável
                })
                return db_task
            return False
        finally:
            conn.close()