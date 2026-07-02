import traceback
import re
import logging
from uuid import UUID
from functools import wraps
from typing import Union, Tuple
from datetime import datetime

from apis.google.google_login_api import client_ifo

from src.models.passwords import make_hash, compare_password as compare

from src.models.database import get_session as database

from src.models.db_execute import insert_info, select_info, delete_info, update_info

from src.models.contents_models.content_models import Contents

from src.models.users_models.user_models import User

from src.models.relationships_models.inscriptions import Subs

from src.models.db_mongo_execute import (
    get_comments,
    get_reviews,
    get_reviews_bulk,
    new_comment,
    new_review, 
    remove_content_inscription,
    get_comment_by_id, 
    update_comment_and_review,
    delete_comment,
    get_comment_by_user_id
)

from src.Logs.terminal_logs import(
    sucesfull_log,
    check_api,
    check_task,
    warning_log,
    error_log
)  

from src.controller.storage.s3_content_storage import generate_pdf_download_url, generate_pdf_view_url, build_pages_base_url

logger = logging.getLogger(__name__)

# src/controller/users/user_default.py (adicione ao final, fora das classes)

def reset_user_password(user_id, new_password):
    """
    Altera a senha de um usuário sem exigir login.
    Retorna True se bem-sucedido, False em caso de erro.
    """
    conn = database()
    try:
        # Verifica existência
        user = check_user(user_id, dataBase=database, column="id")
        if not user:
            logger.warning(f"Tentativa de redefinir senha de usuário inexistente: {user_id}")
            return False

        # Hash da nova senha (reaproveita lógica do Create_Account)
        hashed = make_hash(new_password)

        # Atualiza no banco
        ok = update_info(conn, User, "password", hashed, "id", user_id)
        if ok:
            logger.info(f"Senha do usuário {user_id} redefinida com sucesso.")
            return True
        else:
            logger.error(f"Falha ao atualizar senha do usuário {user_id}")
            return False
    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        conn.close()
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
        @wraps(func)
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
            if not user_exist:
                user_email_in = self.user.get("name")
                user_exist = check_user(search=user_email_in.lower(), dataBase=self.dataBase, column="email")#necwssario caso o usuario tente logar usando email pela barra de nomr

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
    
    _cache = {}          # { chave: (valor, timestamp) }

    @classmethod
    def _cache_get(cls, key, ttl_seconds=300):
        if key in cls._cache:
            value, timestamp = cls._cache[key]
            if (datetime.now() - timestamp).total_seconds() < ttl_seconds:
                return value
            del cls._cache[key]
        return None

    @classmethod
    def _cache_set(cls, key, value):
        cls._cache[key] = (value, datetime.now())
        
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
        if field not in self.manager_fields or not newValue1:
            return False

        conn = self.dataBase()
        if field == "email": 
            if check_user(newValue1, self.dataBase, field):
                logger.warning("email já utilizado.")
                conn.close()
                return False
            
        if field == "name":
            checker = Create_Account(self.dataBase)
            if not checker.create_user_name(newValue1):
                logger.warning("Nome de atualização inválido.")
                conn.close()
                return False
            newValue1 = checker.userName

        elif field == "password":
            real_value = check_user(self.userId, self.dataBase, "id")
            if real_value and compare(newValue1, real_value.get("password")):
                logger.error("A nova senha não pode ser idêntica à atual.")
                conn.close()
                return False

            checker = Create_Account(self.dataBase)
            if not checker.create_user_pass(newValue1, newValue2):
                logger.warning("Nova senha não atende aos requisitos.")
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

    @Login_Account.is_loged            
    def get_my_courses(self) -> list:
        """
        Retorna os cursos em que o usuário está inscrito.
        Otimizado para evitar N+1: antes fazia uma consulta ao banco + uma
        chamada ao MongoDB POR curso inscrito. Agora faz 1 consulta SQL em
        lote (IN) + 1 chamada em lote ao MongoDB, independente de quantos
        cursos o usuário tenha.
        """
        inscriptions = self.my_inscriptions()
        if not inscriptions:
            return []

        content_ids_raw = [str(i["content_id"]) for i in inscriptions]

        conn = self.dataBase()
        try:
            rows = conn.query(Contents).filter(
                Contents.id.in_([UUID(cid) for cid in content_ids_raw])
            ).all()
            contents_by_id = {
                str(c.id): {
                    "id":            str(c.id),
                    "title":         c.title,
                    "desc":          c.desc,
                    "banner":        c.banner,
                    "content_type":  c.content_type,
                    "author":        c.author,
                    "creation_date": c.creation_date,
                    "publisher_id":  str(c.publisher_id),
                    "s3_uuid":       c.s3_uuid,
                    "total_paginas": c.total_paginas,
                } for c in rows
            }
        except Exception as e:
            logger.error(f"Erro ao buscar conteúdos das inscrições em lote: {e}")
            return []
        finally:
            conn.close()

        if not contents_by_id:
            return []

        all_stats = get_reviews_bulk(list(contents_by_id.keys()))
        for content_id, content in contents_by_id.items():
            content["rating"] = all_stats.get(content_id, {
                "average_rating": 0.0,
                "total_reviews": 0,
                "total_inscriptions": 0,
                "sums_reviews": 0,
            })
            if content.get("s3_uuid") and not content.get("url_base_s3"):
                content["url_base_s3"] = build_pages_base_url(content["s3_uuid"])

        # Preserva a ordem original das inscrições.
        return [
            contents_by_id[cid] for cid in content_ids_raw if cid in contents_by_id
        ]

    @Login_Account.is_loged
    def get_my_courses_cached(self, ttl=600):
        """
        Wrapper com cache em memória (TTL) sobre get_my_courses(). Corrigido:
        antes estava com indentação incorreta (definido dentro do corpo de
        GET_FULL_CONTENT, após seus `return`), o que o tornava código morto —
        nunca era de fato um método da classe, e por isso o cache nunca
        chegava a ser usado.
        """
        cache_key = f"my_courses_{self.userId}"
        cached = self._cache_get(cache_key, ttl)
        if cached is not None:
            return cached
        courses = self.get_my_courses()
        self._cache_set(cache_key, courses)
        return courses
        
    @Login_Account.is_loged   
    def get_content_by_id(self, contentId: str):
        conn = self.dataBase()
        try:
            content = select_info(
                conn,
                Contents,
                "id",
                UUID(str(contentId)),
                ["id", "title", "desc", "banner", "content_type", "author", "creation_date",
                 "publisher_id", "s3_uuid", "total_paginas"]
            )
            if not content:
                warning_log(f"[GET_CONTENT_BY_ID]: conteúdo {contentId} não encontrado")
                return False

            sucesfull_log(f"[GET_CONTENT_BY_ID]: conteúdo retornado com sucesso {content['id']}")
            return content
            
        except Exception as e:
            error_log(f"[GET_CONTENT_BY_ID]: Erro ao obter conteúdo por ID {contentId}: {e}")
            return False            
        finally:
            conn.close()

    @Login_Account.is_loged
    def get_all_contents(self, limit=None, offset=None,
                         search=None, content_type=None,
                         popularity=None, sort=None) -> Union[list, dict, bool]:
        conn = self.dataBase()
        try:
            query = conn.query(Contents)
    
            # Filtro por nome (busca textual)
            if search:
                query = query.filter(Contents.title.ilike(f'%{search}%'))
    
            # Filtro por tipo de conteúdo
            if content_type and content_type != 'all':
                query = query.filter(Contents.content_type == content_type)
    
            # Ordenação por data
            if sort == 'oldest':
                query = query.order_by(Contents.creation_date.asc())
            else:  # recent
                query = query.order_by(Contents.creation_date.desc())
    
            total = query.count()

            # Quando popularidade está ativa, busca tudo primeiro para ordenar
            # antes de paginar — caso contrário limit/offset são aplicados no SQL
            applying_popularity = popularity in ('most_enrolled', 'most_reviewed')

            if limit is not None and not applying_popularity:
                query = query.limit(limit)
                if offset is not None:
                    query = query.offset(offset)
    
            all_contents = query.all()
    
            items = [{
                "id":            str(c.id),
                "title":         c.title,
                "desc":          c.desc,
                "banner":        c.banner,
                "content_type":  c.content_type,
                "author":        c.author,
                "creation_date": c.creation_date,
                "publisher_id":  str(c.publisher_id),
                "s3_uuid":       c.s3_uuid,
                "total_paginas": c.total_paginas,
            } for c in all_contents]
    
            # Popularidade: ordena por stats do MongoDB em 1 query e só então pagina
            if applying_popularity:
                all_stats = get_reviews_bulk([item['id'] for item in items])
                for item in items:
                    s = all_stats.get(item['id'], {})
                    item['_total_inscriptions'] = s.get('total_inscriptions', 0)
                    item['_total_reviews'] = s.get('total_reviews', 0)

                if popularity == 'most_enrolled':
                    items.sort(key=lambda x: x['_total_inscriptions'], reverse=True)
                elif popularity == 'most_reviewed':
                    items.sort(key=lambda x: x['_total_reviews'], reverse=True)

                for item in items:
                    item.pop('_total_inscriptions', None)
                    item.pop('_total_reviews', None)

                # Paginação manual após a ordenação por popularidade
                if limit is not None:
                    off = offset or 0
                    items = items[off: off + limit]
    
            if limit is not None:
                return {"items": items, "total": total}
            return items
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
        try:
            results = conn.query(Contents).filter_by(title=content_name).all()
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
        finally:
            conn.close()

    @Login_Account.is_loged
    def GET_FULL_CONTENT(self, all_contents=False, content_to_select=None, review=False,
                         limit=None, offset=None, search=None, content_type=None,
                         popularity=None, sort=None) -> Union[list, dict, bool]:
        if not all_contents and content_to_select:
            contents = [self.get_content_by_id(content_to_select)]
        elif all_contents and content_to_select is None:
            result = self.get_all_contents(limit=limit, offset=offset,
                                           search=search, content_type=content_type,
                                           popularity=popularity, sort=sort)
            if not result:
                return False
            contents = result["items"]
            total = result["total"]
        else:
            return False
    
        full_content = []

        # Busca ratings de todos os itens de uma vez (1 query MongoDB)
        if review and contents:
            valid_ids = [c["id"] for c in contents if c]
            all_stats = get_reviews_bulk(valid_ids)
        else:
            all_stats = {}

        for content in contents:
            if not content:
                continue
            content_id = content["id"]
            if review:
                content["rating"] = all_stats.get(content_id, {
                    "average_rating": 0.0,
                    "total_reviews": 0,
                    "total_inscriptions": 0,
                    "sums_reviews": 0,
                })
            if content.get("s3_uuid") and not content.get("url_base_s3"):
                content["url_base_s3"] = build_pages_base_url(content["s3_uuid"])
            full_content.append(content)
    
        if all_contents and content_to_select is None:
            return {"items": full_content, "total": total}
        return full_content

    @Login_Account.is_loged
    def get_content_download_url(self, contentId: str):
        content = self.get_content_by_id(contentId)
        if not content:
            return False

        s3_uuid = content.get("s3_uuid") or contentId
        try:
            return generate_pdf_download_url(s3_uuid, content.get("title", "material"))
        except Exception as e:
            error_log(f"[GET_CONTENT_DOWNLOAD_URL]: falha ao gerar link de download de {contentId}: {e}")
            return False

    @Login_Account.is_loged
    def get_content_view_url(self, contentId: str):
        content = self.get_content_by_id(contentId)
        if not content or not content.get("s3_uuid"):
            return False

        try:
            return generate_pdf_view_url(content["s3_uuid"])
        except Exception as e:
            error_log(f"[GET_CONTENT_VIEW_URL]: falha ao gerar link de visualização de {contentId}: {e}")
            return False

    @Login_Account.is_loged
    def check_inscription(self, contentId: str) -> Union[str, bool]:
        """
        Verifica a inscrição diretamente sem chamar get_content_by_id antes.
        Retorna id da inscrição ou False.
        """
        conn = self.dataBase()                   
        try:            
            sub = conn.query(Subs).filter_by(
                student_id=UUID(str(self.userId)),
                content_id=UUID(str(contentId))
            ).first()
            
            if sub and sub.id:
                warning_log(f"[CHECK_INSCRIPTION]: inscrito no conteúdo {contentId}")
                return str(sub.id)
                
            warning_log(f"[CHECK_INSCRIPTION]: usuário não inscrito no conteúdo {contentId}")
            return False
            
        except Exception as E:
            error_log(f"[CHECK_INSCRIPTION]: Erro ao checar inscrição: {E}")
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
            
        conn = self.dataBase()
        try:            
            # Validação se o conteúdo existe de fato no sistema
            if not self.get_content_by_id(contentId):
                return False
                
            inscription = {
                "content_id": UUID(str(contentId)),
                "student_id": UUID(str(self.userId))
            }
            if insert_info(conn, Subs, inscription):
                self.set_content_review(contentId=contentId, is_new_inscription=True, rating=0, comment=None)
                
                # Invalidação do Cache: Remove a chave em cache para forçar recarregamento na próxima chamada
                self._cache.pop(f"my_courses_{self.userId}", None)
                
                sucesfull_log("[NEW_INSCRIPTION]: novo estudante inscrito com sucesso")
                return True
                
            warning_log("[NEW_INSCRIPTION]: não foi possível efetuar cadastro do usuário no curso")
            return False
            
        except Exception as e:
             error_log(f"[NEW_INSCRIPTION]: Erro inesperado: {e}")
             try:
                 conn.rollback()
             except Exception:
                 pass
             return False
        finally:
             conn.close()
             
    @Login_Account.is_loged
    def remove_inscription(self, contentId: str) -> bool:
            check_task(f"[REMOVE_INSCRIPTION]: executando com : {contentId}")
            conn = self.dataBase()
            inscription_id = self.check_inscription(contentId)  
            if not inscription_id:
                conn.close()
                warning_log("[REMOVE_INSCRIPTION]: SEM INSCRIPTION ID")
                return False
            
            try:
                if delete_info(conn, Subs, "id", UUID(str(inscription_id))):
                    try:
                        if remove_content_inscription(contentId):
                            sucesfull_log(f"[REMOVE_INSCRIPTION]: Inscrição {inscription_id} removida com sucesso do SQL e MongoDB.")
                            self._cache.pop(f"my_courses_{self.userId}", None)
                            return True
                        
                        warning_log("[REMOVE_INSCRIPTION]: Não foi possível remover inscrição em >remove_content_inscription<")                        
                        return False
                                                
                    except Exception as mongo_err:
                        error_log("[REMOVE_INSCRIPTION]: Inscrição removida do SQL, mas falhou no MongoDB")
                        error_log(mongo_err)
                        return False
                        
                warning_log("[REMOVE_INSCRIPTION]: Não foi possível remover inscrição em >delete_info<")          
                return False
            except Exception as e:
                logger.error(f"[REMOVE_INSCRIPTION]: Erro ao remover inscrição: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                return False
            finally:
                conn.close()
    
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
            logger.info(f"Comentários obtidos para {contentId}")
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
        if not self.get_content_by_id(contentId):
            return False
            
        # Pega os dados do comentário no MongoDB para validar se o comentador é o dono
        comment_data = get_comment_by_id(contentId, commentId)
        if not comment_data:
            return False
            
        # Validação de Segurança: Garante que o usuário logado é o autor do comentário
        # (Nota: ajuste a chave 'user_id' conforme o seu modelo do MongoDB, geralmente é string ou ObjectId)
        if str(comment_data.get("user_id")) != str(self.userId):
            warning_log("[DELETE_MY_COMMENT]: Tentativa de exclusão de comentário pertencente a outro usuário")
            return False
            
        try:                                    
            if delete_comment(contentId, commentId):
                sucesfull_log("[DELETE_MY_COMMENT]: comentário deletado com sucesso")
                return True
                
            warning_log("[DELETE_MY_COMMENT]: não foi possível deletar comentário")   
            return False
            
        except Exception as E:
            error_log(f"[DELETE_MY_COMMENT]: {E}")
            return False
            
    @Login_Account.is_loged
    def get_my_comment(self, contentId):
        try:
            if not self.check_inscription(contentId):
                return False
                
            sucesfull_log("[GET_MY_COMMENTS] RETORNOU COM SUCESSO")                                
            return get_comment_by_user_id(contentId, self.userId)
            
        except Exception as E:
            error_log(f"[GET_MY_COMMENT]: {E}")
            return False
            
    @Login_Account.is_loged            
    def update_my_comment(self, contentId, rating, new_comment):
        if not self.check_inscription(contentId):
            return False
        try:          
            if update_comment_and_review(course_id=contentId, user_id=self.userId, user_name=self.userName, new_rating=rating, new_comment_text=new_comment):
                sucesfull_log("[UPDATE COMMENT] RETORNOU COM SUCESSO")
                return True
            return False
        except Exception as E:
            error_log(f"[UPDATE_MY_COMMENT]: {E}")
            return False