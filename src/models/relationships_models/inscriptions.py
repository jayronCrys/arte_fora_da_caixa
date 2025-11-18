
#models/relashiontips_models/inscriptions.py
from src.models.database import Base
from src.models import * #---->chama o __init__.py
import logging
import uuid
# --------------------------------------------------
# Configuração do log
# --------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Tabela de Inscrições (ligação aluno ↔ conteúdo)
# --------------------------------------------------
class Subs(Base):
    __tablename__ = "inscricoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ------------------------------------------------
    # student_id: FK para "usuarios.id"
    # Cada linha representa uma relação entre aluno e conteúdo.
    # ------------------------------------------------
    student_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    # ------------------------------------------------
    # content_id: FK para "conteudos.id"
    # ------------------------------------------------
    content_id = Column(UUID(as_uuid=True), ForeignKey("conteudos.id"), nullable=False)
    creation_date = Column(DateTime(timezone=True), default=func.now())

    # ------------------------------------------------
    # Relacionamentos:
    # - student → usuário (auno) relacionado a esta inscrição
    # - content → conteúdo ao qual o aluno está inscrito
    # ------------------------------------------------
    student = relationship("User", back_populates="subs")
    content = relationship("Contents", back_populates="inscricoes")

    def __repr__(self):
        return f"<Inscricao(aluno_id={self.student_id}, conteudo_id={self.content_id})>"

