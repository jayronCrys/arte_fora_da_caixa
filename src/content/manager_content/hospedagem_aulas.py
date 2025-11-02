
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, ForeignKey, LargeBinary,
    Enum, func, Text
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
Base = declarative_base()

# --------------------------------------------------
# Definição de tipos de usuário
# --------------------------------------------------
class TipoUsuario(enum.Enum):
    ADMIN = "admin"
    PROFESSOR = "professor"
    ALUNO = "aluno"

#criar classe enum para os tipos de conteudos, como: portuges, matematica etc..

# --------------------------------------------------
# Usuários
# --------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=True)  # Recebe hash externo
    tipo = Column(Enum(TipoUsuario), default = TipoUsuario.ALUNO, nullable=False)
    foto_perfil = Column(String(255))  # caminho/URL da foto
    criado_em = Column(DateTime(timezone=True), default=func.now())

    # Relacionamentos
    conteudos = relationship("Conteudo", back_populates="autor_publicador")
    inscricoes = relationship("Inscricao", back_populates="aluno")

    def __repr__(self):
        return f"<Usuario(nome={self.nome}, tipo={self.tipo.value})>"

# ------------------------------------------------
# Conteúdos (PDFs enviados)
# ------------------------------------------------
class Conteudo(Base):
    __tablename__ = "conteudos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    arquivo_pdf = Column(LargeBinary, nullable=False)  # binário do PDF
    nome_autor_publico = Column(String(100), nullable=False)  # nome exibido no site
    autor_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=func.now())

    autor_publicador = relationship("Usuario", back_populates="conteudos")
    inscricoes = relationship("Inscricao", back_populates="conteudo")

    def __repr__(self):
        return f"<Conteudo(titulo={self.titulo}, autor={self.nome_autor_publico})>"

# --------------------------------------------------
# Inscrições (ligação aluno ↔ conteúdo)
# --------------------------------------------------
class Inscricao(Base):
    __tablename__ = "inscricoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aluno_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    conteudo_id = Column(UUID(as_uuid=True), ForeignKey("conteudos.id"), nullable=False)
    data_inscricao = Column(DateTime(timezone=True), default=func.now())
    #status = Column(String(20), default="ativa")
    #talvez esse status, seja interwssante, ir mordixiando: em andaaaamnwto, finalizado, pausado etc...
    aluno = relationship("Usuario", back_populates="inscricoes")
    conteudo = relationship("Conteudo", back_populates="inscricoes")

    def __repr__(self):
        return f"<Inscricao(aluno_id={self.aluno_id}, conteudo_id={self.conteudo_id})>"

# ------------------------------------------------
# Configuração do banco
# -----------------------------------------------
def criar_banco(uri="sqlite:///plataforma.db"):
    """
    Cria o banco de dados local e retorna uma sessão ativa.
    """
    engine = create_engine(uri, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    logger.info(f"Banco criado e conectado: {uri}")
    return Session()


# ------------------------------------------------
# Exemplo de uso
# ------------------------------------------------
if __name__ == "__main__":
    session = criar_banco()

    # Cria usuários
    admin = Usuario(nome="Administrador", email="admin@email.com",
                    senha_hash="hash123", tipo=TipoUsuario.ADMIN)
    prof = Usuario(nome="Professor João", email="jclever@gmail.com",
                   senha_hash="hash456", tipo=TipoUsuario.PROFESSOR)
    aluno = Usuario(nome="Maria", email="maria@email.com",
                    senha_hash="hash789", tipo=TipoUsuario.ALUNO)

    session.add_all([admin, prof, aluno])
    session.commit()

    # Admin posta conteúdo (pode alterar nome do autor público)
    conteudo1 = Conteudo(
        titulo="Introdução",
        descricao="Material do curso.",
        arquivo_pdf=b"%PDF...",  # bytes do PDF
        nome_autor_publico="Frederixxxxo",
        autor_publicador=admin
    )

    # Professor posta conteúdo (nome público = nome dele)
    conteudo2 = Conteudo(
        titulo="Aula 1",
        descricao="Primeira aula do módulo.",
        arquivo_pdf=b"%PDF...",
        nome_autor_publico=prof.nome,
        autor_publicador=prof
    )

    session.add_all([conteudo1, conteudo2])
    session.commit()

    # Aluno se inscreve
    insc = Inscricao(aluno=aluno, conteudo=conteudo2)
    session.add(insc)
    session.commit()

    logger.info("Banco populado com dados iniciais.")