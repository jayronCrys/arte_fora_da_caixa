from flask import Blueprint

contents_bp = Blueprint("contents", __name__)

from . import routes  # noqa: E402, F401
