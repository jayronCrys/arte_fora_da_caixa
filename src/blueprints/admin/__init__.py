import flask

admin_bp = flask.Blueprint("admin", __name__)

from . import routes