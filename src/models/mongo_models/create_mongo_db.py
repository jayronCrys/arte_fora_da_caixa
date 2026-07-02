import os
import logging
import dns.resolver
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger("app.create_db_migration")

try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8']
except Exception:
    pass

def init_mongo_db():
    mongo_uri = os.environ.get("MONGODB_URI")
    
    if not mongo_uri:
        logger.critical("[MIGRATION] Variável 'MONGODB_URI' ausente no ambiente!")
        return False
        
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("🔌 Conexão de migração estabelecida com o MongoDB Atlas com sucesso!")
        return client["arte_fora_da_caixa"]
        
    except ConnectionFailure as e:
        logger.error(f"❌ Erro crítico ao conectar na rotina de migração: {e}")
        return False
