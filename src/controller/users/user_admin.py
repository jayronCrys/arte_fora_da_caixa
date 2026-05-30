from src.controller.users.user_default import Management_User_Default, Login_Account, check_user, Create_Account
from src.models.db_execute import insert_info, select_info, delete_info, update_info
from src.models.database import get_session as database
from src.models.passwords import compare_password as compare
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User, UserCred
from src.models.db_mongo_execute import delete_comment, get_comment_by_id, suspend_comment
import uuid
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class Management_Admins(Management_User_Default):
    def __init__(self, Account, database=database):
        super().__init__(Account, database)
        self.validFields = ["name", "email", "password", "cred"]
        self.contentValidFields = ["desc", "title", "banner", "pdf", "content_type"]
        # assume que self.user é um dict vindo do select_info
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None


    

    def is_admin(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user and self.userRole == "admin":
                return func(self, *args, **kwargs)
            else:
                logger.info("Acesso negado: usuário não logado ou sem permissão de administrador.")
                return None
        return wrapper
        
    
    def admin_required(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user and self.userRole == "admin":
                return func(self, *args, **kwargs)
            else:
                logger.info("Acesso negado: usuário não logado ou sem permissão de administrador.")
                return None
        return wrapper
    
    @admin_required    
    def all_users(self):
        conn = self.dataBase()
        all_users = conn.query(User).all()
        conn.close()
        return all_users
    @admin_required
    def create_user_by_admin(self, userName, userPass, userPassConfirm, userCred):
        #--> hole deve ser um campo selecionável e não digitável
        if not userName or not userPass:
            return False
        if not userCred in ["aluno", "professor" , "admin"]:
            logger.warning("Tipo de credencial inválido")
            return False
        else:
            if userCred == "aluno":
                userCred = UserCred.STUDENT
            elif userCred == "professor":
                userCred = UserCred.PROFESSOR
            elif userCred == "admin":
                userCred = UserCred.ADMIN
            else:
                return False
        
        conn = self.dataBase()
        checker = Create_Account(self.dataBase)
        if not checker.create_user_name(userName):
            return False
        if not checker.create_user_pass(userPass, userPassConfirm):
            return False
            
        try:
            ok = insert_info(conn, User, {
                "name": checker.userName,
                "email": None, #--> não é permitido o método de email por usuários criados por admins
                "password": checker.userPass,
                "picture": None,
                "cred": userCred
            })
            if not ok:
                return False
            user = select_info(conn, User, "name", userName, None)
            return True if user else None
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário, motivo {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()

    @admin_required
    def get_user_by_admin(self, userName):
        conn = self.dataBase()
        try:
            db_task = select_info(conn, User, "name", userName)
            return db_task
        finally:
            conn.close()
            
    @admin_required
    def delete_contents_by_admin(self, contentId):
        if not contentId:
            return False
            
        try:                              
            conn = self.dataBase()  
            contentExist = select_info(conn, Contents, "id", uuid.UUID(contentId))
            if contentExist:
                                      
                db_task = delete_info(conn, Contents, "id", uuid.UUID(contentId))
                
                if db_task : return True
                    
            return False
        finally:
                conn.close()
                
        if not contentId:
            return False           
        
        contentExist = self.professor_get_content_by_id(contentId)
        if contentExist:                        
            
            try:
                
                conn = self.dataBase()      
                db_task = delete_info(conn, Contents, "id", uuid.UUID(contentId))
                
                if db_task : return True
                    
                return False
            finally:
                conn.close()
                
    @admin_required
    def delete_user_by_admin(self, userId):
        conn = self.dataBase()
        try:
            db_task = delete_info(conn, User, "id", uuid.UUID(userId))
            return db_task
        finally:
            conn.close()

    @admin_required
    def update_user_by_admin(self, field, newValue, confirmValue, userId):
        if field not in self.validFields:
            logger.warning("parâmetro inválido")
            return False
        checker = Create_Account(self.dataBase)
        save_user = check_user(userId, self.dataBase, "id")
        if field == "name":
            if not checker.create_user_name(newValue):
                return False
            newValue = checker.userName                                            
        if field == "password":
            if not checker.create_user_pass(newValue, confirmValue):
                return False
            
            if compare(newValue, save_user.get("password")):
                logger.info("senhas indenticas")
                return False
            newValue = checker.userPass                
        if field == "cred":
            if newValue == "aluno":
                newValue = UserCred.STUDENT
            elif newValue == "professor":
                newValue = UserCred.PROFESSOR
            elif newValue == "admin":
                newValue = UserCred.ADMIN
            else:
                return False
        try:
            
            conn = self.dataBase()
            db_task = update_info(conn, User, field, newValue, "id", uuid.UUID(userId))
            logger.info("alteração feita com sucesso")
            return db_task
        finally:
            conn.close()
            
            
    @admin_required
    def get_all_contents_by_admin(self):
        print("vou tentar fazer conecao")
        conn = self.dataBase()
        print("fiz comeccao")
        all_contents = conn.query(Contents).all()
        conn.close()
        return all_contents
        
    @admin_required
    def get_content_by_admin(self, contentId):
        conn = self.dataBase()
        print("TENHO I TUPO",contentId)
        content = select_info(conn, Contents, "id", uuid.UUID(contentId), None)
        conn.close()
        return content
       
    @admin_required
    def update_contents_by_admin(self, columnUpdate, contentId, newValue):
        
        if not newValue or not contentId or not columnUpdate:
            return False
            
        if columnUpdate not in self.contentValidFields:
            return False
        
        if columnUpdate == "pdf":
            if not isinstance(newValue, bytes):
                return False
        
        try:                              
            conn = self.dataBase()  
            contentExist = select_info(conn, Contents, "id", uuid.UUID(contentId))
            if contentExist:
                                      
                db_task = update_info(conn, Contents, columnUpdate, newValue, "id", uuid.UUID(contentId))
                
                if db_task : return True
                    
            return False
        finally:
                conn.close()
                
    @admin_required
    def delete_comment_by_admin(self, commentId):
        
        if not self.get_content_by_id(contentId):
            return False
                        
        if not get_comment_by_id(contentId, commentId):
            return False
            
        try:   
            if delete_comment(contentId, commentId):
                return True
        except:
            return False
        
        
    """mudar o banco pra aceitat status ativo"""        
    @admin_required
    def suspended_content_by_admin(self, contentId):
              
        if not self.get_content_by_id(contentId):
            return False
            
        """try:   
            if suspend_comment(contentId):
                return True
        except:
            return False"""
        
    @admin_required        
    def suspended_comment_by_admin(seld, contentId, commentId):
        if not self.get_content_by_id(contentId):
            return False
                        
        if not get_comment_by_id(contentId, commentId):
            return False
            
        try:   
            if suspend_comment(contentId, commentId):
                return True
        except:
            return False
        
    @admin_required
    def publish_content_by_admin(self, content, authorName):
        conn = self.dataBase()
       
        try:
            if content:
                author = select_info(conn, User, "name", authorName)
                print("publicando conteudo", author)
                if author:
                    author = author.get("name")
                    print("meu id", self.userId)
                    db_task = insert_info(conn, Contents, {
                    "title":        content.get("title"),
                    "desc":         content.get("desc"),
                    "banner":       content.get("banner"),
                    "content_type": content.get("content_type"),
                    "pdf":          content.get("pdf"),
                    "author":       str(author),
                    "publisher_id": uuid.UUID(self.userId)
                })
                    if db_task:
                        content = conn.query(Contents).filter_by(title = content.get("title"), publisher_id = uuid.UUID(self.userId)).first()
                        return content.id
            return False
        finally:
            conn.close()