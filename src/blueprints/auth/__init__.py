from flask import Blueprint

auth_bp = Blueprint("auth", __name__)
forg_pass_bp = Blueprint("forgot_password", __name__)
from . import routes, forgot_password # noqa: E402, F401
