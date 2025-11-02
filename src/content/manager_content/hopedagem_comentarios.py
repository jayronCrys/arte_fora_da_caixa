import logging
from pymongo import MongoClient, errors
from datetime import datetime
from bson import ObjectId
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------
# Conexão com MongoDB
# ---------------------------
def mongo_conn(uri="mongodb://localhost:27017/", banco="plataforma"):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[banco]
        comentarios_col = db["comentarios"]
        logger.info("Conexão com MongoDB bem-sucedida.")
        return comentarios_col
    except errors.ServerSelectionTimeoutError:
        logger.error("Não foi possível conectar ao MongoDB. Verifique se o serviço está rodando.")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao conectar ao MongoDB: {e}")
        return False

# ---------------------------
# Funções de comentários
# ---------------------------
def add_comment(comment_col, content_id, user_id, text, parent_id=None):
    if not comment_col:
        logger.error("Coleção não disponível. Comentário não inserido.")
        return False
    try:
        comment = {
            "conteudo_id": str(content_id),
            "usuario_id": str(user_id),
            "texto": text,
            "parent_id": ObjectId(parent_id) if parent_id else None,
            "criado_em": datetime.utcnow(),
            "editado_em": None,
            "likes": 0
        }
        comment_col.insert_one(comment)
        logger.info(f"Comentário adicionado para conteudo_id={content_id} por usuario_id={user_id}. parent_id={parent_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao inserir comentário: {e}")
        return False

# ---------------------------
# Likes
# ---------------------------
def like_comment(comment_col, comment_id, increment=1):
    if not comment_col:
        logger.error("Coleção não disponível. Like não aplicado.")
        return False
    try:
        result = comment_col.update_one(
    {"_id": ObjectId(comment_id), "likes": {"$gte": -increment}},
    {"$inc": {"likes": increment}}
)
        if result.matched_count == 0:
            logger.warning(f"Nenhum comentário encontrado com _id={comment_id}.")
            return False
        logger.info(f"Comentário _id={comment_id} teve likes modificados em {increment}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao aplicar like: {e}")
        return False

# ---------------------------
# Listagem hierárquica ordenada por likes
# ---------------------------
def list_comments(comment_col, content_id):
    if not comment_col:
        logger.error("Coleção não disponível. Nenhum comentário retornado.")
        return False
    try:
        all_comments = list(comment_col.find({"conteudo_id": str(content_id)}))
        comment_dict = {str(c["_id"]): c for c in all_comments}
        for c in all_comments:
            c["respostas"] = []

        root_comments = []
        for c in all_comments:
            pid = c.get("parent_id")
            if pid:
                pid_str = str(pid)
                if pid_str in comment_dict:
                    comment_dict[pid_str]["respostas"].append(c)
                else:
                    logger.warning(f"Comentário {c['_id']} aponta para parent_id={pid} inexistente.")
            else:
                root_comments.append(c)

        def sort_by_likes(comment_list):
            for c in comment_list:
                if c["respostas"]:
                    c["respostas"] = sort_by_likes(c["respostas"])
            return sorted(comment_list, key=lambda x: x.get("likes", 0), reverse=True)

        root_comments = sort_by_likes(root_comments)
        logger.info(f"{len(root_comments)} comentários principais retornados para conteudo_id={content_id}.")
        return root_comments
    except Exception as e:
        logger.error(f"Erro ao buscar comentários: {e}")
        return False

# ---------------------------
# Atualização
# ---------------------------
def update_comment(comment_col, comment_id, new_text):
    if not comment_col:
        logger.error("Coleção não disponível. Comentário não atualizado.")
        return False
    try:
        result = comment_col.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": {"texto": new_text, "editado_em": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            logger.warning(f"Nenhum comentário encontrado com _id={comment_id}.")
            return False
        logger.info(f"Comentário _id={comment_id} atualizado com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar comentário: {e}")
        return False

# ---------------------------
# Deleção
# ---------------------------
def delete_comment(comment_col, comment_id):
    if not comment_col:
        logger.error("Coleção não disponível. Comentário não apagado.")
        return False
    try:
        sub_comments = list(comment_col.find({"parent_id": ObjectId(comment_id)}))
        for sc in sub_comments:
            delete_comment(comment_col, sc["_id"])
        result = comment_col.delete_one({"_id": ObjectId(comment_id)})
        if result.deleted_count == 0:
            logger.warning(f"Nenhum comentário encontrado com _id={comment_id}.")
            return False
        logger.info(f"Comentário _id={comment_id} apagado com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao apagar comentário: {e}")
        return False


# Exemplo de uso
if __name__ == "__main__":
    comment_col = mongo_conn()
    if not comment_col:
        exit(1)

    content_id = uuid.uuid4()
    user_id1 = uuid.uuid4()
    user_id2 = uuid.uuid4()
    user_id3 = uuid.uuid4()

    add_comment(comment_col, content_id, user_id1, "Comentário principal!")

    main_comments = list_comments(comment_col, content_id)
    if main_comments:
        main_id = main_comments[0]["_id"]

        add_comment(comment_col, content_id, user_id2, "Subcomentário 1", parent_id=main_id)

        # Pega subcomentário recém-criado para evitar IndexError
        updated_comments = list_comments(comment_col, content_id)
        sub_id = updated_comments[0]["respostas"][0]["_id"]

        add_comment(comment_col, content_id, user_id3, "Resposta ao subcomentário", parent_id=sub_id)

        like_comment(comment_col, main_id, increment=3)
        like_comment(comment_col, sub_id, increment=5)

    import pprint
    comments_hier = list_comments(comment_col, content_id)
    pprint.pprint(comments_hier)