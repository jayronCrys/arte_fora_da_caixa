from pymongo import MongoClient, errors

def init_mongodb():
    # 1. Conexão com o servidor local do MongoDB
    # (Substitua pela string do MongoDB Atlas quando for para produção)
    client = MongoClient("mongodb://localhost:27017/")
    
    # Seleciona o banco de dados (se não existir, o Mongo preparará sua criação)
    db = client["arte_fora_da_caixa"]
    
    print("🔄 Inicializando banco de dados MongoDB...")

    # ── 2. CONFIGURAÇÃO DA COLEÇÃO: course_comments ──
    # Validação de esquema para garantir integridade dos dados de comentários
    comments_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["course_id", "user_id", "user_name", "rating", "created_at", "is_moderated"],
            "properties": {
                "course_id": {
                    "bsonType": "string",
                    "description": "Deve ser uma string e é obrigatório (ID do curso no SQL)"
                },
                "user_id": {
                    "bsonType": "string",
                    "description": "Deve ser uma string e é obrigatório (ID do usuário no SQL)"
                },
                "user_name": {
                    "bsonType": "string",
                    "description": "Deve ser uma string com o nome de exibição do usuário"
                },
                "rating": {
                    "bsonType": "int",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Deve ser um inteiro entre 1 e 5 estrelas"
                },
                "comment": {
                    "bsonType": "string",
                    "description": "Texto opcional do comentário escrito pelo usuário"
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "Data e hora em que a avaliação foi feita"
                },
                "is_moderated": {
                    "bsonType": "bool",
                    "description": "Define se o comentário foi ocultado por moderação"
                }
            }
        }
    }

    try:
        # Cria a coleção com a validação ativa
        db.create_collection("course_comments", validator=comments_validator)
        print("✅ Coleção 'course_comments' criada com sucesso.")
    except errors.CollectionInvalid:
        print("⚠️ Coleção 'course_comments' já existe. Atualizando regras...")
        db.command("collMod", "course_comments", validator=comments_validator)

    # Criação de Índices para Performance e Regras de Negócio
    # Índice Único composto: Impede estritamente que um usuário comente mais de uma vez no mesmo curso
    db.course_comments.create_index(
        [("course_id", 1), ("user_id", 1)], 
        unique=True, 
        name="unique_user_per_course"
    )
    # Índice de busca: Otimiza a listagem de comentários ordenados por data
    db.course_comments.create_index(
        [("course_id", 1), ("created_at", -1)], 
        name="perf_course_comments_list"
    )


    # ── 3. CONFIGURAÇÃO DA COLEÇÃO: course_stats ──
    # Validação de esquema para os metadados do curso (Média, Inscritos, etc.)
    stats_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["course_id", "average_rating", "total_reviews", "total_students", "rating_distribution", "last_updated"],
            "properties": {
                "course_id": {
                    "bsonType": "string",
                    "description": "ID único do curso associado"
                },
                "average_rating": {
                    "bsonType": "double",
                    "description": "Média aritmética das notas"
                },
                "total_reviews": {
                    "bsonType": "int",
                    "description": "Quantidade total de avaliações recebidas"
                },
                "total_students": {
                    "bsonType": "int",
                    "description": "Contador rápido de alunos inscritos"
                },
                "rating_distribution": {
                    "bsonType": "object",
                    "required": ["1", "2", "3", "4", "5"],
                    "description": "Distribuição quantitativa das estrelas de 1 a 5"
                },
                "last_updated": {
                    "bsonType": "date"
                }
            }
        }
    }

    try:
        db.create_collection("course_stats", validator=stats_validator)
        print("✅ Coleção 'course_stats' criada com sucesso.")
    except errors.CollectionInvalid:
        print("⚠️ Coleção 'course_stats' já existe. Atualizando regras...")
        db.command("collMod", "course_stats", validator=stats_validator)

    # Índice Único: Só pode existir um único documento de estatística por curso
    db.course_stats.create_index([("course_id", 1)], unique=True, name="unique_course_stats")

    print("\n🚀 Configuração do MongoDB concluída com sucesso! Pronto para integração.")

if __name__ == "__main__":
    init_mongodb()
