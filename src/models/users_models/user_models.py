# models/users_models/user_models.py
import enum
import uuid 
import logging
from sqlalchemy import Column, String, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.database import Base

# OTIMIZAÇÃO DE LOGS: logging.basicConfig(...) removido. 
# A configuração do logger raiz deve ser feita exclusivamente no ponto de entrada da aplicação (ex: main.py).
logger = logging.getLogger(__name__)

class UserCred(enum.Enum):
    ADMIN = "admin"
    PROFESSOR = "professor"
    STUDENT = "aluno"

class User(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    
    # NOTA DE PERFORMANCE: 'unique=True' já cria implicitamente um índice único na base de dados.
    email = Column(String(120), unique=True, nullable=True)
    password = Column(String(255), nullable=True)
    cred = Column(Enum(UserCred), default=UserCred.STUDENT, nullable=False)
    picture = Column(String(255))  
    
    # OTIMIZAÇÃO: Adicionado índice para acelerar filtragens e ordenações cronológicas de utilizadores
    creation_date = Column(DateTime(timezone=True), default=func.now(), index=True)

    # DICA PARA EVITAR GARGALOS (N+1 Queries): 
    # Ao carregar utilizadores em lote, lembre-se de usar 'joinedload' ou 'selectinload' na sua query 
    # para evitar que o SQLAlchemy faça uma consulta extra à base de dados para cada relacionamento acessado.
    contents = relationship("Contents", back_populates="publisher")
    subs = relationship("Subs", back_populates="student")

    def __repr__(self):
        return f"<Usuario(nome={self.name}, tipo={self.cred.value})>"
