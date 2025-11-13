
#models/contents_models/content_models.py
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
# Exemplo de uso e populamento inicial
# --------------------------------------------------
if __name__ == "__main__":
    # Cria o banco e inicia a sessão
    session = creator_database.create_db()

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