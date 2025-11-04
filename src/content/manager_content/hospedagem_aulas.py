from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, ForeignKey, LargeBinary,
    Enum, func, Text
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
import logging

#ORMS -> é meio que uma forma de usar um banco de dados e suas tabelas sem usar linguagem SLQ mas sim acessando como objetos nativos

# --------------------------------------------------
# Configuração do log
# --------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Base declarativa — usada como base para as classes do ORM
Base = declarative_base()


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
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=True)  # Recebe hash externo
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


# --------------------------------------------------
# Tabela de Conteúdos (PDFs, materiais, etc.)
# --------------------------------------------------
class Contents(Base):
    __tablename__ = "conteudos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
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
    # - student → usuário (aluno) relacionado a esta inscrição
    # - content → conteúdo ao qual o aluno está inscrito
    # ------------------------------------------------
    student = relationship("User", back_populates="subs")
    content = relationship("Contents", back_populates="inscricoes")

    def __repr__(self):
        return f"<Inscricao(aluno_id={self.student_id}, conteudo_id={self.content_id})>"


# --------------------------------------------------
# Função para criar o banco de dados e retornar uma sessão
# --------------------------------------------------
def create_db(uri="sqlite:///plataforma.db"):#->precisa de uma uri válida
    """
    Cria o banco de dados local e retorna uma sessão ativa.

    Aqui o SQLAlchemy cria as tabelas mapeadas pelas classes (Base.metadata.create_all)
    e prepara a engine e sessão para uso.

    Retorna:
        session (Session): objeto de sessão para executar operações ORM.
    """
    engine = create_engine(uri, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    logger.info(f"Banco criado e conectado: {uri}")
    return Session()


# --------------------------------------------------
# Exemplo de uso e populamento inicial
# --------------------------------------------------
if __name__ == "__main__":
    # Cria o banco e inicia a sessão
    session = create_db()

    # Cria usuários
    admin = User(name="Administrador", email="admin@email.com",
                 password="hash123", cred=UserCred.ADMIN)
    prof = User(name="Professor João", email="jclever@gmail.com",
                password="hash456", cred=UserCred.PROFESSOR)
    aluno = User(name="Maria", email="maria@email.com",
                 password="hash789", cred=UserCred.STUDENT)

    session.add_all([admin, prof, aluno])
    session.commit()

    # ------------------------------------------------
    # Admin posta conteúdo
    # publisher_id = admin.id será automaticamente associado via objeto
    # ------------------------------------------------
    conteudo1 = Contents(
        title="Introdução",
        desc="Material do curso.",
        pdf=b"%PDF...",  # bytes do PDF
        author="Frederixxxxo",
        publisher=admin
    )

    # ------------------------------------------------
    # Professor posta conteúdo
    # ------------------------------------------------
    conteudo2 = Contents(
        title="Aula 1",
        desc="Primeira aula do módulo.",
        pdf=b"%PDF...",
        author=prof.name,
        publisher=prof
    )

    session.add_all([conteudo1, conteudo2])
    session.commit()

    # ------------------------------------------------
    # Aluno se inscreve em um conteúdo
    # O ORM automaticamente associa os IDs corretos (student_id e content_id)
    # ------------------------------------------------
    insc = Subs(student=aluno, content=conteudo2)
    session.add(insc)
    session.commit()

    logger.info("Banco populado com dados iniciais.")