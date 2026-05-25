from flask import Blueprint

user_bp = Blueprint("user", __name__)
inscriptions_bp = Blueprint("inscriptions", __name__)
from . import routes, inscriptions # noqa: E402, F401
