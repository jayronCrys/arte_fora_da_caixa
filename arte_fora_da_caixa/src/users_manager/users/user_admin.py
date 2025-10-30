
from .user_default import Login_Account
from content.assembler_content.manager_conversion import conversor
from ...content.manager_content import db_execute

#----> classe de controlador, não vou adicionar um fabricante,  ele precisaria receber uma request para tomar a decisão e não quero essa injeção de dependencia,
#o main deve cuidar de chamar o método requerido
class Management_Admins(Login_Account):
    def __init__(self, Account, database):
        super().__init__(Account, database)
        self.validFields = ["userName", "email", "password", "role"]
        
        self.userHole = self.user["hole"] #---> o atributo de hole só está disponível para user com propriedades diferentes de default = aluno,
#por isso não está disponível na classe herdada, nela não é usado para verificação já que suas permissões estão disponíveis a todas as credenciais de nível acima.

    @staticmethod
    @Login_Account.is_loged
    def is_admin(func):
        
        def wrapper(self, *args, **kwargs):
            if self.userHole == "Admin":
                return func(*args, **kwargs)
                
            return False
            
        return wrapper
    

    @is_admin
    def create_user_by_admin(self, userName, userPass, Hole):
#--> hole deve ser um campo selecionável e não digitável
        db_task = db_execute.insert_info(self.dataBase, "users", [userName, userPass, Hole],
                                                  [userName, userPass, Hole])
        return db_task
    

    @is_admin
    def get_user_by_admin(self, userName):#---> user name é o identificador do target de return
        conn = self.dataBase()
        db_task = db_execute.select_info(conn, "users", "*", "userName",userName)
        return db_task
              
    

    @is_admin
    def delete_user_by_admin(self, userName):      
        conn = self.dataBase()
        db_task = db_execute.delete_info(conn, "users", "userName", userName)
        return db_task
        

    @is_admin
    def update_user_by_admin(self, field, newValue, userName):
        if field not in self.validFields:
            return False
        
        conn = self.dataBase()
        db_task = db_execute.update_ifo(conn, "users", field, "userName", userName, newValue)
        return db_task
        
    

    @is_admin
    def publish_content_by_admin(self, content, author):
#---> author é um parâmetro que apenas admin tem acesso de informar, esse parâmetro é adicionado automáticamente para credenciais abaixo,
#assim embora o publicador seja um admin o nome de author pode ser algum qualquer. Mesmo o author tendo seu nome editável, o publicador,
#no caso o admin, ainda sim terá seu id associado a publicação indiscriminadamente de maneira não opcional
      
        conn = self.dataBase()
        contentHtml, contentName = conversor(content)

         if contentHtml and contentName:
             authorId = db_execute.select_info(conn, "users", "userName", "id", author)
             db_task = db_execute.insert_info(conn, "contents", ["publisherId", "authorId", "contentName", "content"],
                                                [self.userId, authorId, contentName, contentHtml])
             return db_task
                

               
