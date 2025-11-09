
#models/database/creator_database.py
from database import Base, engine

# Importa as tabelas (isso registra tudo no metadata da Base)
from .models.users_model.user_model import User
from .models.contents_model.content_models import Contents
from .models.relationships.inscriptions import Subs

import os

def create_db():
    Base.metadata.create_all(bind=engine)
    print("Banco criado com todas as tabelas!")

if __name__ == "__main__":
    create_db()