import dns.resolver
try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8']
except Exception:
    pass

from pymongo import MongoClient, errors

# Mantidos como fallback, mas o acesso será feito via funções abaixo
_db_instance = None

def init_mongodb():
    global _db_instance

    # ── CONFIGURAÇÃO DE AMBIENTE ──
    USAR_ATLAS_NUVEM =True

    if USAR_ATLAS_NUVEM:
        print("☁️ Tentando conectar ao MongoDB Atlas (Nuvem)...")
        mongo_uri = "mongodb+srv://Jwksjsjs:1081514Jh@starter-app.0plgyns.mongodb.net/arte_fora_da_caixa?retryWrites=true&w=majority"
    else:
        print("💻 Conectando ao MongoDB Local (Ambiente de Aula)...")
        mongo_uri = "mongodb://127.0.0.1:27017"

    import certifi # 🌟 Adicione no topo do arquivo

# ... dentro de init_mongodb() ...
    try:
        # 🌟 Adicionado o tlsCAFile para o Termux não rejeitar o SSL do Atlas
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
        db = client["arte_fora_da_caixa"]

        
        # Testa a conexão imediatamente de forma síncrona
        client.admin.command('ping')
        
        # ── CONFIGURAÇÃO DA COLEÇÃO: course_comments ──
        comments_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["course_id", "user_id", "user_name", "rating", "created_at", "is_moderated"],
                "properties": {
                    "course_id": { "bsonType": "string", "description": "ID do curso no SQL" },
                    "user_id": { "bsonType": "string", "description": "ID do usuário no SQL" },
                    "user_name": { "bsonType": "string", "description": "Nome do usuário" },
                    "rating": { "bsonType": "int", "minimum": 1, "maximum": 5, "description": "Inteiro entre 1 e 5 estrelas" },
                    "comment": { "bsonType": "string", "description": "Texto do comentário" },
                    "created_at": { "bsonType": "date", "description": "Data da avaliação" },
                    "is_moderated": { "bsonType": "bool", "description": "Status de moderação" }
                }
            }
        }

        try:
            db.create_collection("course_comments", validator=comments_validator)
            print("✅ Coleção 'course_comments' estruturada com sucesso.")
        except errors.CollectionInvalid:
            db.command("collMod", "course_comments", validator=comments_validator)

        db.course_comments.create_index([("course_id", 1), ("user_id", 1)], unique=True, name="unique_user_per_course")
        db.course_comments.create_index([("course_id", 1), ("created_at", -1)], name="perf_course_comments_list")

        # ── CONFIGURAÇÃO DA COLEÇÃO: course_stats ──
        stats_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                # 🌟 CONFIGURAÇÃO OPCIONAL: Apenas course_id e last_updated são estritamente obrigatórios
                "required": ["course_id", "last_updated"],
                "properties": {
                    "course_id": { "bsonType": "string", "description": "ID único do curso" },
                    "total_inscriptions": {"bsonType": "int","description":"Total de alunos matriculados no curso"},
                    "average_rating": { "bsonType": "double", "description": "Média das notas" },
                    "total_reviews": { "bsonType": "int", "description": "Total de avaliações" },
                    "last_updated": { "bsonType": "date" }
                }
            }
        }

        try:
            db.create_collection("course_stats", validator=stats_validator)
            print("✅ Coleção 'course_stats' estruturada com sucesso.")
        except errors.CollectionInvalid:
            db.command("collMod", "course_stats", validator=stats_validator)

        db.course_stats.create_index([("course_id", 1)], unique=True, name="unique_course_stats")
        
        # Armazena a instância conectada globalmente dentro deste arquivo
        _db_instance = db

        print("🚀 Configuração do MongoDB concluída! Banco de dados respondendo perfeitamente.")
        return db

    except errors.ServerSelectionTimeoutError:
        print("\n❌ ERRO CRÍTICO: Não foi possível estabelecer conexão com o MongoDB.")
        return False


# ── 🌟 FUNÇÕES DE ACESSO SEGURO (ANTI-NONETYPE) ──

def get_course_stats_col():
    """Retorna a coleção course_stats de forma segura, garantindo a conexão"""
    global _db_instance
    if _db_instance is None:
        init_mongodb()
    return _db_instance["course_stats"]

def get_course_comments_col():
    """Retorna a coleção course_comments de forma segura, garantindo a conexão"""
    global _db_instance
    if _db_instance is None:
        init_mongodb()
    return _db_instance["course_comments"]
