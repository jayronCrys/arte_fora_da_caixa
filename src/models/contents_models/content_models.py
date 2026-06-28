from src.models.database import Base
from src.models import *
from sqlalchemy import Integer
import uuid
import logging


# ORMS -> é meio que uma forma de usar um banco de dados e suas tabelas sem usar linguagem SQL mas sim acessando como objetos nativos

# --------------------------------------------------
# Configuração do log
# --------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Tabela de Conteúdos
# --------------------------------------------------
# Arquitetura de armazenamento (S3):
#   conteudos/{s3_uuid}/material_original.pdf   -> PDF original (download)
#   conteudos/{s3_uuid}/banner.{ext}             -> banner customizado (se houver)
#   conteudos/{s3_uuid}/paginas/pagina_{n}.jpg    -> fatiamento do PDF, página a página
#
# O banco relacional NÃO guarda mais nenhum binário (nem PDF, nem imagem).
# Ele guarda só o identificador da "pasta" do conteúdo no S3 (s3_uuid) e um
# metadado derivado do processamento (total_paginas). A URL base das páginas
# e as URLs assinadas de download/visualização são SEMPRE construídas em
# tempo de execução pela camada de storage (src/controller/storage/
# s3_content_storage.py) e nunca persistidas — assim não correm o risco de
# ficar desatualizadas se o bucket, a região ou a forma de assinar mudarem.
#
# ATENÇÃO: essa mudança de schema (remoção de 'path', adição de 's3_uuid' e
# 'total_paginas') exige uma migração no banco já existente (Alembic ou
# ALTER TABLE manual). Linhas antigas ficarão com s3_uuid = NULL até serem
# reprocessadas/migradas para o S3.
# --------------------------------------------------
class Contents(Base):
    __tablename__ = "conteudos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    banner = Column(String(500), nullable=True)  # URL completa no S3 ou id de banner padrão do app
    content_type = Column(String(50), nullable=True)

    # ------------------------------------------------
    # s3_uuid: identifica a "pasta" do conteúdo dentro do bucket
    # (conteudos/{s3_uuid}/...). Substitui a antiga coluna "path", que
    # guardava o caminho de um único arquivo local e não fazia mais sentido
    # com o conteúdo fatiado em páginas e hospedado em nuvem.
    # ------------------------------------------------
    s3_uuid = Column(String(32), unique=True, nullable=True, index=True)

    # total_paginas: quantidade de páginas geradas a partir do fatiamento do
    # PDF. Usado pelo front para montar o flipbook/swiper sem precisar listar
    # o S3 a cada acesso.
    total_paginas = Column(Integer, nullable=True, default=0)

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
        return f"<Conteudo(titulo={self.title}, autor={self.author}, s3_uuid={self.s3_uuid})>"
