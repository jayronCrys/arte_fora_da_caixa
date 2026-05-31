from src.models.contents_models import rating_models
from datetime import datetime
from bson.objectid import ObjectId  # 🌟 Adicionado para manipular os IDs do MongoDB

def new_review(course_id, review=0, new_inscription=False):
    # Busca a coleção através da função de acesso seguro
    course_stats_col = rating_models.get_course_stats_col()

    update_fields = {}

    if new_inscription:
        update_fields["total_inscriptions"] = {
            "$add": [
                {"$ifNull": ["$total_inscriptions", 0]},
                1
            ]
        }

    if int(review) > 0:
        update_fields["sums_reviews"] = {
            "$add": [
                {"$ifNull": ["$sums_reviews", 0]},
                review
            ]
        }

        update_fields["total_reviews"] = {
            "$add": [
                {"$ifNull": ["$total_reviews", 0]},
                1
            ]
        }

    update_fields["last_updated"] = datetime.utcnow()

    pipeline = [{"$set": update_fields}]

    if int(review) > 0:
        pipeline.append({
            "$set": {
                "average_rating": {
                    "$divide": [
                        "$sums_reviews",
                        "$total_reviews"
                    ]
                }
            }
        })
        
    print(f"[NEW_REVIEW]: Executando update_one com segurança...")
    course_stats_col.update_one(
        {"course_id": str(course_id)},
        pipeline,
        upsert=True
    )

def remove_content_inscription(course_id):
    """
    Abordagem direta usando $inc clássico. 
    Só decrementa se o documento contiver total_inscriptions maior que 0.
    """
    course_stats_col = rating_models.get_course_stats_col()

    print(f"[REMOVE_INSCRIPTION]: Executando $inc negativo para o curso {course_id}...")

    resultado = course_stats_col.update_one(
        {
            "course_id": str(course_id).strip(),
            "total_inscriptions": {"$gt": 0}
        },
        {
            "$inc": {"total_inscriptions": -1},
            "$set": {"last_updated": datetime.utcnow()}
        },
        upsert=False
    )

    print(f"[REMOVE_INSCRIPTION] MATCHED: {resultado.matched_count} | MODIFIED: {resultado.modified_count}")

def new_comment(course_id, user_id, user_name, rating, texto_comentario):
    course_comments_col = rating_models.get_course_comments_col()

    comentario_doc = {
        "course_id": str(course_id),
        "user_id": str(user_id),
        "user_name": user_name,
        "rating": int(rating),
        "comment": texto_comentario,
        "created_at": datetime.utcnow(),
        "is_moderated": False
    }
    
    print(f"[NEW_COMMENT]: Salvando comentário com segurança...")
    course_comments_col.update_one(
        {"course_id": str(course_id), "user_id": str(user_id)},
        {"$set": comentario_doc},
        upsert=True
    )
def get_reviews(course_id):
    stats = {
        "average_rating": 0.0,
        "total_reviews": 0,
        "total_inscriptions": 0,
        "sums_reviews": 0, # Garante que a chave sempre exista
    }
    try:
        course_stats_col = rating_models.get_course_stats_col()
        resultado = course_stats_col.find_one({"course_id": str(course_id)})
        if resultado:
            # Mescla os dados do banco por cima dos padrões de forma segura
            stats.update(resultado)
            
            # Remove o ObjectId para evitar erros caso decida transformar em JSON depois
            stats.pop("_id", None) 
            
    except Exception as e:
        print(f"🚨 O MOTIVO DO EXCEPT É: {type(e).__name__} - {e}, {type(course_id)}")
        return stats
        
    return stats


def get_comments(course_id, page=1, number_to_page=5):
    next_init = (page - 1) * number_to_page
    
    try:
        course_comments_col = rating_models.get_course_comments_col()
        cursor = course_comments_col.find({"course_id": str(course_id), "is_moderated": False}) \
                                    .sort("created_at", -1) \
                                    .skip(next_init) \
                                    .limit(number_to_page)
        
        return list(cursor)
    except Exception as e:
        print(f"🚨 Erro ao buscar comentários: {e}")
        return []

# =====================================================================
# Novos métodos solicitados baseados na estrutura existente
# =====================================================================

def delete_comment(course_id, comment_id):
    """
    Deleta permanentemente um comentário do banco de dados 
    utilizando o ID do comentário e o ID do conteúdo (garantia extra de segurança).
    """
    try:
        course_comments_col = rating_models.get_course_comments_col()
        
        print(f"[DELETE_COMMENT]: Tentando deletar comentário {comment_id} do conteúdo {course_id}...")
        
        resultado = course_comments_col.delete_one({
            "_id": ObjectId(comment_id),
            "course_id": str(course_id).strip()
        })
        
        print(f"[DELETE_COMMENT]: DELETED_COUNT: {resultado.deleted_count}")
        return resultado.deleted_count > 0
    except Exception as e:
        print(f"🚨 Erro ao deletar comentário: {e}")
        return False

def suspend_comment(course_id, comment_id):
    """
    Suspende um comentário alterando a flag 'is_moderated' para True.
    Isso faz com que ele suma automaticamente do método 'get_comments'.
    """
    try:
        course_comments_col = rating_models.get_course_comments_col()
        
        print(f"[SUSPEND_COMMENT]: Suspendendo comentário {comment_id} do conteúdo {course_id}...")
        
        resultado = course_comments_col.update_one(
            {
                "_id": ObjectId(comment_id),
                "course_id": str(course_id).strip()
            },
            {
                "$set": {
                    "is_moderated": True,
                    "suspended_at": datetime.utcnow()
                }
            }
        )
        
        print(f"[SUSPEND_COMMENT]: MATCHED: {resultado.matched_count} | MODIFIED: {resultado.modified_count}")
        return resultado.modified_count > 0
    except Exception as e:
        print(f"🚨 Erro ao suspender comentário: {e}")
        return False

def get_comment_by_id(course_id, comment_id):
    """
    Busca e retorna um comentário específico através do seu ID e do ID do conteúdo.
    Retorna o dicionário do comentário se encontrado, ou None se não existir.
    """
    try:
        course_comments_col = rating_models.get_course_comments_col()
        
        print(f"[GET_COMMENT_BY_ID]: Buscando comentário {comment_id}...")
        
        comentario = course_comments_col.find_one({
            "_id": ObjectId(comment_id),
            "course_id": str(course_id).strip()
        })
        
        if comentario:
            print(f"[GET_COMMENT_BY_ID]: Comentário encontrado com sucesso.")
            return comentario
            
        print(f"[GET_COMMENT_BY_ID]: Nenhum comentário correspondente encontrado.")
        return None
    except Exception as e:
        print(f"🚨 Erro ao buscar comentário específico: {e}")
        return None
