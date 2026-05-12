
#models/contents_models/content_models.py
from src.models.database import Base
from src.models import *
import uuid
import logging


#ORMS -> é meio que uma forma de usar um banco de dados e suas tabelas sem usar linguagem SLQ mas sim acessando como objetos nativos

# --------------------------------------------------
# Configuração do log
# --------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Tabela de Conteúdos
# --------------------------------------------------
class Contents(Base):
    __tablename__ = "conteudos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    banner = Column(LargeBinary, nullable=True)   # imagem do banner em binário (pode ser None)
    content_type = Column(String(50), nullable=True)
    pdf = Column(LargeBinary, nullable=False)  # arquivo PDF em binário
    author = Column(String(100), nullable=False)  # nome público do autor
    # ------------------------------------------------
    # publisher_id é uma chave estrangeira que aponta para "usuarios.id" que corresponde á parâmetro de id da tabela usuarios
    # Isso cria o vínculo entre um conteúdo e o usuário que o publicou.
    # ------------------------------------------------
    publisher_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    creation_date = Column(DateTime(timezone=True), default=func.now())

    # ------------------------------------------------
    # publisher: permite acessar o objeto User associado ao conteúdo.
    # Exemplo: conteudo.publisher.name retorna o nome do publicador.
    # ------------------------------------------------
    publisher = relationship("User", back_populates="contents")

    # ------------------------------------------------
    # inscricoes: lista de alunos inscritos neste conteúdo.
    # Cada inscrição (Subs) tem o content_id apontando para este conteúdo.
    # ------------------------------------------------
    inscricoes = relationship("Subs", back_populates="content")

    def __repr__(self):
        return f"<Conteudo(titulo={self.title}, autor={self.author})>"
