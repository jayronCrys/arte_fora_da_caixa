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


def get_comments(course_id, page=1, number_to_page=5, moderated=True):
    next_init = (page - 1) * number_to_page
    
    try:
        course_comments_col = rating_models.get_course_comments_col()
        cursor = course_comments_col.find({"course_id": str(course_id), "is_moderated": moderated}) \
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

def get_comment_by_user_id(course_id, user_id):
    """
    Busca e retorna um comentário específico através do seu ID e do ID do conteúdo.
    Retorna o dicionário do comentário se encontrado, ou None se não existir.
    """
    try:
        course_comments_col = rating_models.get_course_comments_col()
        
        print(f"[GET_COMMENT_BY_ID]: Buscando comentário por get_cpmment_by_user_id {user_id}...")
        
        comentario = course_comments_col.find_one({
            "user_id": str(user_id),
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
        
def get_comment_by_id(course_id, comment_id):
    """
    Busca e retorna um comentário específico através do seu ID e do ID do conteúdo.
    Retorna o dicionário do comentário se encontrado, ou None se não existir.
    """
    try:
        course_comments_col = rating_models.get_course_comments_col()
        
        print(f"[GET_COMMENT_BY_ID]: Buscando comentário por get_comment_by_id {type(course_id)}...")
        
        comentario = course_comments_col.find_one({
            "_id": ObjectId(comment_id),  # <--- Aqui usa ObjectId
            "course_id": str(course_id).strip()
        })
        
        if comentario:
            print(f"[GET_COMMENT_BY_ID]: Comentário encontrado com sucesso.")
            print(comentario)
            return comentario
        print(comentario)            
        print(f"[GET_COMMENT_BY_ID]: Nenhum comentário correspondente encontrado.")
        return None
    except Exception as e:
        print(f"🚨 Erro ao buscar comentário específico: {e}")
        return None
        

def update_comment_and_review(course_id, user_id, user_name, new_rating, new_comment_text):
    """
    Atualiza obrigatoriamente o comentário e a nota de um usuário.
    Subtrai as estrelas antigas do total, adiciona as novas e recalcula a média global.
    """
    print("ENYRO NA DEF DE ATTS")
    try:
        course_comments_col = rating_models.get_course_comments_col()
        course_stats_col = rating_models.get_course_stats_col()

        course_id_str = str(course_id).strip()
        user_id_str = str(user_id).strip()
        new_rating = int(new_rating)

        # 1. Busca o comentário antigo para saber a nota anterior
        old_comment = course_comments_col.find_one({
            "course_id": course_id_str,
            "user_id": user_id_str
        })

        if old_comment:
            old_rating = int(old_comment.get("rating", 0))
            
            # Se nada mudou, cancela a operação para poupar processamento
            if old_rating == new_rating and old_comment.get("comment") == new_comment_text:
                print("[UPDATE_REVIEW]: Nenhuma alteração detectada no comentário ou nota.")
                return True
            
            # Diferença que será aplicada na soma global (Ex: Nota mudou de 3 para 5 -> Delta = +2)
            # (Ex: Nota mudou de 5 para 2 -> Delta = -3)
            delta_sums = new_rating - old_rating
            delta_reviews = 0  # O número total de avaliações não muda, já que é uma atualização
        else:
            # Fallback de segurança: se o comentário não existia por algum motivo, trata como novo
            delta_sums = new_rating
            delta_reviews = 1

        # 2. Atualiza o documento do comentário do usuário
        comentario_doc = {
            "course_id": course_id_str,
            "user_id": user_id_str,
            "user_name": user_name,
            "rating": new_rating,
            "comment": new_comment_text,
            "created_at": datetime.utcnow(),
            "is_moderated": False  # Edições resetam a moderação para aprovação padrão
        }

        course_comments_col.update_one(
            {"course_id": course_id_str, "user_id": user_id_str},
            {"$set": comentario_doc},
            upsert=True
        )

        # 3. Executa o pipeline para atualizar a soma de notas e recalcular a média global
        stats_pipeline = [
            {
                "$set": {
                    "sums_reviews": {
                        "$add": [{"$ifNull": ["$sums_reviews", 0]}, delta_sums]
                    },
                    "total_reviews": {
                        "$add": [{"$ifNull": ["$total_reviews", 0]}, delta_reviews]
                    },
                    "last_updated": datetime.utcnow()
                }
            },
            {
                "$set": {
                    "average_rating": {
                        "$cond": [
                            {"$gt": ["$total_reviews", 0]},
                            {"$divide": ["$sums_reviews", "$total_reviews"]},
                            0.0
                        ]
                    }
                }
            }
        ]

        print(f"[UPDATE_REVIEW]: Recalculando estatísticas do curso {course_id_str} (Delta: {delta_sums})...")
        course_stats_col.update_one(
            {"course_id": course_id_str},
            stats_pipeline,
            upsert=True
        )

        return True

    except Exception as e:
        print(f"🚨 Erro ao atualizar comentário e notas: {e}")
        return False
