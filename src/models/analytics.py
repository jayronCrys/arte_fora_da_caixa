import logging

from src.models.database import get_session as database
from src.models.db_execute import select_info
from src.models.db_mongo_execute import get_reviews, get_reviews_bulk
from src.models.contents_models.content_models import Contents
from src.models.users_models.user_models import User
from src.models.relationships_models.inscriptions import Subs
from sqlalchemy import func
from src.models.mongo_models import rating_models
import uuid

logger = logging.getLogger(__name__)


def analytics(content_id):
    # ─────────────────────────────────────────────────────────────────
    # TOGGLE: DADOS FICTÍCIOS (Descomente as linhas abaixo para ativar)
    # ─────────────────────────────────────────────────────────────────
    logger.warning(f"[ANALYTICS]: retornando dados FICTÍCIOS para o conteúdo {content_id} (toggle de mock ativo)")
    return {
    "content_title": "Arte Impressionista e Seus Segredos (Fictício)",
     "publi_by": "Prof. Vincent Mock",
    "publi_date": "2026-02-10",
    "total_inscriptions": 145,
    "average_rating": 4.8,
    "sums_reviews": 144,
    "total_reviews": 30,
    "inscriptions_line": ["2026-02-11", "2026-03-01", "2026-04-10", "2026-06-25"]
    }
    # ─────────────────────────────────────────────────────────────────

    conn = database()
    try:
        temp_list = []
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
            analytics_doc["sums_reviews"] = reviews["sums_reviews"]
            analytics_doc["total_reviews"] = reviews["total_reviews"]

        inscriptions = conn.query(Subs).filter_by(content_id=uuid.UUID(content_id)).all()
        if isinstance(inscriptions, list):
            for inscription in inscriptions:
                temp_list.append(inscription.creation_date)
            analytics_doc["inscriptions_line"] = temp_list

        return analytics_doc
    except Exception as e:
        logger.error(f"Erro ao montar analytics do conteúdo {content_id}: {e}")
        return {}
    finally:
        conn.close()


def general_analytics(publisher_id):
    # ─────────────────────────────────────────────────────────────────
    # TOGGLE: DADOS FICTÍCIOS (Descomente as linhas abaixo para ativar)
    # ─────────────────────────────────────────────────────────────────
    logger.warning(f"[GENERAL_ANALYTICS]: retornando dados FICTÍCIOS para o publisher {publisher_id} (toggle de mock ativo)")
    return {
        "total_published_contents": 6,
        "global_inscriptions": 482,
        "global_total_reviews": 95,
        "global_average_rating": 4.7,
        "global_inscriptions_line": ["2026-01-15", "2026-01-20", "2026-02-10", "2026-03-18", "2026-05-22", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-04-05", "2026-05-17", "2026-05-17", "2026-05-17", "2026-06-30"]
    }
    # ─────────────────────────────────────────────────────────────────

    conn = database()
    try:
        my_contents = conn.query(Contents).filter_by(publisher_id=uuid.UUID(publisher_id)).all()

        general_doc = {
            "total_published_contents": len(my_contents),
            "global_inscriptions"     : 0,
            "global_total_reviews"    : 0,
            "global_average_rating"   : 0.0,
            "global_inscriptions_line": []
        }

        if not my_contents:
            return general_doc

        content_ids = [content.id for content in my_contents]

        # Otimização: antes fazia 1 chamada ao MongoDB POR conteúdo do
        # professor (N+1). Agora usa get_reviews_bulk para buscar as stats
        # de todos os conteúdos em uma única chamada.
        all_stats = get_reviews_bulk(content_ids)

        total_sums_reviews = 0
        for stats in all_stats.values():
            general_doc["global_inscriptions"]  += stats.get("total_inscriptions", 0)
            general_doc["global_total_reviews"] += stats.get("total_reviews", 0)
            total_sums_reviews                  += stats.get("sums_reviews", 0)

        if general_doc["global_total_reviews"] > 0:
            general_doc["global_average_rating"] = round(
                total_sums_reviews / general_doc["global_total_reviews"], 2
            )

        all_inscriptions                        = conn.query(Subs).filter(Subs.content_id.in_(content_ids)).all()
        dates                                   = [ins.creation_date for ins in all_inscriptions if getattr(ins, "creation_date", None)]
        general_doc["global_inscriptions_line"] = sorted(dates)

        return general_doc
    except Exception as e:
        logger.error(f"Erro ao montar analytics gerais do publisher {publisher_id}: {e}")
        return {
            "total_published_contents": 0,
            "global_inscriptions"     : 0,
            "global_total_reviews"    : 0,
            "global_average_rating"   : 0.0,
            "global_inscriptions_line": []
        }
    finally:
        conn.close()


def platform_global_analytics():
    # ─────────────────────────────────────────────────────────────────
    # TOGGLE: DADOS FICTÍCIOS (Descomente as linhas abaixo para ativar)
    # ─────────────────────────────────────────────────────────────────
    logger.warning("[PLATFORM_ANALYTICS]: retornando dados FICTÍCIOS da plataforma (toggle de mock ativo)")
    return {
    "total_active_contents"        : 42,
    "total_users_registered"       : 1850,
    "platform_total_inscriptions"  : 5420,
    "platform_total_reviews"       : 1200,
    "platform_average_rating"      : 4.6,
     "growth_inscriptions_timeline": ["2026-01-01", "2026-01-10", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-02-20", "2026-04-05", "2026-05-17", "2026-05-17", "2026-05-17", "2026-06-30", "2026-06-31", "2026-06-31",
     "2026-06-31", "2026-06-31"]
     }
    # ─────────────────────────────────────────────────────────────────

    conn = database()
    try:
        global_doc = {
            "total_active_contents"        : 0,
            "total_users_registered"       : 0,
            "platform_total_inscriptions"  : 0,
            "platform_total_reviews"       : 0,
            "platform_average_rating"      : 0.0,
            "growth_inscriptions_timeline" : []
        }

        global_doc["total_active_contents"]  = conn.query(func.count(Contents.id)).scalar()
        global_doc["total_users_registered"] = conn.query(func.count(User.id)).scalar()

        try:
            course_stats_col = rating_models.get_course_stats_col()
            pipeline = [
                {
                    "$group": {
                        "_id"               : None,
                        "total_inscriptions": {"$sum": "$total_inscriptions"},
                        "total_reviews"     : {"$sum": "$total_reviews"},
                        "sums_reviews"      : {"$sum": "$sums_reviews"}
                    }
                }
            ]
            result = list(course_stats_col.aggregate(pipeline))
            if result:
                datas_mongo                               = result[0]
                global_doc["platform_total_inscriptions"] = datas_mongo.get("total_inscriptions", 0)
                global_doc["platform_total_reviews"]      = datas_mongo.get("total_reviews", 0)

                total_reviews = datas_mongo.get("total_reviews", 0)
                sums_reviews  = datas_mongo.get("sums_reviews", 0)
                if total_reviews > 0:
                    global_doc["platform_average_rating"] = round(sums_reviews / total_reviews, 2)

        except Exception as e:
            logger.error(f"Erro ao agregar dados globais do MongoDB: {e}")

        all_subs                                   = conn.query(Subs.creation_date).order_by(Subs.creation_date.asc()).all()
        global_doc["growth_inscriptions_timeline"] = [sub.creation_date for sub in all_subs if sub.creation_date]

        return global_doc
    finally:
        conn.close()