from flask import Blueprint

professor_bp = Blueprint("professor", __name__)

from . import routes  # noqa: E402, F401
