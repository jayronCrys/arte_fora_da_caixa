import os
import logging
import dns.resolver
from pymongo import MongoClient, errors
import certifi

# Configuração do Logger local do módulo
logger = logging.getLogger("app.rating_models")

try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8']
except Exception as e:
    logger.debug(f"Não foi possível reconfigurar o DNS Resolver: {e}")

_db_instance = None

def init_mongodb():
    global _db_instance

    # Recupera a string de conexão das variáveis de ambiente (.env)
    mongo_uri = os.environ.get("MONGODB_URI")
    
    if not mongo_uri:
        logger.critical("A variável de ambiente 'MONGODB_URI' não foi definida no arquivo .env!")
        return False

    logger.info("Tentando conectar ao MongoDB via pool de conexões otimizado...")

    try:
        # Inicializa o cliente reutilizando conexões abertas (Connection Pooling)
        client = MongoClient(
            mongo_uri, 
            serverSelectionTimeoutMS=5000, 
            maxPoolSize=50,  # Limita e controla o gargalo de conexões simultâneas
            tlsCAFile=certifi.where()
        )
        db = client["arte_fora_da_caixa"]

        # Força o ping síncrono para validar conexão antes de aceitar tráfego
        client.admin.command('ping')
        
        # ── VALIDATOR: course_comments ──
        comments_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["course_id", "user_id", "user_name", "rating", "created_at", "is_moderated"],
                "properties": {
                    "course_id": { "bsonType": "string" },
                    "user_id": { "bsonType": "string" },
                    "user_name": { "bsonType": "string" },
                    "rating": { "bsonType": "int", "minimum": 1, "maximum": 5 },
                    "comment": { "bsonType": "string" },
                    "created_at": { "bsonType": "date" },
                    "is_moderated": { "bsonType": "bool" }
                }
            }
        }

        try:
            db.create_collection("course_comments", validator=comments_validator)
        except errors.CollectionInvalid:
            db.command("collMod", "course_comments", validator=comments_validator)

        # Índices essenciais para consultas rápidas sem Table Scan
        db.course_comments.create_index([("course_id", 1), ("user_id", 1)], unique=True, name="unique_user_per_course")
        db.course_comments.create_index([("course_id", 1), ("created_at", -1)], name="perf_course_comments_list")

        # ── VALIDATOR: course_stats ──
        stats_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["course_id", "last_updated"],
                "properties": {
                    "course_id": { "bsonType": "string" },
                    "total_inscriptions": {"bsonType": "int"},
                    "average_rating": { "bsonType": "double" },
                    "total_reviews": { "bsonType": "int" },
                    "last_updated": { "bsonType": "date" }
                }
            }
        }

        try:
            db.create_collection("course_stats", validator=stats_validator)
        except errors.CollectionInvalid:
            db.command("collMod", "course_stats", validator=stats_validator)

        db.course_stats.create_index([("course_id", 1)], unique=True, name="unique_course_stats")
        
        _db_instance = db
        logger.info("🚀 Conexão com o MongoDB estabelecida e coleções indexadas com sucesso.")
        return db

    except errors.ServerSelectionTimeoutError as e:
        logger.critical(f"❌ Falha crítica de timeout ao conectar ao MongoDB: {e}")
        return False

def get_course_stats_col():
    global _db_instance
    if _db_instance is None:
        init_mongodb()
    return _db_instance["course_stats"]

def get_course_comments_col():
    global _db_instance
    if _db_instance is None:
        init_mongodb()
    return _db_instance["course_comments"]
