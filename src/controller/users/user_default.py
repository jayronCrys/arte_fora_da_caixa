# /controller/users/user_default.py
import traceback
from src.controller.apis.google.google_login_api import client_ifo
from src.models.passwords import make_hash
from src.models.passwords import compare_password as compare
from src.models.database import get_session as database
from src.models.db_execute import insert_info, select_info, delete_info, update_info
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User
from src.models.relationships_models.inscriptions import Subs

from typing import Union
import re
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def check_user(seach, dataBase=database, collumn="name"):
    """
    dataBase -> função que retorna sessão (get_session)
    collumn -> coluna para busca (default "name")
    """
    # se for busca por id e seach for string, converte para UUID
    if collumn == "id" and isinstance(seach, str):
        try:
            seach = UUID(seach)
        except Exception:
            # se não conseguir converter, deixa como veio select_info vê com isso e retorna False
            pass

    conn = dataBase()
    try:
        userExist = select_info(conn, User, collumn, seach, None)
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
    def __init__(self, dataBase=database):
        self.dataBase = dataBase
        self.userName = None
        self.userPass = None

    def create_user(self, method, account: dict):  # -->account deve ser um dict
        if method == "google":
            if not account.get("name") or not account.get("email"):
                return False

        if method == "local":
            if not self.userName or not self.userPass:
                return False

        # --->self.userName e self.userPass são definidas nas funções de validação de nome e senha
        self.userName = account.get("name") or self.userName

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
            logger.info("senha de tamanho indevido")
            return False

        if pass1.replace(" ", "") != pass1:
            logger.info("A senha não pode conter espaços em branco")
            return False

        if (any(e.isdigit() for e in pass2) and
                any(e.isalpha() for e in pass2) and
                any(e.islower() for e in pass2) and
                any(e.isupper() for e in pass2)):
            # verifica em ordem se tem: digitos, letras, letras minusculas e maiusculas.
            self.userPass = make_hash(pass1)
            return True

        logger.info("senha muito fraca")
        return False

    def create_user_name(self, name):
        name = name.strip()# Tira espaços do inicio e fim
        if not name:
            return False

        # realName conserva o nome real, isso é necessário para manter os espaços entre duas palavras
        realName = " ".join(name.split())
        name = name.replace(" ", "")
        if len(name) < 5 or len(name) > 50:
            logger.info("Nome fora do range")
            return False

        if check_user(realName, self.dataBase):
            logger.info("Nome já existe")
            return False

        # Define os padrões aceitos para nome e verifica se é respeitado pelo user
        if re.match(r'^[A-Za-z0-9._-]+$', name):
            self.userName = realName
            return True
        logger.info("Nome contém caracteres não permitidos")
        return False


    @classmethod
    def creator(cls, creationMethod, userName=None, email: Union[dict, None] = None, pass1=None, pass2=None) -> bool:
        
        createUser = cls(database)
        user = None
        
        if creationMethod == "google" and email and email.get("name") and email.get("email"):
            user = createUser.create_user(creationMethod, email)

        # usando a conta local há uma sequência de validações
        elif creationMethod == "local" and userName and pass1 and pass2:
            if not createUser.create_user_name(userName):
                logger.info("Nome de usuário inválido")
                return False, None

            if not createUser.create_user_pass(pass1, pass2):
                logger.info("Senha não respeita as especificações")
                return False, None

            user = createUser.create_user(creationMethod, {
                "name": createUser.userName,
                "email": None,
                "picture": None
            })

        else:
            return False, None

        if user:
            logginMethod = creationMethod
            logger.info("Tentando fazer login automático")
            return Login_Account.login(logginMethod, user, True)
        return False, None


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
        self.cred = None

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

        # ---> todas essas informações devem ser garantidamente retornadas caso estejam definidas no banco de dados
        
        self.isLoged = True
        self.cred = self.user.get("cred")
        self.userId = self.user.get("id")
        self.email = self.user.get("email")
        self.userName = self.user.get("name")
        self.userPass = True
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
            logger.info("Nome e senha foram repassados")
            userNameIn = self.user.get("name")
            userPassIn = self.user.get("password")

            userExist = check_user(userNameIn, self.dataBase)

            if userExist and compare(userPassIn, userExist.get("password")):
                logger.info("Nome de usuário existe e a senha é igual a salva")
                self.user = userExist
                self.get_infor_user_verif()
                self.isLoged = True
                return self.isLoged, self.user

            logger.info("senhas diferentes")

        self.isLoged = False
        return self.isLoged, None

    @classmethod
    def login(cls, loginMethod, account: dict, redirectByCreateAccount=False) -> Union[bool, dict, None]:
        userLog = cls(account, database)
        userLoged, userAccount = False, None
        if redirectByCreateAccount:
            # evita recarregar o banco pra buscar informações, usa as informações contidas na account direcionada por create_account
            userLog.get_infor_user_verif(account)
            return True, account

        else:
            if loginMethod == "google":
                userLoged, userAccount = userLog.login_with_google_account()

            elif loginMethod == "local":
                userLoged, userAccount = userLog.login_with_local_account()

        # se userAccount não existe, tenta criar automaticamente
        if not (userAccount) and account and loginMethod == "google":
            logging.info("tentando criar uma conta com as informações")
            return Create_Account.creator(creationMethod=loginMethod,
                                          userName=account.get("name"),
                                          email=account)

        return userLoged, userAccount


class Management_User_Default(Login_Account):

    def __init__(self, account, dataBase=database):
        super().__init__(account, dataBase)

        self.get_infor_user_verif(account)

        self.manager_fields = ["name", "email", "password", "picture", "subs"]

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
    def update_user(self, field, newValue1, newValue2=None):
        if field in self.manager_fields:
            conn = self.dataBase()

            
            if field == "name":
                checker = Create_Account(self.dataBase)
                if not checker.create_user_name(newValue1):
                    print("Nome inválido")
                    return False
                newValue1 = checker.userName
            if field == "password":
                checker = Create_Account(self.dataBase)

                if not checker.create_user_pass(newValue1, newValue2):
                    print("senha invalida")
                    return False
                
                # verifica se não é a mesma senha
                realValue = check_user(self.userId, self.dataBase, "id")
                if realValue and compare(newValue1, realValue.get("password")):
                    logging.error("Senha idêntica à atual")
                    return False
                newValue1 = checker.userPass
                print("senhas não são iguais")
            
            try:
                ok = update_info(conn, User, field, newValue1, "id", self.userId)

                if not ok:
                    return False

                user_updated = check_user(self.userId, self.dataBase, "id")

                if user_updated:
                    self.user = user_updated
                    self.get_infor_user_verif(user_updated)

                return True

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
            db_task = delete_info(conn, User, "id", UUID(self.userId))
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
                    
    @Login_Account.is_loged   
    def get_content_by_id(self, contentId):
        print(f"[get_content_by_id] contentId recebido: '{contentId}', tipo: {type(contentId)}")
        conn = self.dataBase()
        
        try:
            content = select_info(
                conn,
                Contents,
                "id",
               UUID(contentId),
                ["id", "title", "desc", "banner", "content_type", "author", "creation_date", "publisher_id", "pdf"]
            )
            return content
            
        except:
            conn.rollback()
            return False            
        finally:
            conn.close()
        
        
    @Login_Account.is_loged
    def get_all_contents(self):
        conn = self.dataBase()
        
        try:
            
            all_contents = conn.query(Contents).all()
            # converte para dict ANTES de fechar a sessão
            result = []
            for c in all_contents:
                
                result.append({
                    "id":            str(c.id),
                    "title":         c.title,
                    "desc":          c.desc,
                    "banner":        c.banner,   # bytes ou None
                    "content_type":  c.content_type,
                    "author":        c.author,
                    "creation_date": c.creation_date,
                    "publisher_id":  str(c.publisher_id),
                })     
            return result
        except:
            conn.rollback()
            return False
            
        finally:            
            conn.close()
            

    @Login_Account.is_loged
    def check_inscription(self, contentId):
        conn = self.dataBase()
        if not self.get_content_by_id(contentId):
            
            return False
                   
        try:            
            sub = conn.query(Subs).filter_by(
                student_id=UUID(self.userId),
                content_id=UUID(contentId)
            ).first()
            
            if not sub:
                return False
              
            else:
                print("está incrito olha", sub.id)      
                conn.close()
                return str(sub.id)
        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            return True
        finally:                         
             conn.close()
             
             
             
    @Login_Account.is_loged
    def my_inscriptions(self):
        conn = self.dataBase()
        
        try:
            all_contents = conn.query(Subs).filter_by(student_id=UUID(self.userId)).all()
            
            if not all_contents:               
                return None
                
            print(all_contents)                
            result = []
            
            for c in all_contents:
                result.append({
                        "id":            str(c.id),
                        "student_id":         str(c.student_id),
                        "content_id":          str(c.content_id),
                        "creation_date":        c.creation_date,
                    })
                    
            print(result, "fujo antes ou nem?")                    
            return result
            
        except:
            print("estou fugindo dos meis problemas")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    @Login_Account.is_loged
    def new_inscription(self, contentId):
        
        try:
            if self.check_inscription(contentId):
                print("já inscrito nezze contudo")
            print("nao inscrito")                            
        except:
            print("Y"*25)
            traceback.print_exc()
            return True
            
        try:
            
            conn = self.dataBase()
            if not self.get_content_by_id(contentId):
                print("nao achei no banco")
                return False
                
            inscription = {
            "content_id": UUID(contentId),
            "student_id": UUID(self.userId)
            }
            if insert_info(conn, Subs, inscription):
                print("Aqui deu certo")
                return True
                             
        except:
             print("Y"*25)
             traceback.print_exc()
             print("cai vem aki")
             conn.rollback()
             return False
             
        finally:
             conn.close()
         
    @Login_Account.is_loged
    def remove_incription(self, contentId):
        conn = self.dataBase()
        inscriptionId = check_inscription(content_id)  
        if not isncriptionId:
            return False
        
        try:
            if delete_info(conn, Subs, "id", inscriptionId):
                return True
                
        except:
            conn.rollback()
            return False
            
        finally:
            conn.close()            
        
        