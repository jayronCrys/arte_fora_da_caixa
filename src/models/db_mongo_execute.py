from src.models.contents_models import rating_models
from datetime import datetime

def new_review(course_id, review=0, new_inscription=False):
    # 🌟 CORRIGIDO: Busca a coleção através da função de acesso seguro (Garante que não seja None)
    course_stats_col = rating_models.get_course_stats_col()

    update_fields = {}

    # Incrementa inscrições apenas se for nova inscrição
    if new_inscription:
        update_fields["total_inscriptions"] = {
            "$add": [
                {"$ifNull": ["$total_inscriptions", 0]},
                1
            ]
        }

    # Incrementa reviews apenas se review > 0
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

    # Adicionado campo obrigatório exigido pelo validador do seu schema do Mongo
    update_fields["last_updated"] = datetime.utcnow()

    pipeline = [
        {
            "$set": update_fields
        }
    ]

    # Só recalcula média se existir review
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

def new_comment(course_id, user_id, user_name, rating, texto_comentario):
    # 🌟 CORRIGIDO: Busca a coleção através da função de acesso seguro
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
    }
    try:
        # 🌟 CORRIGIDO: Busca a coleção através da função de acesso seguro
        course_stats_col = rating_models.get_course_stats_col()
        resultado = course_stats_col.find_one({"course_id": str(course_id)})
        if resultado:
            print("RESULTADO DE GET_REBIEWZ", resultado)
            stats = resultado
    except Exception as e:
        print(f"🚨 O MOTIVO DO EXCEPT É: {type(e).__name__} - {e}, {type(course_id)}")
        return stats
        
    return stats

def get_comments(course_id, page=1, number_to_page=5):
    next_init = (page - 1) * number_to_page
    
    try:
        # 🌟 CORRIGIDO: Busca a coleção através da função de acesso seguro
        course_comments_col = rating_models.get_course_comments_col()
        
        cursor = course_comments_col.find({"course_id": str(course_id), "is_moderated": False}) \
                                    .sort("created_at", -1) \
                                    .skip(next_init) \
                                    .limit(number_to_page)
        
        return list(cursor)
    except Exception as e:
        print(f"🚨 Erro ao buscar comentários: {e}")
        return []
