# models/relashiontips_models/inscriptions.py
import uuid
import logging
from sqlalchemy import Column, DateTime, ForeignKey, Boolean, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.database import Base

# OTIMIZAÇÃO DE LOGS: logging.basicConfig(...) removido para respeitar o fluxo global de produção.
logger = logging.getLogger(__name__)

class Subs(Base):
    __tablename__ = "inscricoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # OTIMIZAÇÃO CRÍTICA: Adicionado index=True para evitar Table Scan ao procurar inscrições de um aluno
    student_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    
    # OTIMIZAÇÃO CRÍTICA: Adicionado index=True para consultas rápidas de métricas e listagem de alunos por curso
    content_id = Column(UUID(as_uuid=True), ForeignKey("conteudos.id"), nullable=False, index=True)
    
    creation_date = Column(DateTime(timezone=True), default=func.now())
    is_favorite = Column(Boolean, default=False)

    student = relationship("User", back_populates="subs")
    content = relationship("Contents", back_populates="inscricoes")

    # OTIMIZAÇÃO E SEGURANÇA ECONÓMICA: Garante unicidade e otimiza a velocidade de validação de duplicados
    __table_args__ = (
        UniqueConstraint('student_id', 'content_id', name='uq_student_content_unique'),
    )

    def __repr__(self):
        return f"<Inscricao(aluno_id={self.student_id}, conteudo_id={self.content_id})>"
