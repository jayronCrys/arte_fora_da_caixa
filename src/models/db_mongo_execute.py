from src.models.content_models.rating_models import course_stats, course_comments
from datetime import datetime



def new_inscription(course_id):
    # O 'upsert=True' cria o documento do curso caso ele ainda não exista no Mongo
    course_stats.update_one(
        {"course_id": str(course_id)},
        {
            "$inc": {"total_students": 1},
            "$setOnInsert": {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            },
            "$set": {"last_updated": datetime.utcnow()}
        },
        upsert=True
    )
    
from db_mongo import comments_col
from datetime import datetime

def new_comment(course_id, user_id, user_name, rating, texto_comentario):
    comentario_doc = {
        "course_id": str(course_id),
        "user_id": str(user_id),
        "user_name": user_name,
        "rating": int(rating),
        "comment": texto_comentario,
        "created_at": datetime.utcnow(),
        "is_moderated": False
    }
    
    # Atualiza se existir (mesmo curso + mesmo usuário), senão insere um novo
    course_comments.update_one(
        {"course_id": str(course_id), "user_id": str(user_id)},
        {"$set": comentario_doc},
        upsert=True
    )



def get_rating(course_id):
    # Busca um único documento que dê Match com o ID do curso
    stats = course_stats.find_one({"course_id": str(course_id)})
    
    if not stats:
        # Retorno padrão caso o curso nunca tenha tido interações ainda
        return {
            "average_rating": 0.0,
            "total_reviews": 0,
            "total_students": 0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        }
        
    return stats
    
    
    
    

def get_comments(course_id, page=1, number_to_page=5):
    # Quantos comentários pular com base na página atual
    next_init = (page - 1) * number_to_page
    
    # Executa a busca filtrando apenas os que não foram ocultados pela moderação
    cursor = course_comments.find({"course_id": str(course_id), "is_moderated": False}) \
                         .sort("created_at", -1) \
                         .skip(next_init) \
                         .limit(number_to_page)
    
    # Transforma o cursor do Mongo em uma lista comum do Python
    comments = list(cursor)
    
    return comments
    
