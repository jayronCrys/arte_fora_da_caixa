
from src.models.database import get_session as database
from src.models.db_execute import select_info
from src.models.db_mongo_execute import get_reviews
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User
from src.models.relationships_models.inscriptions import Subs
from sqlalchemy import func
from src.models.mongo_models import rating_models

import uuid

def analytics(content_id):
    conn = database()
    temp_list =[]
    analytics_doc = {}
    
    content = select_info(conn, Contents, "id", uuid.UUID(content_id))
    
    if isinstance(content, dict):
        
        publisher_id = content["publisher_id"]
        publisher = conn.query(User).filter_by(id=uuid.UUID(publisher_id)).first()
        
        analytics_doc["content_title"] = content["title"]
        analytics_doc["publi_by"] = publisher.name
        analytics_doc["publi_date"] = content["creation_date"]                
    
        
    reviews = get_reviews(content_id)
    
    if isinstance(reviews, dict):
        analytics_doc["total_inscriptions"] = reviews["total_inscriptions"]   
        analytics_doc["average_rating"] = reviews["average_rating"]
        analytics_doc["sums_reviews"]=reviews["sums_reviews"]
        analytics_doc["total_reviews"] = reviews["total_reviews"]
        
    inscriptions = conn.query(Subs).filter_by(content_id=uuid.UUID(content_id)).all()
    
        
    if isinstance(inscriptions, list):
               
        for inscription in inscriptions:
            inscription_date = inscription.creation_date
            temp_list.append(inscription_date)
            
        analytics_doc["inscriptions_line"] = temp_list
    
    return analytics_doc

def general_analytics(publisher_id):
    conn = database()
    
    # 1. Busca todos os conteúdos que o usuário publicou
    my_contents = conn.query(Contents).filter_by(publisher_id=uuid.UUID(publisher_id)).all()
    
    # Inicializa a estrutura do relatório geral
    general_doc = {
        "total_published_contents": len(my_contents),
        "global_inscriptions": 0,
        "global_total_reviews": 0,
        "global_average_rating": 0.0,
        "global_inscriptions_line": []
    }
    
    if not my_contents:
        print("ANALYTCS", general_doc)
        return general_doc

    total_sums_reviews = 0
    content_ids = [content.id for content in my_contents]
    
    # 2. Acumula os dados do MongoDB de cada conteúdo
    for c_id in content_ids:
        reviews = get_reviews(c_id)
        
        general_doc["global_inscriptions"] += reviews.get("total_inscriptions", 0)
        general_doc["global_total_reviews"] += reviews.get("total_reviews", 0)
        total_sums_reviews += reviews.get("sums_reviews", 0)

    # Calcular a média global combinada de todos os conteúdos
    if general_doc["global_total_reviews"] > 0:
        general_doc["global_average_rating"] = round(
            total_sums_reviews / general_doc["global_total_reviews"], 2
        )
        
    # 3. Busca a linha do tempo de inscrições combinada de todos os seus conteúdos
    # Usando o operador IN do SQLAlchemy para trazer tudo de uma vez só
    all_inscriptions = conn.query(Subs).filter(Subs.content_id.in_(content_ids)).all()
    
    # Ordena as datas para o gráfico fazer sentido cronológico
    dates = [ins.creation_date for ins in all_inscriptions if getattr(ins, "creation_date", None)]
    general_doc["global_inscriptions_line"] = sorted(dates)
    

    return general_doc




def platform_global_analytics():
    conn = database()
    
    # Inicializa o documento de retorno
    global_doc = {
        "total_active_contents": 0,
        "total_users_registered": 0,
        "platform_total_inscriptions": 0,
        "platform_total_reviews": 0,
        "platform_average_rating": 0.0,
        "growth_inscriptions_timeline": []
    }
    
    # 1. Consultas ultra rápidas no SQL (traz apenas o número, não os objetos inteiros)
    global_doc["total_active_contents"] = conn.query(func.count(Contents.id)).scalar()
    global_doc["total_users_registered"] = conn.query(func.count(User.id)).scalar()
    
    # 2. Agregação no MongoDB (Soma tudo direto no motor do banco, sem loops no Python)
    try:
        course_stats_col = rating_models.get_course_stats_col()
        
        pipeline = [
            {
                "$group": {
                    "_id": None, # Agrupa a coleção inteira em um único resultado
                    "total_inscriptions": {"$sum": "$total_inscriptions"},
                    "total_reviews": {"$sum": "$total_reviews"},
                    "sums_reviews": {"$sum": "$sums_reviews"}
                }
            }
        ]
        
        result = list(course_stats_col.aggregate(pipeline))
        
        if result:
            datas_mongo = result[0]
            global_doc["platform_total_inscriptions"] = datas_mongo.get("total_inscriptions", 0)
            global_doc["platform_total_reviews"] = datas_mongo.get("total_reviews", 0)
            
            # Calcula a média ponderada global da plataforma
            total_reviews = datas_mongo.get("total_reviews", 0)
            sums_reviews = datas_mongo.get("sums_reviews", 0)
            
            if total_reviews > 0:
                global_doc["platform_average_rating"] = round(sums_reviews / total_reviews, 2)
                
    except Exception as e:
        print(f"🚨 Erro ao agregar dados globais do MongoDB: {e}")

    # 3. Linha do tempo global de inscrições (Histórico de crescimento da plataforma)
    all_subs = conn.query(Subs.creation_date).order_by(Subs.creation_date.asc()).all()
    global_doc["growth_inscriptions_timeline"] = [sub.creation_date for sub in all_subs if sub.creation_date]
    
    return global_doc
      