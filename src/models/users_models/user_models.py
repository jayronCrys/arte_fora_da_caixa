
#models/users_models/user_models.py
from src.models.database import Base
from src.models import *
import logging
import uuid 
import enum
from sqlalchemy import LargeBinary


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Enum de credenciais do usuário (papéis) --->
# São todas os tipps de crendenciais que um usuários pode possuir. Talvez adicionar uma para tipos de conteudos (ptgues, matematica, historia ...) possa ser bom.
# --------------------------------------------------
class UserCred(enum.Enum):
    ADMIN = "admin"
    PROFESSOR = "professor"
    STUDENT = "aluno"


# --------------------------------------------------
# Tabela de Usuários
# --------------------------------------------------
class User(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=True)

    password = Column(String(255), nullable=True)
    #password = Column(String(255), nullable=True)  # Recebe hash externo
    cred = Column(Enum(UserCred), default=UserCred.STUDENT, nullable=False)
    picture = Column(String(255))  # caminho/URL da foto
    creation_date = Column(DateTime(timezone=True), default=func.now())

    # ------------------------------------------------
    # Relacionamentos ORM:
    # - contents: lista de conteúdos publicados por este usuário, caso haja algum.
    # - subs: lista de inscrições que este usuário (como aluno) possui.
    # O parâmetro back_populates deve bater com o nome do campo inverso.
    # ------------------------------------------------
    contents = relationship("Contents", back_populates="publisher")
    subs = relationship("Subs", back_populates="student")

    def __repr__(self):
        return f"<Usuario(nome={self.name}, tipo={self.cred.value})>"
