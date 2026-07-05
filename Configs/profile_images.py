import os
from src.models.db_execute import update_info, delete_info
from src.models.database import get_session as database
from src.models.users_models.user_models import User
from storage.storage_host import delete_user_profile_image, upload_user_profile_image
import uuid
import logging

logger = logging.getLogger(__name__)

def profile_image_save(user_id, image_current_picture, new_image_name, image_bytes):
    conn = database()
    try:
        # Tenta deletar a imagem anterior (se existir)
        if image_current_picture:
            delete_success = delete_user_profile_image(user_id, image_current_picture)
            if not delete_success:
                logger.warning(f"Não foi possível deletar a imagem anterior do usuário {user_id}")
        
        # Faz upload da nova imagem
        image_path = upload_user_profile_image(user_id, new_image_name, image_bytes)
        print("CAMINHO ATUAL:" + (image_current_picture or "Nenhuma"))
        print("NOVO CAMINHO:" + image_path)
        
        # Atualiza o banco de dados
        update_success = update_info(conn, User, 'picture', image_path, 'id', user_id)
        
        if update_success:
            logger.info(f"Foto de perfil do usuário {user_id} atualizada com sucesso")
            return image_path
        else:
            logger.error(f"Falha ao atualizar registro no banco para o usuário {user_id}")
            return None
            
    except Exception as E:
        logger.error(f"Não foi possível realizar a alteração na foto de perfil do usuário {user_id}: {E}")
        return None
    finally:
        conn.close()