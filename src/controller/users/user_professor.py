from src.controller.users.user_default import Management_User_Default, Login_Account
from src.models.db_execute import insert_info, select_info, delete_info, update_info
from src.models.contents_models.content_models import Contents
from functools import wraps
from src.models.database import get_session as database
from src.models.db_mongo_execute import delete_comment, get_comment_by_id, suspend_comment
import uuid


class Management_Professors(Management_User_Default):
    def __init__(self, account, dataBase=database):
        super().__init__(account, dataBase)
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None
        self.contentValidFields = ["desc", "title", "banner", "pdf", "content_type"]
    def professor_required(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user and self.userRole == "professor":
                return func(self, *args, **kwargs)
            else:
                logger.info("Acesso negado: usuário não logado ou sem permissão de professor.")
                return None
        return wrapper

    """tem que modificae a tela de home page, pra expor esses conteudo, apos isso já da pra fazer a primeirs entrega"""
    @professor_required
    def select_contents_by_publisher_id(self):
        if not self.userId:
            return False
        userId = [uuid.UUID(self.userId)]
        try:
            conn = self.dataBase()
            all_my_contents = conn.query(Contents).filter(Contents.publisher_id.in_(userId)).all()
            return all_my_contents
        finally:
            conn.close()        
            
    @professor_required
    def professor_get_content_by_id(self, contentId):
        if not self.userId:
            return False
            
        try:
            conn = self.dataBase()
            contentExist = select_info(conn, Contents, "id", uuid.UUID(contentId))
            
            if contentExist:                               
                if contentExist.get("publisher_id") == self.userId:
                    return contentExist
                                   
            return False                
        finally:
            conn.close()        
            
    @professor_required
    def delete_contents_by_id(self, contentId):
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
        
    @professor_required
    def update_contents_by_id(self, columnUpdate, contentId, newValue):
        
        if not newValue or not contentId or not columnUpdate:
            return False
            
        if columnUpdate not in self.contentValidFields:
            return False
        
        if columnUpdate == "pdf":
            if not isinstance(newValue, bytes):
                return False
        contentExist = self.professor_get_content_by_id(contentId) 
        if contentExist:                        
            
            try:
                
                conn = self.dataBase()      
                db_task = update_info(conn, Contents, columnUpdate, newValue, "id", uuid.UUID(contentId))
                
                if db_task : return True
                    
                return False
            finally:
                conn.close()
                
    #adicionar campo de "ativo" no banco de dados pra permitir status suspenso ou não de content
    
    @professor_required
    def suspended_content_by_professor(self, contentId):
        
        if not self.get_content_by_id(contentId):
            return False
                        
        if not self.professor_get_content_by_id(contentId):
            return False
            
        #try:   
            #if suspend_comment(contentId, commentId):
                #return True
        #except:
            #return False
            
        
    @professor_required        
    def suspended_comment_by_professor(self, commentId, contentId):
              
        if not self.get_content_by_id(contentId):
            return False
                        
        if not get_comment_by_id(contentId, commentId):
            return False
        
        if not self.professor_get_content_by_id(contentId):
            return False
            
        try:   
            if suspend_comment(contentId, commentId):
                return True
        except:
            return False    
        
    @professor_required
    def publish_content_by_professor(self, content, author):
        
        if author != self.get_user_name():
            return False
        author = self.userId
        try:
            if content:               
                if author:
                    conn = self.dataBase()
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
                        content = conn.query(Contents).filter_by(title=content.get("title"), publisher_id=uuid.UUID(self.userId)).first()
                        return content.id
            return False
        finally:
            conn.close()