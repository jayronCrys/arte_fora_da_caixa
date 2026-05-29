import dns.resolver
try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8']
except Exception:
    pass

from pymongo import MongoClient, errors

# Declarar as variáveis no topo para o Flask não dar ImportError
course_stats = None
course_comments = None

def init_mongodb():
    global course_stats, course_comments

    # ── CONFIGURAÇÃO DE AMBIENTE ──
    # Mude para True se quiser testar no Atlas (Nuvem) quando estiver em casa.
    # Mude para False se estiver na Facul/Estácio (Local) para não travar o código.
    USAR_ATLAS_NUVEM = False 

    if USAR_ATLAS_NUVEM:
        print("☁️ Tentando conectar ao MongoDB Atlas (Nuvem)...")
        mongo_uri = "mongodb+srv://Jwksjsjs:1081514Jh@starter-app.0plgyns.mongodb.net/arte_fora_da_caixa?retryWrites=true&w=majority"
    else:
        print("💻 Conectando ao MongoDB Local (Ambiente de Aula)...")
        mongo_uri = "mongodb://127.0.0.1:27017"

    try:
        # Definimos timeout curto (5s) para se não achar o banco local/nuvem avisar rápido
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
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
                "required": ["course_id", "average_rating", "total_reviews", "total_students", "rating_distribution", "last_updated"],
                "properties": {
                    "course_id": { "bsonType": "string", "description": "ID único do curso" },
                    "average_rating": { "bsonType": "double", "description": "Média das notas" },
                    "total_reviews": { "bsonType": "int", "description": "Total de avaliações" },
                    "total_students": { "bsonType": "int", "description": "Total de alunos" },
                    "rating_distribution": { "bsonType": "object", "required": ["1", "2", "3", "4", "5"], "description": "Distribuição de estrelas" },
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

        # Alimenta as variáveis para uso global do resto do app
        course_stats = db["course_stats"]
        course_comments = db["course_comments"]

        print("🚀 Configuração do MongoDB concluída! Banco de dados respondendo perfeitamente.")
        return db

    except errors.ServerSelectionTimeoutError:
        print("\n❌ ERRO CRÍTICO: Não foi possível estabelecer conexão com o MongoDB.")
        if USAR_ATLAS_NUVEM:
            print("💡 Motivo: A rede da faculdade bloqueou o acesso ao Atlas na nuvem.")
            print("🛠️ Solução rápida: Vá no código e mude 'USAR_ATLAS_NUVEM = False' para usar o banco local da máquina da aula.")
        else:
            print("💡 Motivo: O serviço local do MongoDB não está rodando nesta máquina.")
            print("🛠️ Solução rápida: Certifique-se de iniciar o serviço 'MongoDB Server' (mongod) no Windows da faculdade.")
        return False

# Executa ao iniciar o app
init_mongodb()