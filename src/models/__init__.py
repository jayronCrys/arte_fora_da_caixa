# Importações globais do SQLAlchemy usadas nos modelos para evitar
# importar sempre Column, String, etc. em cada arquivo de modelo.
# `from models import *` para pegar essas referências.
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    LargeBinary, Enum, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

# Base e session/engine ficam no subpacote database
from .database import Base, engine, get_session

__all__ = [
    "Base", "engine", "get_session",
    "Column", "Integer", "String", "Text", "DateTime", "ForeignKey",
    "LargeBinary", "Enum", "func", "relationship", "UUID"
]