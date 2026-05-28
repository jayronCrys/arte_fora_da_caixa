
#src/models/database/__init__.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Base declarativa usada por todos os modelos
Base = declarative_base()

# Engine e fábrica de sessões
# -> alterar a URI pra a que vcs forem usar
engine = create_engine("sqlite:///__arte_.db", echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_session():
    """
    Retorna uma nova sessão. conn = get_session() e sempre finalizar com conn.close().
    """
    return SessionLocal()