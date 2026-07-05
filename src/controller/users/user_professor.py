from functools import wraps
import uuid
import logging

from src.controller.users.user_default import Management_User_Default, Login_Account

from src.models.db_execute import insert_info, select_info, delete_info, update_info

from src.models.contents_models.content_models import Contents

from src.models.database import get_session as database

from src.models.db_mongo_execute import(delete_comment,
            get_comment_by_id,
            suspend_comment,
            unhide_comment
)

from src.models.analytics import analytics, general_analytics
from src.controller.storage.s3_content_storage import (
    create_content_storage,
    replace_content_pdf,
    upload_content_banner,
    delete_content_storage,
)

logger = logging.getLogger(__name__)

class Management_Professors(Management_User_Default):
    def __init__(self, account:dict, dataBase=database)->None:
        super().__init__(account, dataBase)
        self.userRole = self.user.get("cred") if isinstance(self.user, dict) else None
        # Atualizado: removido "pdf", adicionados s3_uuid e total_paginas
        self.contentValidFields = ["desc", "title", "banner", "content_type", "s3_uuid", "total_paginas"]

    def professor_required(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.isLoged and self.user and self.userRole == "professor" and self.userId:
                return func(self, *args, **kwargs)
            else:
                logger.info("Acesso negado: usuário não logado ou sem permissão de professor.")
                return None
        return wrapper

    # _______________________ CONTEÚDOS __________________________

    @professor_required
    def select_contents_by_publisher_id(self)->list:
        try:
            userId = uuid.UUID(self.userId)
            conn = self.dataBase()
            all_my_contents = conn.query(Contents).filter(Contents.publisher_id == userId).all()
            return all_my_contents
        except Exception as e:
            logger.error(f"Erro ao buscar conteúdos do professor: {e}")
            return []
        finally:
            conn.close()

    @professor_required
    def get_content_analytics(self, contentId:str)->bool|list:
        if not self.professor_get_content_by_id(contentId):
            return False
        try:
            return analytics(contentId)
        except Exception as e:
            logger.error(f"Erro ao coletar analytics do conteúdo {contentId}: {e}")
            return False

    @professor_required
    def get_my_analytics(self)->list:
        try:
            return general_analytics(self.userId)
        except Exception as e:
            logger.error(f"Erro ao coletar analytics pessoais: {e}")
            return []

    @professor_required
    def professor_get_content_by_id(self, contentId:str)->bool|dict:
        try:
            conn = self.dataBase()
            contentExist = select_info(conn, Contents, "id", uuid.UUID(contentId))
            if not contentExist:
                return False
            return contentExist if str(contentExist.get("publisher_id")) == str(self.userId) or contentExist.get("author") == self.userName else False
        except Exception as e:
            logger.error(f"Erro ao obter conteúdo {contentId}: {e}")
            return False
        finally:
            conn.close()

    @professor_required
    def delete_contents_by_id(self, contentId:str)->bool:
        """
        Remove o conteúdo do banco e se houver, apaga os arquivos correspondentes no S3.
        """
        if not contentId:
            return False

        content = self.professor_get_content_by_id(contentId)
        if not content:
            return False

        conn = self.dataBase()
        try:
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

    @professor_required
    def update_contents_by_id(self, columnUpdate: str, contentId: str, newValue: any) -> bool:
        """
        Atualiza um campo do conteúdo. Campos relacionados ao S3 (s3_uuid, total_paginas)
        são permitidos, mas normalmente serão alterados via upload/substituição de PDF.
        """
        if newValue is None or not contentId or not columnUpdate:
            return False
        if columnUpdate not in self.contentValidFields:
            return False
        if columnUpdate == "total_paginas" and not isinstance(newValue, int):
            return False

        if not self.professor_get_content_by_id(contentId):
            return False

        conn = self.dataBase()
        try:
            return update_info(conn, Contents, columnUpdate, newValue, "id", contentId)
        except Exception as e:
            logger.error(f"Erro ao atualizar conteúdo {contentId}: {e}")
            return False
        finally:
            conn.close()

    # _______________________ S3 – PDF __________________________

    @professor_required
    def upload_content_pdf_by_professor(self, pdf_bytes:bytes)->bool|dict:
        """
        Sobe um PDF novo para o S3 (upload + fatiamento).
        Retorna metadados (s3_uuid, total_paginas, url_base_s3) para uso na publicação.
        """
        try:
            return create_content_storage(pdf_bytes)
        except Exception as e:
            logger.error(f"Erro ao subir PDF para o S3: {e}")
            return False

    @professor_required
    def replace_content_pdf_by_professor(self, contentId:str, pdf_bytes:bytes)->bool:
        """
        Substitui o PDF de um conteúdo já publicado: sobe o novo material,
        remove o antigo do S3 e atualiza s3_uuid/total_paginas no banco.
        """
        content = self.professor_get_content_by_id(contentId)
        if not content:
            return False

        old_s3_uuid = content.get("s3_uuid")
        if not old_s3_uuid:
            logger.warning(f"Conteúdo {contentId} não possui s3_uuid; impossível substituir PDF.")
            return False

        try:
            new_data = replace_content_pdf(old_s3_uuid, pdf_bytes)
        except Exception as e:
            logger.error(f"Erro ao substituir PDF do conteúdo {contentId}: {e}")
            return False

        ok_uuid = self.update_contents_by_id("s3_uuid", contentId, new_data["s3_uuid"])
        ok_paginas = self.update_contents_by_id("total_paginas", contentId, new_data["total_paginas"])
        return bool(ok_uuid and ok_paginas)

    # _______________________ S3 – BANNER _______________________

    @professor_required
    def upload_content_banner_by_professor(self, contentId: str, banner_filename: str, banner_bytes: bytes)->str|bool:
        """
        Sobe/atualiza o banner customizado de um conteúdo e já salva a nova URL no banco.
        """
        content = self.professor_get_content_by_id(contentId)
        if not content:
            return False

        s3_uuid = content.get("s3_uuid")
        if not s3_uuid:
            logger.warning(f"Conteúdo {contentId} ainda não possui s3_uuid; não é possível anexar banner.")
            return False

        try:
            banner_url = upload_content_banner(s3_uuid, banner_filename, banner_bytes)
            if self.update_contents_by_id("banner", contentId, banner_url):
                return banner_url
            return False
            
        except Exception as e:
            logger.error(f"Erro ao subir banner do conteúdo {contentId}: {e}")
            return False
 

    # _______________________ PUBLICAÇÃO ________________________

    @professor_required
    def publish_content_by_professor(self, content:dict, author:str)->bool|str:
        """
        Publica um novo conteúdo. Espera um dicionário 'content' com os metadados
        do S3 (s3_uuid, total_paginas) preenchidos, além dos campos descritivos.
        """
        user_name = self.get_user_name()
        if author != user_name:
            return False

        if not content or not author:
            return False

        conn = self.dataBase()
        try:
            db_task = insert_info(conn, Contents, {
                "title":         content.get("title"),
                "desc":          content.get("desc"),
                "banner":        content.get("banner"),
                "content_type":  content.get("content_type"),
                "s3_uuid":       content.get("s3_uuid"),
                "total_paginas": content.get("total_paginas"),
                "author":        str(user_name),
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
            logger.error(f"Erro ao publicar conteúdo: {e}")
            return False
        finally:
            conn.close()

    # _______________________ COMENTÁRIOS _______________________

    @professor_required
    def suspended_comment_by_professor(self, contentId:str, commentId:str):
        
        if not get_comment_by_id(contentId, commentId):
            return False
        if not self.professor_get_content_by_id(contentId):
            return False
        try:
            return suspend_comment(contentId, commentId)
        except Exception as e:
            logger.error(f"Erro ao suspender comentário {commentId}: {e}")
            return False
            
    @professor_required
    def unhide_comment_by_professor(self, contentId:str, commentId:str)->bool:
        if not self.get_content_by_id(contentId):
            return False
        if not get_comment_by_id(contentId, commentId):
            return False
        if not self.professor_get_content_by_id(contentId):
            return False
            
        try:
            return bool(unhide_comment(contentId, commentId))
        except Exception as e:
            logger.error(f"Erro ao desocultar comentário {commentId}: {e}")
            return False

    @professor_required
    def delete_comment_by_professor(self, contentId:str, commentId:str)->bool:
        if not self.professor_get_content_by_id(contentId):
            return False
        if not get_comment_by_id(contentId, commentId):
            return False
        try:
            return bool(delete_comment(contentId, commentId))
        except Exception as e:
            logger.error(f"Erro ao deletar comentário {commentId}: {e}")
            return False

    @professor_required
    def get_comment_by_professor(self, contentId:str):
        ocult = []
        if self.professor_get_content_by_id(contentId):
            ocult = self.get_content_comment(contentId, True) or []
        all_comments = self.get_content_comment(contentId, False) or []
        return all_comments, ocult

    @professor_required
    def suspended_content_by_professor(self, contentId:str)->bool:
        # A ser implementado: alterar status do conteúdo para 'suspenso'
        if not self.get_content_by_id(contentId):
            return False
        if not self.professor_get_content_by_id(contentId):
            return False
        logger.warning("Funcionalidade de suspensão de conteúdo ainda não implementada.")
        return False