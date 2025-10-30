
from .user_default import Login_Account
from ...content.assembler_content.manager_conversion import conversor
from ...content.manager_content import db_execute


class Management_Professors(Login_Account):
    def __init__(self, account, dataBase):
        super().__init__(account, dataBase)

    @staticmethod
    @Login_Account.is_loged
    def is_professor(func):   
        def wrapper(self, *args, **kwargs):
            if self.userHole == "Professor":
                return func(*args, **kwargs)        
            return False    
        return wrapper
    

    @is_professor
    def publisher_content(self, content):
        conn = self.dataBase()
        contentHtml, contentName = conversor(content)
            
        if contentHtml and contentName:
            db_task = db_execute.insert_info(conn, "contents", ["publisherId", "authorId", "contentName", "content"], 
                                            [self.userId, self.userId, contentName, contentHtml])
            return db_task


