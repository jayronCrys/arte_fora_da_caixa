# db_execute.py
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
import logging
from typing import Union, List, Type
from sqlalchemy.orm import DeclarativeMeta

# Mantive tuas mensagens de logging; só deixei consistentes
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ========================================
# Funções CRUD para SQLAlchemy
#========================================
def insert_info(session: Session, model: Type[DeclarativeMeta], data: dict) -> bool:
    """
    Insere um novo registro no banco.
    Session -> sessão ativa de um banco conectado.
    Model -> classe do modelo SQLAlchemy.
    Data -> dicionário com as colunas e valores.
    """
    try:
        novo_registro = model(**data)
        session.add(novo_registro)
        session.commit()
        logger.info(f"Registro inserido com sucesso em {model.__tablename__}")
        return True
    except Exception as e:
        # desfaz alterações pendentes
        try:
            session.rollback()
        except Exception:
            pass
        logger.error(f"Erro ao inserir informação em {getattr(model, '__tablename__', model)}: {e}")
        return False


def select_info(session: Session, model: Type[DeclarativeMeta],
                columnReference: str, valueReference: Union[str, int],
                items_to_select: Union[List[str], None] = None) -> Union[bool, dict]:
    """
    Seleciona um registro com DeclarativeMeta em uma coluna e valor.
    Retorna um dicionário com os campos e valores.
    """
    try:
        stmt = select(model).where(getattr(model, columnReference) == valueReference)
        result = session.execute(stmt).scalars().first()

        if not result:
            logger.warning(f"Nenhum resultado encontrado para {columnReference}={valueReference}")
            return False

        # Caso o usuário especifique colunas específicas
        if items_to_select:
            data = {col: getattr(result, col) for col in items_to_select}
        else:
            # Retorna todas as colunas do modelo como dicionário
            data = {
                column.name: getattr(result, column.name)
                for column in model.__table__.columns
            }

        return data

    except Exception as e:
        logger.error(f"Erro ao selecionar dados: {e}")
        return False


def update_info(session: Session, model: Type[DeclarativeMeta],
                columnUpdate: str, newValue: Union[str, int, float],
                columnReference: str, valueReference: Union[str, int]) -> bool:
    """
    Atualiza um campo específico.
    """
    try:
        stmt = (
            update(model)
            .where(getattr(model, columnReference) == valueReference)
            .values({columnUpdate: newValue})
        )
        session.execute(stmt)
        session.commit()
        logger.info(f"Registro atualizado em {getattr(model, '__tablename__', model)}")
        return True
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        logger.error(f"Erro ao atualizar: {e}")
        return False


def delete_info(session: Session, model: Type[DeclarativeMeta],
                columnReference: str, valueReference: Union[str, int]) -> bool:
    """
    Deleta um registro do banco.
    """
    try:
        stmt = delete(model).where(getattr(model, columnReference) == valueReference)
        session.execute(stmt)
        session.commit()
        logger.info(f"Registro deletado de {getattr(model, '__tablename__', model)}")
        return True
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        logger.error(f"Erro ao deletar: {e}")
        return False