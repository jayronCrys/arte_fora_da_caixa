from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session
import logging
from typing import Union, List, Type
from sqlalchemy.orm import DeclarativeMeta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ========================================
# Funções CRUD para SQLAlchemy
#========================================
def insert_info(session: Session, model: Type[Base], data: dict) -> bool:
    """
    Insere um novo registro no banco.
    Session -> sessão ativa de um banco conectado.
    Model -> classe do modelo SQLAlchemy.
    Data -> dicionário com as colunas e valores.
    Podem ser adicionados em uma só chamada todos os campos necessários.
    """
    try:
        novo_registro = model(**data)
        session.add(novo_registro)
        session.commit()
        logger.info(f"Registro inserido com sucesso em {model.__tablename__}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao inserir informação em {model.__tablename__}: {e}")
        return False

def select_info(session: Session, model: Type[Base],
                columnReference: str, valueReference: Union[str, int],
                items_to_select: Union[List[str], None] = None) -> Union[bool, tuple]:
    """
    Seleciona um registro com base em uma coluna e valor.
    Session -> referência a um banco conectado, onde as informaçãona serem modificadas estão contidas.
    Model -> tabela de refência para a alteração das informaçãoes.
    ColummReference -> coluna que representa a entidade que será modificada.
    valueReference -> valor de busca usado para identificar a entidade.
    items_to_select: lista de colunas a selecionar ou None para todasAtualiza um campo específico.
    """
    try:
        stmt = select(model).where(getattr(model, columnReference) == valueReference)
        result = session.execute(stmt).scalars().first()

        if not result:
            logger.warning(f"Nenhum resultado encontrado para {collumnReference}={valueReference}")
            return False

        if items_to_select:
            data = tuple(getattr(result, col) for col in items_to_select)
            return data
        else:
            return result
    except Exception as e:
        logger.error(f"Erro ao selecionar dados: {e}")
        return False

def update_info(session: Session, model: Type[Base],
                columnUpdate: str, newValue: Union[str, int, float],
                columnReference: str, valueReference: Union[str, int]) -> bool:
    """
    Atualiza um campo específico.
    Session -> referência a um banco conectado, onde as informaçãona serem modificadas estão contidas.
    Model -> tabela de refência para a alteração das informaçãoes.
    ColumnUpdate -> coluna referêcia que terá o valor modificado.
    ColummReference -> coluna que representa a entidade que será modificada.
    valueReference -> valor de busca usado para identificar a entidade.
    """
    try:
        stmt = (
            update(model)
            .where(getattr(model, columnReference) == valueReference)
            .values({columnUpdate: newValue})
        )
        session.execute(stmt)
        session.commit()
        logger.info(f"Registro atualizado em {model.__tablename__}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao atualizar: {e}")
        return False

def delete_info(session: Session, model: Type[Base],
                columnReference: str, valueReference: Union[str, int]) -> bool:
    """
    Deleta um registro do banco.
    Session -> referência a um banco conectado, onde as informaçãona serem modificadas estão contidas.
    Model -> tabela de refência para a alteração das informaçãoes.
    ColumnReference -> coluna que representa a entidade que será deletado.
    valueReference -> valor de busca usado para identificar a entidade. 
    """
    try:
        stmt = delete(model).where(getattr(model, columnReference) == valueReference)
        session.execute(stmt)
        session.commit()
        logger.info(f"Registro deletado de {model.__tablename__}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao deletar: {e}")
        return False