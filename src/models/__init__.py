# Importações globais do SQLAlchemy usadas nos modelos para evitar
# importar sempre Column, String, etc. em cada arquivo de modelo.
# `from models import *` para pegar essas referências.
#src/models/__init__.py

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, ForeignKey,
    LargeBinary, Enum, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.models.users_models.user_models import User
from src.models.contents_models.content_models import Contents
from src.models.relationships_models.inscriptions import Subs
# Base e session/engine ficam no subpacote database
from .database import Base, engine, get_session

__all__ = [
    "Base", "engine", "get_session",
    "Column", "Integer", "String", "Text", "Boolean", "DateTime", "ForeignKey",
    "LargeBinary", "Enum", "func", "relationship", "UUID"
]