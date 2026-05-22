from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
import logging
from typing import Union, List, Type
from sqlalchemy.orm import DeclarativeMeta
import enum
import uuid
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def insert_info(session: Session, model: Type[DeclarativeMeta], data: dict) -> bool:
    try:
        novo_registro = model(**data)
        session.add(novo_registro)
        session.commit()
        logger.info(f"Registro inserido com sucesso em {model.__tablename__}")
        return True

    except Exception as e:
        try:
            session.rollback()
        except:
            pass
        logger.error(f"Erro ao inserir: {e}")
        return False



def select_info(
    session: Session,
    model: Type[DeclarativeMeta],
    columnReference: Union[List[str], str],
    valueReference: Union[str, int, List[Union[str, int]]],
    items_to_select: Optional[List[str]] = None
) -> Union[bool, dict]:
    """
    Seleciona um registro da tabela.

    - Se columnReference for str, usa condição simples: coluna = valor.
    - Se columnReference for list, valueReference deve ser uma lista de mesmo
      tamanho e monta um AND entre todas as condições.

    Retorna um dict com as colunas solicitadas ou False.
    """
    try:
        # Monta a cláusula WHERE conforme o tipo de columnReference
        if isinstance(columnReference, list):
            if not isinstance(valueReference, list) or len(columnReference) != len(valueReference):
                raise ValueError(
                    "Para columnReference em lista, valueReference deve ser uma lista de mesmo tamanho."
                )
            conditions = []
            for col_name, val in zip(columnReference, valueReference):
                conditions.append(getattr(model, col_name) == val)
            where_clause = and_(*conditions)
        else:
            # Caso string única
            where_clause = getattr(model, columnReference) == valueReference

        # Executa a consulta
        stmt = select(model).where(where_clause)
        result = session.execute(stmt).scalars().first()

        if not result:
            return False

        # Define quais colunas retornar
        cols = items_to_select or [col.name for col in model.__table__.columns]
        data = {}

        for col in cols:
            value = getattr(result, col)
            if isinstance(value, enum.Enum):
                value = value.value
            elif isinstance(value, uuid.UUID):
                value = str(value)
            data[col] = value

        return data

    except Exception as e:
        logger.error(f"Erro ao selecionar: {e}")
        return False
def update_info(session: Session, model: Type[DeclarativeMeta],
                columnUpdate: str, newValue: Union[str, int, float],
                columnReference: str, valueReference: Union[str, int]) -> bool:

    try:
        logger.info(
            "update_info: model=%s columnUpdate=%s columnReference=%s valueReference=%r",
            getattr(model, '__tablename__', str(model)),
            columnUpdate,
            columnReference,
            valueReference,
        )

       
        if isinstance(valueReference, dict) and "id" in valueReference:
            valueReference = valueReference["id"]

        if valueReference is None or (isinstance(valueReference, str) and valueReference.strip() == ""):
            raise ValueError("valueReference vazio")

        
        col = getattr(model, columnReference)
        col_type = getattr(col, "type", None)

        if isinstance(col_type, PG_UUID):
            if isinstance(valueReference, str):
                valueReference = UUID(valueReference)
       
        stmt = (
            update(model)
            .where(col == valueReference)
            .values({columnUpdate: newValue})
        )

        session.execute(stmt)
        session.commit()

        logger.info(f"Registro atualizado em {model.__tablename__}")
        return True

    except Exception as e:
        try:
            session.rollback()
        except:
            pass

        logger.error(f"Erro ao atualizar: {e}")
        return False



def delete_info(session: Session, model: Type[DeclarativeMeta],
                columnReference: str, valueReference: Union[str, int]) -> bool:

    try:
        stmt = delete(model).where(getattr(model, columnReference) == valueReference)
        session.execute(stmt)
        session.commit()
        logger.info(f"Registro deletado de {model.__tablename__}")
        return True

    except Exception as e:
        try:
            session.rollback()
        except:
            pass

        logger.error(f"Erro ao deletar: {e}")
        return False