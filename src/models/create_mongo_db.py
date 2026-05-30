import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

def init_mongo_db():
    # CORRIGIDO: Removidos os caracteres < e > de volta da senha
    mongo_uri = "mongodb+srv://Jwksjsjs:1081514Jh@starter-app.0plgyns.mongodb.net/arte_fora_da_caixa?retryWrites=true&w=majority"
    try:
        # Aumentei o timeout para 5000ms (5 segundos) para dar tempo de conectar na rede móvel/wi-fi do telemóvel
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # O comando 'ping' força o banco a responder imediatamente
        client.admin.command('ping')
        print("🔌 Conexão cohahaham o MongoDB estabelecida com sucesso!")
        
        return client["arte_fora_da_caixa"]
        
    except ConnectionFailure:
        print("❌ ERRO CRÍTICO: Não foi possível conectar ao MongoDB.")
        print("💡 Dica: Se a senha estiver certa, verifique se liberou o IP (0.0.0.0/0) no painel do MongoDB Atlas!")
        return False

