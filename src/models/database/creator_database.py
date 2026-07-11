
#models/database/creator_database.py
from src.models.database import Base, engine

# Importa as tabelas
from src.models.users_models.user_models import User
from src.models.contents_models.content_models import Contents
from src.models.relationships_models.inscriptions import Subs

def create_db():
    Base.metadata.create_all(bind=engine)
    print("Banco criado com todas as tabelas!")

if __name__ == "__main__":
    create_db()