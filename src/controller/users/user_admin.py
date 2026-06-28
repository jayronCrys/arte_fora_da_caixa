from functools import wraps
import uuid
import logging

from src.controller.users.user_default import Management_User_Default, check_user, Create_Account
from src.models.db_execute import insert_info, select_info, delete_info, update_info
from src.models.database import get_session as database
from src.models.analytics import platform_global_analytics, analytics, general_analytics
from src.models.passwords import compare_password as compare
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User, UserCred
from src.models.db_mongo_execute import delete_comment, get_comment_by_id, suspend_comment
from src.controller.storage.s3_content_storage import (
    create_content_storage,
    replace_content_pdf,
    upload_content_banner,
    delete_content_storage,
)

logger = logging.getLogger(__name__)

class Management_Admins(Management_User_Default):
    def __init__(self, Account, database=database):
        super().__init__(Account, database)
        self.validFields = ["name", "email", "password", "cred"]
        # Removido "pdf" (a Contents não guarda mais binário) e adicionados
        # os campos da nova arquitetura de storage no S3.
        self.contentValidFields = ["desc", "title", "banner", "content_type", "s3_uuid", "total_paginas"]
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None

    # Mapeamento para evitar repetição de if/else de credenciais
    CRED_MAP = {
        "aluno": UserCred.STUDENT,
        "professor": UserCred.PROFESSOR,
        "admin": UserCred.ADMIN
    }

    def admin_required(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user and self.userRole == "admin" and self.userId:
                return func(self, *args, **kwargs)
            
            logger.info("Acesso negado: usuário não logado ou sem permissão de administrador.")
            return None
        return wrapper
    #_________________OTHER_USERS__________________________
    @admin_required
    def get_user_by_username(self, userName):
        conn = self.dataBase()
        try:
            db_task = select_info(conn, User, "name", userName)
            return db_task if db_task else None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por nome: {e}")
            return None            
        finally:
            conn.close()
            
    @admin_required
    def get_user_by_id(self, userId):
        conn = self.dataBase()
        try:
            db_task = select_info(conn, User, "id", uuid.UUID(userId))
            
            return db_task if db_task else None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por ID: {e}")
            return None            
        finally:
            conn.close()
                        
    @admin_required    
    def all_users(self):
        conn = self.dataBase()
        try:
            return conn.query(User).all()
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            return False
        finally:            
            conn.close()
        
    @admin_required
    def create_user_by_admin(self, userName, userPass, userCred="aluno"):
        
        mapped_cred = self.CRED_MAP.get(userCred)
        if not mapped_cred:
            logger.warning("Tipo de credencial inválido")
            return False
        
        conn = self.dataBase()
        checker = Create_Account(self.dataBase)
        
        if not checker.create_user_name(userName) or not checker.create_user_pass(userPass, userPass):
            conn.close()
            return False
            
        try:
            ok = insert_info(conn, User, {
                "name": checker.userName,
                "email": None,  # Não permitido e-mail para contas criadas por admin
                "password": checker.userPass,
                "picture": None,
                "cred": mapped_cred
            })
            if not ok:
                return False
                
            return select_info(conn, User, "name", userName, None)
            
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()
    @admin_required
    def update_user_by_admin(self, field, newValue,userId):
        if field not in self.validFields or not userId:
            logger.warning("Parâmetro de atualização inválido")
            return False
            
        # Corrigido: Validação por ID
        if not self.get_user_by_id(userId):
            return False
                        
        checker = Create_Account(self.dataBase)
        save_user = check_user(userId, self.dataBase, "id")
        
        if field == "name":
            if not checker.create_user_name(newValue):
                return False
            newValue = checker.userName                                            
        
        elif field == "password":
            
            if compare(newValue, save_user.get("password")):
                logger.info("Senhas idênticas, nenhuma alteração feita.")
                return False
            newValue = checker.userPass                
        
        elif field == "cred":
            newValue = self.CRED_MAP.get(newValue)
            if not newValue:
                return False

        conn = self.dataBase()
        try:
            db_task = update_info(conn, User, field, newValue, "id", uuid.UUID(userId))
            logger.info("Alteração realizada com sucesso.")
            return db_task
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário {userId}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False            
        finally:
            conn.close()
            
    @admin_required
    def delete_user_by_admin(self, userId):
        if not userId:
            return False
            
        # Corrigido: Agora valida por ID, não por nome
        if not self.get_user_by_id(userId):
            return False
            
        conn = self.dataBase()
        try:
            return delete_info(conn, User, "id", uuid.UUID(userId))
        except Exception as e:
            logger.error(f"Erro ao deletar usuário {userId}: {e}")
            return False            
        finally:
            conn.close()
                
    #____________________USERS_REVIEWS_________________________
    @admin_required
    def get_comment_by_admin(self, contentId):
        return self.get_content_comment(contentId=contentId, moderated=False) or [], self.get_content_comment(contentId=contentId, moderated=True) or []

    @admin_required        
    def suspended_comment_by_admin(self, contentId, commentId):
        # Corrigido: 'seld' alterado para 'self'
        if not self.get_content_by_id(contentId):
            return False
                        
        if not get_comment_by_id(contentId, commentId):
            return False
            
        try:   
            return bool(suspend_comment(contentId, commentId))
        except Exception as e:
            logger.error(f"Erro ao suspender comentário {commentId}: {e}")
            return False
            
    @admin_required
    def delete_comment_by_admin(self, contentId, commentId):
        # Corrigido: Adicionado 'contentId' nos parâmetros do método
        if not self.get_content_by_id(contentId):
            return False
                        
        if not get_comment_by_id(contentId, commentId):
            return False
            
        try:   
            return bool(delete_comment(contentId, commentId))
        except Exception as e:
            logger.error(f"Erro ao deletar comentário {commentId}: {e}")
            return False
    #_______________________CONTENTS_____________________
    
                  
    @admin_required
    def get_content_by_admin(self, contentId):
        # Como nenhuma lista de colunas é passada, select_info retorna todas
        # as colunas da tabela — já inclui s3_uuid e total_paginas
        # automaticamente, sem precisar listar campo a campo aqui.
        conn = self.dataBase()
        try:
            return select_info(conn, Contents, "id", uuid.UUID(contentId))
        except Exception as e:
            logger.error(f"Erro ao obter conteúdo {contentId}: {e}")
            return False
        finally:
            conn.close()    

            
    @admin_required
    def get_all_contents_by_admin(self):
        try:
            # Nota: Certifique-se de que 'get_all_contents' existe na classe pai
            return self.get_all_contents()
        except Exception as e:
            logger.error(f"Erro ao obter todos os conteúdos: {e}")
            return False
        
            
    @admin_required
    def publish_content_by_admin(self, content, authorName):
        """
        Espera um dicionário 'content' já com os metadados de storage
        calculados (s3_uuid/total_paginas/banner), por exemplo o retorno de
        upload_content_pdf_by_admin(). Apenas persiste a referência no banco
        relacional — nenhum binário é guardado aqui.
        """
        conn = self.dataBase()
        try:
            author = select_info(conn, User, "name", authorName)
            if content and author:
                author_name = author.get("name")                
                db_task = insert_info(conn, Contents, {
                    "title":         content.get("title"),
                    "desc":          content.get("desc"),
                    "banner":        content.get("banner"),
                    "content_type":  content.get("content_type"),
                    "s3_uuid":       content.get("s3_uuid"),
                    "total_paginas": content.get("total_paginas"),
                    "author":        str(author_name),
                    "publisher_id":  uuid.UUID(self.userId)
                })
                if db_task:
                    content_obj = conn.query(Contents).filter_by(
                        title=content.get("title"), 
                        publisher_id=uuid.UUID(self.userId)
                    ).first()
                    return content_obj.id if content_obj else False
                return False
        except Exception as e:
            logger.error(f"Erro ao publicar conteúdo por admin: {e}")
            return False
        finally:
            conn.close()

    @admin_required
    def upload_content_pdf_by_admin(self, pdf_bytes):
        """
        Sobe um PDF novo para o S3 (upload + fatiamento). Não toca no banco
        relacional — retorna os metadados (s3_uuid/total_paginas/url_base_s3)
        para quem chamar decidir entre publicar (insert) ou atualizar (update).
        """
        try:
            return create_content_storage(pdf_bytes)
        except Exception as e:
            logger.error(f"Erro ao subir PDF para o S3: {e}")
            return False

    @admin_required
    def replace_content_pdf_by_admin(self, contentId, pdf_bytes):
        """
        Substitui o PDF de um conteúdo já publicado: sobe o novo material em
        um diretório novo, remove o antigo do S3 e atualiza s3_uuid/
        total_paginas no banco relacional.
        """
        content = self.get_content_by_admin(contentId)
        if not content:
            return False

        old_s3_uuid = content.get("s3_uuid")

        try:
            new_data = replace_content_pdf(old_s3_uuid, pdf_bytes)
        except Exception as e:
            logger.error(f"Erro ao substituir PDF do conteúdo {contentId}: {e}")
            return False

        ok_uuid = self.update_contents_by_admin("s3_uuid", contentId, new_data["s3_uuid"])
        ok_paginas = self.update_contents_by_admin("total_paginas", contentId, new_data["total_paginas"])
        return bool(ok_uuid and ok_paginas)

    @admin_required
    def upload_content_banner_by_admin(self, contentId, banner_filename, banner_bytes):
        """
        Sobe/atualiza o banner customizado de um conteúdo e já salva a nova
        URL no banco relacional.
        """
        content = self.get_content_by_admin(contentId)
        if not content:
            return False

        s3_uuid = content.get("s3_uuid")
        if not s3_uuid:
            logger.warning(f"Conteúdo {contentId} ainda não possui s3_uuid; não é possível anexar banner.")
            return False

        try:
            banner_url = upload_content_banner(s3_uuid, banner_filename, banner_bytes)
        except Exception as e:
            logger.error(f"Erro ao subir banner do conteúdo {contentId}: {e}")
            return False

        return self.update_contents_by_admin("banner", contentId, banner_url)

    @admin_required
    def update_contents_by_admin(self, columnUpdate, contentId, newValue):
        if newValue is None or not contentId or not columnUpdate:
            return False
            
        if columnUpdate not in self.contentValidFields:
            return False

        if columnUpdate == "total_paginas" and not isinstance(newValue, int):
            return False
        
        conn = self.dataBase()
        try:                              
            contentExist = select_info(conn, Contents, "id", uuid.UUID(contentId))
            if contentExist:
                return update_info(conn, Contents, columnUpdate, newValue, "id", uuid.UUID(contentId))
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar conteúdo {contentId}: {e}")
            return False
        finally:
            conn.close()

    @admin_required
    def suspended_content_by_admin(self, contentId):
        if not self.get_content_by_id(contentId):
            return False
        # TODO: Implementar lógica de alteração do status para 'suspenso' no banco de dados.
        return True
                    
    @admin_required
    def delete_contents_by_admin(self, contentId):
        """
        Remove o conteúdo do banco relacional e, em seguida, limpa o
        diretório correspondente no S3 (PDF original, páginas e banner).
        A ordem importa: só tentamos limpar o S3 depois que a remoção do
        banco for confirmada, para nunca deixar um registro "fantasma"
        apontando para arquivos já apagados.
        """
        if not contentId:
            return False
            
        conn = self.dataBase()
        try:
            content = select_info(conn, Contents, "id", uuid.UUID(contentId))
            if not content:
                return False

            s3_uuid = content.get("s3_uuid")

            deleted = delete_info(conn, Contents, "id", uuid.UUID(contentId))
            if deleted and s3_uuid:
                if not delete_content_storage(s3_uuid):
                    logger.warning(
                        f"Conteúdo {contentId} removido do banco, mas falhou a limpeza "
                        f"do diretório S3 ({s3_uuid})."
                    )
            return deleted
        except Exception as e:
            logger.error(f"Erro ao deletar conteúdo {contentId}: {e}")
            return False
        finally:
            conn.close()
                            
    #___________________ANALYTICS________________________ 
    @admin_required
    def get_content_analytics_by_admin(self, contentId):
        # Corrigido: Nome do método corrigido de 'admim' para 'admin'
        print("<>"*10, contentId)
        if not self.get_content_by_admin(contentId):
            return False
            
        try:            
            return analytics(contentId)
        except Exception as e:
            logger.error(f"Erro ao coletar analytics do conteúdo {contentId}: {e}")
            return False
            
    @admin_required            
    def search_users_by_name(self, userName):
        
        if not userName:
            return []
            
        conn = self.dataBase()
        # 1ª Tentativa: Busca exata
        results = conn.query(User).filter_by(name=userName).all()
        
        # 2ª Tentativa: Se não achou nada na busca exata, busca por aproximação direto no banco
        if not results:
            results = conn.query(User).filter(User.name.contains(userName)).all()
        temp_list = []
        for result in results:
            temp_json = {
            "id": str(result.id),
            "name": result.name,
            "email": result.email
            }
            temp_list.append(temp_json)
                        
        return temp_list
                    
    @admin_required
    def get_professor_analytics(self, professor_name):
        try:
            professor = self.get_user_by_username(professor_name)
            print(f"[[[[PROFESSOR {professor}\n{type(professor['id'])}]]]]")
            if not professor["id"]:
                return False
            
            professor_analytic = general_analytics(professor["id"])
            return professor_analytic if professor_analytic else False
        except Exception as e:
            logger.error(f"Erro ao coletar analytics globais da plataforma: {e}")
            return False
            
    @admin_required
    def get_plataform_analytics(self):
        try:
            analytic = platform_global_analytics()
            return analytic if analytic else False
        except Exception as e:
            logger.error(f"Erro ao coletar analytics globais da plataforma: {e}")
            return False
