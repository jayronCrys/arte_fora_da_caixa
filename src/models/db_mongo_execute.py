import logging
from datetime import datetime
from bson.objectid import ObjectId
from src.models.mongo_models import rating_models

logger = logging.getLogger("app.db_execute")

def new_review(course_id, review=0, new_inscription=False):
    course_stats_col = rating_models.get_course_stats_col()
    update_fields = {}

    if new_inscription:
        update_fields["total_inscriptions"] = {
            "$add": [{"$ifNull": ["$total_inscriptions", 0]}, 1]
        }

    if int(review) > 0:
        update_fields["sums_reviews"] = {
            "$add": [{"$ifNull": ["$sums_reviews", 0]}, int(review)]
        }
        update_fields["total_reviews"] = {
            "$add": [{"$ifNull": ["$total_reviews", 0]}, 1]
        }

    update_fields["last_updated"] = datetime.utcnow()
    pipeline = [{"$set": update_fields}]

    if int(review) > 0:
        pipeline.append({
            "$set": {
                "average_rating": {
                    "$divide": ["$sums_reviews", "$total_reviews"]
                }
            }
        })
        
    logger.debug(f"Atualizando estatísticas de review para o curso: {course_id}")
    course_stats_col.update_one(
        {"course_id": str(course_id)},
        pipeline,
        upsert=True
    )

def remove_content_inscription(course_id):
    course_stats_col = rating_models.get_course_stats_col()
    
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
    logger.info(f"Remover inscrição do curso {course_id} | Matched: {resultado.matched_count} | Modified: {resultado.modified_count}")

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
        "sums_reviews": 0,
    }
    try:
        course_stats_col = rating_models.get_course_stats_col()
        # Otimização: Uso de projeção nativa {'_id': 0} poupa rede e processamento
        resultado = course_stats_col.find_one({"course_id": str(course_id)}, {"_id": 0})
        if resultado:
            stats.update(resultado)
    except Exception as e:
        logger.error(f"Erro ao buscar review do curso {course_id}: {e}")
        return stats
    return stats

def get_reviews_bulk(course_ids: list) -> dict:
    _default = lambda: {
        "average_rating": 0.0,
        "total_reviews": 0,
        "total_inscriptions": 0,
        "sums_reviews": 0,
    }
    if not course_ids:
        return {}
    try:
        course_stats_col = rating_models.get_course_stats_col()
        ids_str = [str(cid) for cid in course_ids]
        
        # Otimização de Rede: Projeta exclusão de _id direto na base do MongoDB
        cursor = course_stats_col.find({"course_id": {"$in": ids_str}}, {"_id": 0})
        
        result = {}
        for doc in cursor:
            cid = doc.get("course_id")
            result[cid] = doc
            
        for cid in ids_str:
            if cid not in result:
                result[cid] = _default()
        return result
    except Exception as e:
        logger.error(f"Erro em get_reviews_bulk: {e}")
        ids_str = [str(cid) for cid in course_ids]
        return {cid: _default() for cid in ids_str}

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
        logger.error(f"Erro ao buscar comentários para o curso {course_id}: {e}")
        return []

def delete_comment(course_id, comment_id):
    try:
        course_comments_col = rating_models.get_course_comments_col()
        resultado = course_comments_col.delete_one({
            "_id": ObjectId(comment_id),
            "course_id": str(course_id).strip()
        })
        return resultado.deleted_count > 0
    except Exception as e:
        logger.error(f"Erro ao deletar comentário {comment_id}: {e}")
        return False

def unhide_comment(course_id, comment_id):
    try:
        course_comments_col = rating_models.get_course_comments_col()
        resultado = course_comments_col.update_one(
            {
                "_id": ObjectId(comment_id),
                "course_id": str(course_id).strip()
            },
            {
                "$set": {
                    "is_moderated": False,
                    "suspended_at": None
                }
            }
        )
        return resultado.modified_count > 0
    except Exception as e:
        logger.error(f"Erro ao desocultar comentário {comment_id}: {e}")
        return False

def suspend_comment(course_id, comment_id):
    try:
        course_comments_col = rating_models.get_course_comments_col()
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
        return resultado.modified_count > 0
    except Exception as e:
        logger.error(f"Erro ao suspender comentário {comment_id}: {e}")
        return False

def get_comment_by_user_id(course_id, user_id):
    try:
        course_comments_col = rating_models.get_course_comments_col()
        return course_comments_col.find_one({
            "user_id": str(user_id),
            "course_id": str(course_id).strip()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar comentário do usuário {user_id}: {e}")
        return None
        
def get_comment_by_id(course_id, comment_id):
    try:
        course_comments_col = rating_models.get_course_comments_col()
        return course_comments_col.find_one({
            "_id": ObjectId(comment_id),
            "course_id": str(course_id).strip()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar comentário por ID {comment_id}: {e}")
        return None

def update_comment_and_review(course_id, user_id, user_name, new_rating, new_comment_text):
    try:
        course_comments_col = rating_models.get_course_comments_col()
        course_stats_col = rating_models.get_course_stats_col()

        course_id_str = str(course_id).strip()
        user_id_str = str(user_id).strip()
        new_rating = int(new_rating)

        # Otimização de payload: Busca apenas as chaves estritamente necessárias para o cálculo do Delta
        old_comment = course_comments_col.find_one(
            {"course_id": course_id_str, "user_id": user_id_str},
            {"rating": 1, "comment": 1}
        )

        if old_comment:
            old_rating = int(old_comment.get("rating", 0))
            if old_rating == new_rating and old_comment.get("comment") == new_comment_text:
                return True
            
            delta_sums = new_rating - old_rating
            delta_reviews = 0
        else:
            delta_sums = new_rating
            delta_reviews = 1

        comentario_doc = {
            "course_id": course_id_str,
            "user_id": user_id_str,
            "user_name": user_name,
            "rating": new_rating,
            "comment": new_comment_text,
            "created_at": datetime.utcnow(),
            "is_moderated": False
        }

        course_comments_col.update_one(
            {"course_id": course_id_str, "user_id": user_id_str},
            {"$set": comentario_doc},
            upsert=True
        )

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

        course_stats_col.update_one({"course_id": course_id_str}, stats_pipeline, upsert=True)
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar comentário e notas do curso {course_id}: {e}")
        return False
