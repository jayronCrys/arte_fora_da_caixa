import traceback
import re
import logging
from uuid import UUID
from functools import wraps
from typing import Union, Tuple

from src.controller.apis.google.google_login_api import client_ifo
from src.models.passwords import make_hash
from src.models.passwords import compare_password as compare
from src.models.database import get_session as database
from src.models.db_execute import insert_info, select_info, delete_info, update_info
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User
from src.models.relationships_models.inscriptions import Subs
from src.models.db_mongo_execute import get_comments, get_reviews, new_comment, new_review, remove_content_inscription, get_comment_by_id, update_comment_and_review, get_comment_by_user_id
from src.Logs.terminal_logs import sucesfull_log, check_api, check_task, warning_log, error_log

logger = logging.getLogger(__name__)


def check_user(search, dataBase=database, column="name"):
    """
    dataBase -> função que retorna sessão (get_session)
    column -> coluna para busca (default "name")
    """
    if column == "id" and isinstance(search, str):
        try:
            search = UUID(search)
        except ValueError:
            pass

    conn = dataBase()
    try:
        user_exist = select_info(conn, User, column, search, None)
        logger.info("Informações de usuário extraídas com sucesso.")
        return user_exist
    except Exception as e:
        logger.error(f"Erro ao selecionar atributos de usuário: {e}")
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

    def create_user(self, method: str, account: dict):
        if method == "google" and (not account.get("name") or not account.get("email")):
            return False

        if method == "local" and (not self.userName or not self.userPass):
            return False

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

            return select_info(conn, User, "name", self.userName, None)
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()

    def create_user_pass(self, pass1: str, pass2: str) -> bool:
        if pass1 != pass2 or len(pass1) < 8:
            logger.info("Senha com tamanho indevido ou divergente.")
            return False

        if " " in pass1:
            logger.info("A senha não pode conter espaços em branco.")
            return False

        if (any(e.isdigit() for e in pass1) and
                any(e.isalpha() for e in pass1) and
                any(e.islower() for e in pass1) and
                any(e.isupper() for e in pass1)):
            self.userPass = make_hash(pass1)
            return True

        logger.info("Senha muito fraca.")
        return False

    def create_user_name(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False

        real_name = " ".join(name.split())
        name_without_spaces = name.replace(" ", "")
        
        if len(name_without_spaces) < 5 or len(name_without_spaces) > 50:
            logger.info("Nome fora do limite permitido.")
            return False

        if check_user(real_name, self.dataBase):
            logger.info("Nome de usuário já existe.")
            return False

        if re.match(r'^[A-Za-z0-9._-]+$', name_without_spaces):
            self.userName = real_name
            return True
        logger.info("Nome contém caracteres não permitidos.")
        return False

    @classmethod
    def creator(cls, creationMethod: str, userName=None, email: Union[dict, None] = None, pass1=None, pass2=None) -> Tuple[bool, Union[dict, None]]:
        create_account_instance = cls(database)
        user = None
        
        if creationMethod == "google" and email and email.get("name") and email.get("email"):
            user = create_account_instance.create_user(creationMethod, email)

        elif creationMethod == "local" and userName and pass1 and pass2:
            if not create_account_instance.create_user_name(userName):
                logger.info("Nome de usuário inválido.")
                return False, None

            if not create_account_instance.create_user_pass(pass1, pass2):
                logger.info("Senha não respeita as especificações.")
                return False, None

            user = create_account_instance.create_user(creationMethod, {
                "name": create_account_instance.userName,
                "email": None,
                "picture": None
            })
        else:
            return False, None

        if user:
            logger.info("Tentando realizar login automático pós-criação.")
            return Login_Account.login(creationMethod, user, redirectByCreateAccount=True)
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
        @wraps(func)  # Corrigido: Agora preserva metadados da função original
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user:
                return func(self, *args, **kwargs)
            return False
        return wrapper

    def get_infor_user_verif(self, user=None):
        if user:
            self.user = user
        
        self.isLoged = True
        self.cred = self.user.get("cred")
        self.userId = self.user.get("id")
        self.email = self.user.get("email")
        self.userName = self.user.get("name")
        self.userPass = True
        self.createDate = self.user.get("creation_date")
        self.picture = self.user.get("picture")

    def login_with_google_account(self) -> Tuple[bool, Union[dict, None]]:
        if isinstance(self.user, dict):
            user_name_in = self.user.get("name")
            user_email_in = self.user.get("email")

            user_exist = check_user(user_name_in, self.dataBase)

            if user_exist and user_exist.get("email") == user_email_in:
                self.user = user_exist
                self.get_infor_user_verif()
                return self.isLoged, self.user

        self.isLoged = False
        return self.isLoged, None

    def login_with_local_account(self) -> Tuple[bool, Union[dict, None]]:
        if isinstance(self.user, dict):
            logger.info("Nome e senha repassados para login local.")
            user_name_in = self.user.get("name")
            user_pass_in = self.user.get("password")

            user_exist = check_user(user_name_in, self.dataBase)

            if user_exist and compare(user_pass_in, user_exist.get("password")):
                logger.info("Usuário validado com sucesso.")
                self.user = user_exist
                self.get_infor_user_verif()
                return self.isLoged, self.user

            logger.info("Credenciais inválidas.")

        self.isLoged = False
        return self.isLoged, None

    @classmethod
    def login(cls, loginMethod: str, account: dict, redirectByCreateAccount=False) -> Tuple[bool, Union[dict, None]]:
        user_log = cls(account, database)
        
        if redirectByCreateAccount:
            user_log.get_infor_user_verif(account)
            return True, account

        user_logged, user_account = False, None
        if loginMethod == "google":
            user_logged, user_account = user_log.login_with_google_account()
        elif loginMethod == "local":
            user_logged, user_account = user_log.login_with_local_account()

        if not user_account and account and loginMethod == "google":
            logger.info("Conta Google não encontrada. Iniciando auto-criação.")
            return Create_Account.creator(creationMethod=loginMethod, userName=account.get("name"), email=account)

        return user_logged, user_account


class Management_User_Default(Login_Account):
    def __init__(self, account, dataBase=database):
        super().__init__(account, dataBase)
        self.get_infor_user_verif(account)
        self.manager_fields = ["name", "email", "password", "picture", "subs"]
    #______________________USER________________________
    @Login_Account.is_loged
    def get_user(self):
        return self.user

    @Login_Account.is_loged
    def get_user_name(self):
        return self.userName

    @Login_Account.is_loged
    def get_email(self):
        return self.email if self.email else "Nenhum email associado a este perfil."

    @Login_Account.is_loged
    def update_user(self, field: str, newValue1, newValue2=None) -> bool:
        if field not in self.manager_fields:
            return False

        conn = self.dataBase()

        if field == "name":
            checker = Create_Account(self.dataBase)
            if not checker.create_user_name(newValue1):
                logger.warning("Nome de atualização inválido.")
                conn.close()
                return False
            newValue1 = checker.userName

        elif field == "password":
            checker = Create_Account(self.dataBase)
            if not checker.create_user_pass(newValue1, newValue2):
                logger.warning("Nova senha não atende aos requisitos.")
                conn.close()
                return False
            
            real_value = check_user(self.userId, self.dataBase, "id")
            if real_value and compare(newValue1, real_value.get("password")):
                logger.error("A nova senha não pode ser idêntica à atual.")
                conn.close()
                return False
            newValue1 = checker.userPass
        
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
            logger.error(f"Erro ao atualizar usuário: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()

    @Login_Account.is_loged
    def delete_user(self) -> bool:
        conn = self.dataBase()
        try:
            return bool(delete_info(conn, User, "id", UUID(str(self.userId))))
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()
    #_____________________CONTENT_________________________
    @Login_Account.is_loged            
    def get_my_courses(self) -> list: 
        inscriptions = self.my_inscriptions()
        if not inscriptions:
            return []
            
        my_courses = []
        for inscription in inscriptions:
            content_id = inscription["content_id"]
            # Ajustado para usar o nome do método corrigido em snake_case
            course = self.GET_FULL_CONTENT(all_contents=False, content_to_select=content_id, review=True)
            
            if course and len(course) > 0:
                my_courses.append(course[0])
                    
        return my_courses
        
    @Login_Account.is_loged   
    def get_content_by_id(self, contentId: str):
        conn = self.dataBase()
        try:
            content = select_info(
                conn,
                Contents,
                "id",
                UUID(str(contentId)),
                ["id", "title", "desc", "banner", "content_type", "author", "creation_date", "publisher_id"]
            )
            sucesfull_log(f"[GET_CONTENT_BY_ID]: conteúdo retornado com sucesso {content['id']}")
            return content
            
        except Exception as e:
            error_log(f"[GET_CONTENT_BY_ID]: Erro ao obter conteúdo por ID {contentId}: {e}")
            return False            
        finally:
            conn.close()

    @Login_Account.is_loged
    def get_all_contents(self) -> Union[list, bool]:
        conn = self.dataBase()
        try:
            all_contents = conn.query(Contents).all()
            return [{
                "id":            str(c.id),
                "title":         c.title,
                "desc":          c.desc,
                "banner":        c.banner,
                "content_type":  c.content_type,
                "author":        c.author,
                "creation_date": c.creation_date,
                "publisher_id":  str(c.publisher_id),
            } for c in all_contents]
        except Exception as e:
            logger.error(f"Erro ao listar todos os conteúdos: {e}")
            return False
        finally:            
            conn.close()
            
    @Login_Account.is_loged            
    def get_content_by_name(self, content_name):
        
        if not content_name:
            return []
            
        conn = self.dataBase()
        # 1ª Tentativa: Busca exata
        results = conn.query(Contents).filter_by(title=content_name).all()
        
        # 2ª Tentativa: Se não achou nada na busca exata, busca por aproximação direto no banco
        if not results:
            results = conn.query(Contents).filter(Contents.title.contains(content_name)).all()
        temp_list = []
        for result in results:
            temp_json = {
            "id": str(result.id),
            "title": result.title,
            "desc": result.desc,
            "author": result.author
            }
            temp_list.append(temp_json)
                        
        return temp_list


    @Login_Account.is_loged
    def GET_FULL_CONTENT(self, all_contents=False, content_to_select=None, review=False) -> Union[list, bool]:
        # Corrigido nome para snake_case conforme PEP 8
        if not all_contents and content_to_select:
            contents = [self.get_content_by_id(content_to_select)]
        elif all_contents and content_to_select is None:
            contents = self.get_all_contents()
        else:
            return False
            
        full_content = []
        for content in contents:
            if not content:
                continue
                
            content_id = content["id"]
            if review:
                content["rating"] = self.get_content_review(content_id)
            
            full_content.append(content)
            check_task("RETORNO DE GET FULL CONTENT")
            check_task(full_content)
        return full_content
    #_____________________INSCRIPTIONS_________________________
    @Login_Account.is_loged
    def check_inscription(self, contentId: str) -> Union[str, bool]:
        if not self.get_content_by_id(contentId): 
            return False
            
        conn = self.dataBase()                   
        try:            
            sub = conn.query(Subs).filter_by(
                student_id=UUID(str(self.userId)),
                content_id=UUID(str(contentId))
            ).first()
            if sub.id:
                warning_log(f"[CHECK_INSCRIPTION]: inscrito no conteúdo {contentId}")
                return sub.id
                
            warning_log(f"[CHECK_INSCRIPTION]: usuário não inscrito no conteúdo {contentId}")
            return False
            
        except Exception as E:
            error_log("[CHECK_INSCRIPTION]")
            error_log(E)
            return False
        finally:                         
             conn.close()


    @Login_Account.is_loged
    def my_inscriptions(self) -> Union[list, bool]:
        conn = self.dataBase()
        try:
            all_contents = conn.query(Subs).filter_by(student_id=UUID(str(self.userId))).all()
            if not all_contents:               
                return []
                
            return [{
                "id":            str(c.id),
                "student_id":    str(c.student_id),
                "content_id":    str(c.content_id),
                "creation_date": c.creation_date,
            } for c in all_contents]
        except Exception as e:
            logger.error(f"Erro ao buscar inscrições: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()
            
    @Login_Account.is_loged
    def new_inscription(self, contentId: str) -> bool:
        if self.check_inscription(contentId):
            return True
            
        try:            
            conn = self.dataBase()
            if not self.get_content_by_id(contentId):
                return False
                
            inscription = {
                "content_id": UUID(str(contentId)),
                "student_id": UUID(str(self.userId))
            }
            if insert_info(conn, Subs, inscription):
                self.set_content_review(contentId=contentId, is_new_inscription=True, rating=0, comment=None)
                sucesfull_log("[NEW_INSCRIPTION]: novo estudante inscrito com sucesso")
                
                return True
            warning_log("[NEW_INSCRIPTION]: não foi possível efetuar cadastro do usuário no curso")
            return False
            
        except Exception as e:
             error_log("[NEW_INSCRIPTION]")
             error_log(e)
             try:
                 conn.rollback()
             except Exception as e:
                 error_log("[NEW_INSCRIPTION]")
                 error_log(e)
             return False
        finally:
             conn.close()
             
    @Login_Account.is_loged
    def remove_inscription(self, contentId: str) -> bool:
            # Corrigido: Nome do método unificado para 'remove_inscription'
            check_task(f"[REMOVE_INSCRIPTION]: executando com : {contentId}")
            conn = self.dataBase()
            inscription_id = self.check_inscription(contentId)  
            if not inscription_id:
                warning_log("[REMOVE_INSCRIPTION]: SEM INSCRIPTIOND ID")
                return False
            
            try:
                if delete_info(conn, Subs, "id", UUID(str(inscription_id))):
                    try:
                        if remove_content_inscription(contentId):
                            sucesfull_log(f"[REMOVE_INSCRIPTION]: Inscrição {inscription_id} removida com sucesso do SQL e MongoDB.")
                            return True
                        
                        warning_log("[REMOVE_INSCRIPTION]: Não foi possível remover inscrição em >remove_content_inscription<")                        
                        return False
                                                
                    except Exception as mongo_err:
                        error_log(f"[REMOVE_INSCRIPTION]:Inscrição removida do SQL, mas falhou no MongoDB")
                        error_log(mongo_err)
                        return False
                        
                warning_log("[REMOVE_INSCRIPTION]: Não foi possível remover inscrição em >delete_info<")          
                return False
            except Exception as e:
                logger.error(f"[REMOVE_INSCRIPTION]:Erro ao remover inscrição: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                return False
            finally:
                conn.close() #_______________________REVIEWS______________________
    
    
    @Login_Account.is_loged
    def get_content_review(self, contentId: str):
        if not contentId or not self.get_content_by_id(contentId):
            return False
            
        try:
            return get_reviews(contentId)
        except Exception as e:
            logger.error(f"Erro em get_reviews para o conteúdo {contentId}: {e}")
            return False            

    @Login_Account.is_loged
    def get_content_comment(self, contentId: str, moderated=False):
        if not contentId or not self.get_content_by_id(contentId):
            return False

        try:
            comments = get_comments(course_id=contentId, moderated=moderated)
            print("RETORNO DE GET_CPMM3ENTS", comments)
            return comments
                
        except Exception as e:
            logger.error(f"Erro em get_comments para o conteúdo {contentId}: {e}")
            return False
        
    @Login_Account.is_loged                   
    def set_content_review(self, contentId: str, is_new_inscription=False, rating=0, comment=None) -> bool:    
        if not self.get_content_by_id(contentId):
            return False
        try:        
            if is_new_inscription:
                new_review(course_id=contentId, review=0, new_inscription=is_new_inscription)
                return True
                
            # 🌟 CORRIGIDO: Ordem das validações alterada para evitar AttributeError caso comment seja None
            if comment is None or comment.strip() == "":
                comment = ""
                
            new_review(course_id=contentId, review=rating, new_inscription=is_new_inscription)
            new_comment(course_id=contentId, user_id=self.userId, user_name=self.userName, rating=rating, texto_comentario=comment)
            return True
        except Exception as e:
            logger.error(f"Erro ao inserir review/comentário: {e}")
            return False


    @Login_Account.is_loged
    def delete_my_comment(self, contentId: str, commentId: str):
        # Corrigido o nome para um padrão descritivo uniforme
        if not self.get_content_by_id(contentId):
            return False
            
        if not get_comment_by_id(contentId, commentId):
            return False
            
        try:                                    
            if delete_comment(contentId, commentId):
                sucesfull_log("[DELETE_MY_COMMENY]: comentário deletado com sucesso")
                return True
                
            warning_log("[DELETE_MY_COMMENY]: não foi possível deletar comentário")   
            return False
            
        except Exception as E:
            error_log("[DELETE_MY_COMMENY]")
            error_log(E)
            return False
            
    
            
    @Login_Account.is_loged
    def get_my_comment(self, contentId):
        try:
            if not self.check_inscription(contentId):
                return False
                
            sucesfull_log("[GET_MY_COMMENTS] RETORNOU COM SUCESSO")                                
            return get_comment_by_user_id(contentId, self.userId)
            
        except Exception as E:
            error_log("[GET_MY_COMMENT]")
            error_log(E)
            False
            
    @Login_Account.is_loged            
    def update_my_comment(self, contentId, rating,new_comment):
        
        if not self.check_inscription(contentId):
            return False
        try:          
            if update_comment_and_review(course_id=contentId,user_id=self.userId,user_name=self.userName,new_rating=rating,new_comment_text=new_comment):
                  sucesfull_log("[UPDATE COMMENT] RETORNOU COM SUCESSO")
                  return True
                  
        except Exception as E:
            
            error_log("[UPDATE_MY_COMMENT]")
            error_log(E)
            return False
            
                                                    