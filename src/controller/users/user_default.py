# /controller/users/user_default.py

#                         Caminhos dos meus módulos
#---------------------------------------------------------------------------------

from ..apis.google.google_loggin_api import client_ifo
from ...models.passwords import make_hash as hash
from ...models.passwords import compare_password as compare
from ...models.database import get_session as database
from ...models.db_execute import insert_info, select_info, delete_info, update_info
from ...models.contents_models.content_models import Contents
from ...models.users_models.user_models import User
from ...models.relationships_models.inscriptions import Subs

#----------------‐----------------------------------------------------------------
#                           Importações externas
#----------------‐----------------------------------------------------------------
from typing import Union
import re
import logging
#----------------‐----------------------------------------------------------------

logger = logging.getLogger(__name__)


def check_user(userName, dataBase):
    """
    dataBase -> função que retorna sessão (get_session)
    """
    conn = dataBase()
    try:
        userExist = select_info(conn, User, "name", userName, None)  # corrigido user_name -> name
        logger.info("Informações de usuário extraídas com sucesso")  
        return userExist

    except Exception as e:
        logger.error(f"Erro ao selecionar atributos de usuário, motivo {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False   

    finally:
        conn.close()


class Create_Account:
    def __init__(self, dataBase):
        self.dataBase = dataBase
        self.userName = None
        self.userPass = None


    def create_user(self, method, account: dict): #-->account deve ser um dict 
        if method == "google":
            if not account.get("userName") or not account.get("email"):
                return False
        
        if method == "local":
            if not self.userName or not self.userPass:
                return False
        
        #--->self.userName e self.userPass são definidas nas funções de validação de nome e senha
        self.userName = account.get("userName") or self.userName
                            
        conn = self.dataBase()
        try:
            ok = insert_info(conn, User, {
                "name": self.userName,
                "email": account.get("email"),
                "password": self.userPass, 
                "picture": account.get("picture")
            })
            if not ok:
                return False

            user = select_info(conn, User, "name", self.userName, None)
            return user
        
        except Exception as e:          
            logger.error(f"Erro ao adicionar usuário, motivo {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        
        finally:              
            conn.close()


    def create_user_pass(self, pass1, pass2):
        if pass1 != pass2 or len(pass1) < 8:
            return False

        if (any(e.isdigit() for e in pass2) and
            any(e.isalpha() for e in pass2) and
            any(e.islower() for e in pass2) and
            any(e.isupper() for e in pass2)):
            self.userPass = hash(pass1)
            return True

        return False
        

    def create_user_name(self, name):
        if len(name) < 5 or len(name) > 50:
            return False

        if check_user(name, self.dataBase):
            return False
               
        #Define os padrões aceitos para nome e verifica se é respeitado pelo user
        if re.match(r'^[a-z0-9._-]+$', name):
            self.userName = name
            return True

        return False


    @classmethod
    def creator(cls, creationMethod, userName=None, email: Union[dict, None] = None, pass1=None, pass2=None)->bool:
        createUser = cls(database)        
        user = None

        #usuários logando usando google, terão privilégios, não passam pela validação de nome
        if creationMethod == "google" and email and email.get("userName") and email.get("email"):
            user = createUser.create_user(creationMethod, email)
            
        #usando a conta local há uma sequência de validações            
        elif creationMethod == "local" and userName and pass1 and pass2:
            if not createUser.create_user_name(userName):
                return False
                           
            if not createUser.create_user_pass(pass1, pass2):
                return False
                                       
            user = createUser.create_user(creationMethod, {
                "userName": createUser.userName,
                "email": None,
                "picture": None
            })
            
        else:
            return False

        if user:
            logginMethod = creationMethod
            return Login_Account.login(logginMethod, user, True)    
        return False
    

class Login_Account:

    def __init__(self, account, dataBase):
        
        self.user = account
        self.dataBase = dataBase
        
        self.userName = None
        self.userPass = None
        self.email = None
        self.createDate = None
        self.picture = None
        self.userId = None
        self.isLoged = False       
        

    @staticmethod
    def is_loged(func):
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user:
                return func(self, *args, **kwargs)
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
        self.userName = self.user.get("name")
        self.userPass = "não te interessa, mas existe"
        self.createDate = self.user.get("creation_date")
        self.picture = self.user.get("picture")
        
    
    def login_with_google_account(self):
        if isinstance(self.user, dict):
            userNameIn = self.user.get("name")
            userEmailIn = self.user.get("email")
            
            userExist = check_user(userNameIn, self.dataBase)
            if userExist and userExist.get("email") == userEmailIn:
                self.user = userExist
                self.get_infor_user_verif()
                self.isLoged = True
                return self.isLoged, self.user
                    
        self.isLoged = False                            
        return self.isLoged, None

    
    def login_with_local_account(self):  
        if isinstance(self.user, dict):
            userNameIn = self.user.get("name")
            userPassIn = self.user.get("password")
            
            userExist = check_user(userNameIn, self.dataBase)       
            if userExist and compare(userPassIn, userExist.get("password")):
                self.user = userExist
                self.get_infor_user_verif()
                self.isLoged = True
                return self.isLoged, self.user
                
        self.isLoged = False
        return self.isLoged, None    



    @classmethod
    def login(cls, loginMethod, account:dict, redirectByCreateAccount=False)->Union[bool, dict, None]:

        userLog = cls(account, database)
        userLoged, userAccount = False, None

        if redirectByCreateAccount:
            #evita recarregar o banco pra buscar informações, usa as informações contidas na account direcionada por create_account
            userLog.get_infor_user_verif(account)
            return True, account
            
        else:
            if loginMethod == "google":                     
                userLoged, userAccount = userLog.login_with_google_account()

            elif loginMethod == "local":
                userLoged, userAccount = userLog.login_with_local_account()
        
        
        #se userAccount não existe, tenta criar automaticamente
        if not(userAccount) and account:
            create_local = Create_Account(database)
            return create_local.creator(loginMethod, account)
        
        return userLoged, userAccount
       
        


class Management_User_Default(Login_Account):

    def __init__(self, account, dataBase):
        super().__init__(account, dataBase)
        #Define os atributos que o usuário tem permissão para fazer update
        self.manager_fields = ["name", "email", "password"]


    @Login_Account.is_loged
    def get_user(self):
        return self.user
        
    @Login_Account.is_loged
    def get_user_name(self):
        return self.userName

    @Login_Account.is_loged
    def get_email(self):
        return self.email if self.email else "nenhum email associado á este perfil"

    @Login_Account.is_loged
    def update_user(self, field, newValue):
        if field in self.manager_fields:
            conn = self.dataBase()
            try:
                db_task = update_info(conn, User, field, newValue, "id", self.userId)
                return db_task
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                logging.error(f"Erro ao atualizar usuário: {e}")
                return False
            finally:
                conn.close()
        return False

    @Login_Account.is_loged
    def delete_user(self):   
        conn = self.dataBase()
        try:
            db_task = delete_info(conn, User, "id", self.userId)
            return db_task
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.error(f"Erro ao deletar usuário: {e}")
            return False
        finally:
            conn.close()