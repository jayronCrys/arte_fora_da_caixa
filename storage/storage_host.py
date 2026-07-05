"""
Camada de acesso ao Amazon S3 para o armazenamento de conteúdos.

Caminho sugerido no projeto: src/controller/storage/s3_content_storage.py
(lembre de criar um __init__.py vazio em src/controller/storage/ se o pacote
ainda não existir)

Estrutura de diretórios dentro do bucket:
    conteudos/{s3_uuid}/material_original.pdf
    conteudos/{s3_uuid}/banner.{ext}          (opcional — só quando o banner
                                                não é um dos padrões do app)
    conteudos/{s3_uuid}/paginas/pagina_{n}.jpg

Este módulo concentra TODAS as operações de escrita/leitura/remoção no S3
relacionadas a conteúdos. Rotas e classes de usuário (Management_User_Default,
Management_Admins etc.) devem chamar essas funções em vez de falar
diretamente com boto3 — isso evita duplicar a configuração do client e
centraliza o tratamento de erro/limpeza de arquivos órfãos em um único lugar.
"""

import os
import uuid
import logging
from io import BytesIO

import json

import boto3
from botocore.exceptions import ClientError
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

# ── Configuração do cliente ────────────────────────────────────────────────
# Credenciais e endpoint do MinIO/S3 movidos para variáveis de ambiente —
# antes estavam hardcoded ("minioadmin"/"minioadmin" e a URL local).
#   MINIO_ENDPOINT_URL   -> endpoint_url do client (ex.: http://127.0.0.1:9000)
#   MINIO_PUBLIC_URL      -> host público usado para montar as URLs de acesso
#                            às imagens/arquivos (deve ser o MESMO endpoint da
#                            API S3, não o console web do MinIO — ver nota
#                            abaixo sobre o bug de porta 9001 vs 9000)
#   AWS_ACCESS_KEY_ID     -> usuário de acesso do MinIO
#   AWS_SECRET_ACCESS_KEY -> senha/secret de acesso do MinIO
#   AWS_REGION            -> região (mantém default "sa-east-1" se ausente)
#   AWS_BUCKET_NAME       -> nome do bucket (mantém default "myminio" se ausente)
s3_client = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT_URL", "http://127.0.0.1:9000"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "sa-east-1"),
)

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "myminio")

# URL pública usada para montar os links de acesso a objetos (páginas de PDF,
# banners, fotos de perfil). Deve apontar para a API S3 do MinIO — a mesma
# porta usada em MINIO_ENDPOINT_URL — e não para o console web (que por
# padrão roda em uma porta diferente, tipicamente 9001).
PUBLIC_URL_BASE = os.getenv("MINIO_PUBLIC_URL", "http://127.0.0.1:9000")

CONTENT_PREFIX = "conteudos"
JPEG_QUALITY = 85
PROFILE_IMAGES = 'profile_imgs'


def _ensure_public_bucket_policy():
    """
    Aplica a política de leitura pública no bucket. Chamada explicitamente
    (ver bloco `if __name__ == "__main__"` ao final do arquivo) em vez de
    rodar como efeito colateral do import — antes, toda vez que este módulo
    era importado (ou seja, a cada start da aplicação), ele fazia chamadas de
    rede ao MinIO e reaplicava a política automaticamente, o que é
    desnecessário em toda inicialização e dificulta rastrear problemas de
    conexão na hora errada.
    """
    public_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"]
            }
        ]
    }
    try:
        s3_client.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(public_policy))
        logger.info(f"Bucket '{BUCKET_NAME}' configurado como público para leitura.")
    except Exception as e:
        logger.error(f"Erro ao aplicar política pública no bucket '{BUCKET_NAME}': {e}")


# ── Helpers de nomenclatura de chaves ──────────────────────────────────────
def _content_prefix(s3_uuid: str) -> str:
    return f"{CONTENT_PREFIX}/{s3_uuid}/"


def _pdf_key(s3_uuid: str) -> str:
    return f"{CONTENT_PREFIX}/{s3_uuid}/material_original.pdf"


def _page_key(s3_uuid: str, page_number: int) -> str:
    return f"{CONTENT_PREFIX}/{s3_uuid}/paginas/pagina_{page_number}.jpg"


def _banner_key(s3_uuid: str, ext: str) -> str:
    ext = (ext or "jpg").lower()
    return f"{CONTENT_PREFIX}/{s3_uuid}/banner.{ext}"


def build_pages_base_url(s3_uuid: str) -> str:
    """URL pública (não assinada) usada como prefixo das imagens de página."""
    return f"{PUBLIC_URL_BASE}/{BUCKET_NAME}/{_content_prefix(s3_uuid)}paginas/"

def _profile_image_key(usuario_id: str, ext: str) -> str:
    ext = (ext or "jpg").lower()
    return f"{PROFILE_IMAGES}/{usuario_id}/foto_perfil.{ext}"


# ── CREATE: PDF (upload + fatiamento) ──────────────────────────────────────
def create_content_storage(pdf_bytes: bytes) -> dict:
    """
    Cria um novo diretório de conteúdo no S3: sobe o PDF original e gera o
    fatiamento (uma imagem JPEG por página).

    Retorna {"s3_uuid": ..., "total_paginas": ..., "url_base_s3": ...}.
    Levanta exceção em caso de falha, tentando antes limpar o que já tiver
    subido para não deixar lixo órfão no bucket.
    """
    s3_uuid = uuid.uuid4().hex
    try:
        logger.debug(f"Iniciando upload do PDF do conteúdo {s3_uuid} para o bucket {BUCKET_NAME}")
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=_pdf_key(s3_uuid),
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        
        pages = convert_from_bytes(pdf_bytes)
        for i, page in enumerate(pages, start=1):
            buffer = BytesIO()
            page.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            buffer.seek(0)
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=_page_key(s3_uuid, i),
                Body=buffer,
                ContentType="image/jpeg",
            )

        logger.info(f"[S3_CREATE_CONTENT]: conteúdo {s3_uuid} criado com {len(pages)} páginas")
        return {
            "s3_uuid": s3_uuid,
            "total_paginas": len(pages),
            "url_base_s3": build_pages_base_url(s3_uuid),
        }

    except Exception as e:
        logger.error(f"[S3_CREATE_CONTENT]: falha ao criar storage do conteúdo {s3_uuid}: {e}")
        delete_content_storage(s3_uuid)
        raise


def replace_content_pdf(old_s3_uuid: str, pdf_bytes: bytes) -> dict:
    """
    Substitui o PDF de um conteúdo já existente. É gerado um s3_uuid NOVO
    (evita que o navegador do aluno sirva páginas antigas em cache) e o
    diretório antigo só é removido depois que o novo upload tiver sucesso.

    Retorna o mesmo formato de create_content_storage.
    """
    new_data = create_content_storage(pdf_bytes)
    if old_s3_uuid:
        if not delete_content_storage(old_s3_uuid):
            logger.warning(
                f"[S3_REPLACE_CONTENT]: novo conteúdo {new_data['s3_uuid']} criado, "
                f"mas falhou ao remover o diretório antigo {old_s3_uuid}"
            )
    return new_data


# ── CREATE / UPDATE: Banner ────────────────────────────────────────────────
def upload_content_banner(s3_uuid: str, banner_filename: str, banner_bytes: bytes) -> str:
    """
    Sobe/substitui o banner customizado de um conteúdo (put_object sobrescreve
    sozinho, então serve tanto para criar quanto para atualizar).

    Retorna a URL pública completa do banner, ou levanta exceção em caso de falha.
    """
    if not s3_uuid:
        raise ValueError("s3_uuid é obrigatório para subir um banner")

    ext = banner_filename.rsplit(".", 1)[-1].lower() if banner_filename and "." in banner_filename else "jpg"
    content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    key = _banner_key(s3_uuid, ext)

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=banner_bytes,
            ContentType=content_type,
        )
        logger.info(f"[S3_UPLOAD_BANNER]: banner do conteúdo {s3_uuid} atualizado")
        return f"{PUBLIC_URL_BASE}/{BUCKET_NAME}/{key}"
    except Exception as e:
        logger.error(f"[S3_UPLOAD_BANNER]: falha ao subir banner do conteúdo {s3_uuid}: {e}")
        raise


# ── DELETE ──────────────────────────────────────────────────────────────────
def delete_content_storage(s3_uuid: str) -> bool:
    """
    Remove TODO o diretório de um conteúdo no S3 (PDF original, páginas e
    banner customizado, se houver). Deve ser chamado sempre que um conteúdo
    for excluído do banco relacional, e também ao substituir o PDF de um
    conteúdo existente, para não deixar arquivos órfãos no bucket.
    """
    if not s3_uuid:
        return False

    try:
        objects_to_delete = []
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=_content_prefix(s3_uuid)):
            for obj in page.get("Contents", []):
                objects_to_delete.append({"Key": obj["Key"]})

        if not objects_to_delete:
            return True

        # delete_objects aceita no máximo 1000 chaves por chamada
        for i in range(0, len(objects_to_delete), 1000):
            chunk = objects_to_delete[i : i + 1000]
            s3_client.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": chunk})

        logger.info(f"[S3_DELETE_CONTENT]: {len(objects_to_delete)} objeto(s) removido(s) do conteúdo {s3_uuid}")
        return True

    except Exception as e:
        logger.error(f"[S3_DELETE_CONTENT]: falha ao remover diretório do conteúdo {s3_uuid}: {e}")
        return False


def delete_content_banner(s3_uuid: str, banner_url_or_key: str) -> bool:
    """Remove só o banner customizado de um conteúdo, mantendo PDF e páginas."""
    if not s3_uuid or not banner_url_or_key:
        return False

    key = banner_url_or_key
    if key.startswith("http://") or key.startswith("https://"):
        key = key.split(f"{BUCKET_NAME}.s3.amazonaws.com/", 1)[-1]

    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)
        return True
    except Exception as e:
        logger.error(f"[S3_DELETE_BANNER]: falha ao remover banner do conteúdo {s3_uuid}: {e}")
        return False


# ── READ: URLs assinadas (acesso controlado ao PDF original) ──────────────
def generate_pdf_download_url(s3_uuid: str, download_filename: str, expires_in: int = 60) -> str:
    """URL assinada para forçar o download do PDF original (expira rápido)."""
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": _pdf_key(s3_uuid),
                "ResponseContentDisposition": f'attachment; filename="{download_filename}.pdf"',
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        logger.error(f"[S3_PRESIGN_DOWNLOAD]: falha ao gerar URL de download do conteúdo {s3_uuid}: {e}")
        raise


def generate_pdf_view_url(s3_uuid: str, expires_in: int = 300) -> str:
    """URL assinada para abrir o PDF original embutido no navegador (visualização)."""
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": _pdf_key(s3_uuid),
                "ResponseContentType": "application/pdf",
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        logger.error(f"[S3_PRESIGN_VIEW]: falha ao gerar URL de visualização do conteúdo {s3_uuid}: {e}")
        raise

# ── USER PROFILE IMAGES: Create / Update / Delete ───────────────────────────

def upload_user_profile_image(usuario_id: str, filename: str, image_bytes: bytes) -> str:
    """
    Sobe ou substitui a imagem de perfil de um usuário. Como o put_object sobrescreve
    o arquivo caso ele já exista, essa mesma função serve para criar e editar.

    Retorna a URL pública completa da imagem, ou levanta exceção em caso de falha.
    """
    if not usuario_id:
        raise ValueError("usuario_id é obrigatório para subir uma imagem de perfil")

    # Extrai a extensão do arquivo original (padrão: jpg)
    ext = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else "jpg"
    content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    key = _profile_image_key(usuario_id, ext)

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
        logger.info(f"[S3_UPLOAD_PROFILE_IMAGE]: foto de perfil do usuário {usuario_id} atualizada")

        # Corrigido: usava porta 9001, que no MinIO é o CONSOLE WEB (interface
        # de administração), não a API S3 — portanto nunca serviria a imagem
        # de verdade. Agora usa PUBLIC_URL_BASE, a mesma base (porta 9000)
        # usada por build_pages_base_url/upload_content_banner.
        return f"{PUBLIC_URL_BASE}/{BUCKET_NAME}/{key}"

    except Exception as e:
        logger.error(f"[S3_UPLOAD_PROFILE_IMAGE]: falha ao subir foto de perfil do usuário {usuario_id}: {e}")
        raise

# ✅ CÓDIGO CORRIGIDO:
def delete_user_profile_image(usuario_id: str, profile_url_or_key: str) -> bool:
    """
    Remove a imagem de perfil de um usuário do bucket S3/MinIO.
    Deve ser chamada quando o usuário remover a foto ou excluir a conta.
    """
    if not usuario_id or not profile_url_or_key:
        print("delete_user_profile_image: usuario_id ou profile_url_or_key ausente")
        return False

    key = profile_url_or_key
    if key.startswith("http://") or key.startswith("https://"):
        # Extrai apenas o caminho relativo da URL
        prefixo = f"{PUBLIC_URL_BASE}/{BUCKET_NAME}/"
        if key.startswith(prefixo):
            key = key.replace(prefixo, "", 1)
        else:
            # Fallback genérico para outros formatos de URL
            from urllib.parse import urlparse
            parsed = urlparse(key)
            key = parsed.path.lstrip('/')
        
        print(f"Chave extraída da URL em delete_user_profile_image: {key}")
    
    print(f"Chave da imagem a ser excluída: {key}")
    
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)
        logger.info(f"[S3_DELETE_PROFILE_IMAGE]: foto de perfil do usuário {usuario_id} removida")
        return True
    except Exception as e:
        logger.error(f"[S3_DELETE_PROFILE_IMAGE]: falha ao remover foto de perfil do usuário {usuario_id}: {e}")
        return False

if __name__ == "__main__":
    # Execução manual/única para configurar o bucket: `python -m src.controller.storage.s3_content_storage`
    logging.basicConfig(level=logging.INFO)
    _ensure_public_bucket_policy()