
#                         Caminhos dos meus módulos
#---------------------------------------------------------------------------------
from ..passwords import make_hash as hash
from ..passwords import compare_password as compare
from ...apis.google.google_loggin_api import client_ifo
from ...content.manager_content import hospedagem_aulas as database
from ...content.manager_content import db_execute
#----------------‐----------------------------------------------------------------
#                           Importações externas
#----------------‐----------------------------------------------------------------
from datetime import datetime
from typing import Union
import uuid #-> vai ser desnecessario quando usa um banco de vdd
import re
import logging
#slite3 está contido no arquivo hospedafem_aulas
#----------------‐----------------------------------------------------------------


def check_user(userName, dataBase):
    conn = dataBase()
    try:
        userExist = db_execute.select_info(database, "USERS", "user_name", "*", userName).fetchone()
        logging.info("Informações de usuário extraidas com sucesso")  
        return userExist

    except Exception as e:
        logging.error(f"Erro ao selecionar atributos de usuário, motivo {e}")
        return False   

    finally:
        conn.close()
        logging.info("Banco de dados fechado com sucesso")


class Create_Account:
    def __init__(self, dataBase):
        self.dataBase = dataBase
        self.userEmail = None
        self.userName = None
        self.userPass = None
        self.userId = None
        self.picture = None


    def create_user(self, userName=None, method=None, email=None):
        
        if userName is not None:
            self.userName = userName
            
        self.userEmail = email
        if self.userName and (self.userPass or (method == "google" and email)):
            try:
                self.userId = str(uuid.uuid4())#essa definicão nao vai existir, id vai ser um default no db
                conn = self.dataBase()
                db_execute(self.dataBase, "USERS", ["user_id", "user_name", "password", "email"] , [self.userId, self.userName, self.userPass, self.userEmail])
                
                user = {"user_id": self.userId,
                             "name": self.userName,
                              "email": self.userEmail,
                              "password": True, #->nao expoe a senha
                              "picture": self.picture,
                              "creationDate": datetime.today()}
                logging.info(f"Novo usuário {self.userName} adicionado com sucesso")
                
                return user

            except Exception as e:          
                logging.error("Erro ao adicionar usuário , motivo {e}")
                logging.warning("Desfazendo alterações no banco")
                conn.rollback()
                
                return False
                
            finally:              
                conn.close()
                logging.info("Banco de dados fechado com sucesso")
               
        return False


    def create_user_pass(self, pass1, pass2):

        if pass1 != pass2:
            return False      

        if len(pass1) < 8:
            return False

        if (any(e.isdigit() for e in pass1) and
            any(e.isalpha() for e in pass1) and
            any(e.islower() for e in pass1) and
            any(e.isupper() for e in pass1)):
            self.userPass = hash(pass1)
            return True

        return False
        

    def create_user_name(self, name):

        if len(name) < 5 or len(name) > 50:
            return False

        if check_user(name, self.dataBase):
            return False
               
 #Define os padrões aceitos para nome e verifica se é respeitado pelo user
        pattern = re.compile(r'^[a-z0-9._-]+$')
        pattern = pattern.match(name)

        if pattern:
            self.userName = name
            return True

        return False


    @classmethod
    def creator(cls, creationMethod, userName, email=None, pass1=None, pass2=None)->bool :

        dataBase = database.init_db
        createUser = cls(dataBase)        
        user = None
        #usuários aud loggando udando google, teram privilégios, eles não passaram pela 
        #validação de nome e não precisarão de senha, apenas da conta google.
        if creationMethod == "google" and (userName and email) :
            user = createUser.create_user(userName, creationMethod, email)
            
        elif creationMethod == "local" and (userName and pass1 and pass2):           
            if not createUser.create_user_name(userName):
                return False
                           
            if not createUser.create_user_pass(pass1, pass2):
                return False
                                       
            user = createUser.create_user()
          
        else:
            return False

        if user:
             logginMethod = creationMethod
             Login_Account.login(logginMethod, user)
        
        return False


class Login_Account:

    def __init__(self, account, dataBase):
        self.userName = None
        self.userPass = None
        self.email = None
        self.createDate = None
        self.user = None
        self.isLoged = False       
        self.account = account
        self.dataBase = dataBase

    @staticmethod
    def is_loged(self, func):
        def wrapper(*args, **kwargs):
            if self.isLoged and self.user:
                return func(*args, **kwargs)
                
            else:
                return False
                
        return wrapper


    def get_infor_user_verif(self, user=None): 
        if user:
            self.user = user
            self.isLoged = True
        
        #---> todas essas informações devem ser garantidamente retornadas caso estejam definidas no banco de dados
        self.userId = self.user.get("id")
        self.email = self.user.get("email")
        self.userName = self.user.get("user_name")
        self.userPass = self.user.get("password")
        self.createDate = self.user.get("creation_date")
        self.picture = self.user.grt("picture")
          
    
    def login_with_google_account(self):    
        userNameIn, emailIn = self.account  
        if not self.user:
            self.user = check_user(userNameIn, self.dataBase)

        if self.user:
            self.get_infor_user_verif()
            self.isLoged = True

            return self.isLoged, self.user
            
        if not(self.user) and self.userName and self.email:           
            self.isLoged = False

        return self.isLoged, None

    
    def login_with_local_account(self):  
        userNameIn,  userPassIn = self.account
        if not self.user:
            self.user = check_user(userNameIn, self.dataBase)

        if self.user:
            #Compara a senha informada pelo usuário com a senha associada ao user name no banco
            if compare(userPassIn, self.userPass):
            #->>> checar se capare recebe um user ou a senha direto
                self.get_infor_user_verif()
                self.isLoged = True
                
                return self.isLoged, self.user
                
        self.isLoged = False
        return self.isLoged, None    



    
    #Onde logginMethod deve vir de uma url direcionada ao main flask e redicecionada a este cls mthd
    #Account pode ser uma lista contendo nome e senha, para situção para loggin convencional, ou um dict para--
    #loggin com google
    #O método vai retornar se o user está logado ou não, caso esteja, retorna como segundo parâmetro --
    #um dicionário, caso não esteja loggado o segundo parâmentro é None.
    @classmethod
    def login(cls, loginMethod, account:dict, redirectByCreateAccount=False)->Union[bool, dict, None]:

        dataBase = database.init_db
        userLog = cls(account, dataBase)
        userLoged, userAccount = False, None

        if redirectByCreateAccount:
            #evita recarregar o banco pra buscar informações, usa as iformações contidas a account direcionada por create_account
            userLoged = userLog.get_infor_user_verif(account)
              
        else:
            if loginMethod == "google":                     
                userLoged, userAccount = userLog.login_with_google_account()

            elif loginMethod == "Local":
                userLoged, userAccount = userLog.login_with_local_account()
        
            if not(userAccount) and account:
                create_loccal = Create_Account()
                return create_loccal.creator(loginMethod, account)
        
        return userLoged, userAccount
       
        


class Management_User(Login_Account):

    def __init__(self, account, dataBase):
        super().__init__(account, dataBase)
        #Define os atributos que o usuário tem permissão para fazer update
        self.manager_fields = ["user_name", "email", "passWord"]

    @Login_Account.is_loged
    def get_user(self):
        return self.userName

    @Login_Account.is_loged
    def get_email(self):
        return self.email if self.email else "nenhum email associado á este perfil"

    @Login_Account.is_loged
    def update_user(self, field, newValue):
        if field not in self.manager_fields:
            conn = self.dataBase()
            db_task = db_execute.update_ifo(conn, "USERS", field, "id", self.userId, newValue)
            return db_task
 
        return False

    @Login_Account.is_loged
    def delete_user(self):   
        conn = self.dataBase()
        db_task = db_execute.delete_info(conn, "users", "id", self.id)
        return db_task
 