import os
import uuid

from flask import Flask
from flask_socketio import SocketIO
from .jinjafilters import *
from .errorhandlers import *

socketio = SocketIO()

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ['SESSION_SECRET']
    )

    # Custom code: Initialize custom config
    app.config.from_object("config")

    # Custom code: Initialize session ID
    initialize_sid(app)
    socketio.init_app(app, engineio_logger=True, logger=True)

    from . import bl_home
    app.register_blueprint(bl_home.bp)

    from . import bl_modals
    app.register_blueprint(bl_modals.bp)

    from . import bl_niceurls
    app.register_blueprint(bl_niceurls.bp)

    from . import auth
    app.register_blueprint(auth.bp)

    # ADDS HANDLER FOR ERRORs
    app.register_error_handler(500, error_500)
    app.register_error_handler(404, error_404)

    # JINJA FILTERS
    app.jinja_env.filters['slugify'] = slugify
    app.jinja_env.filters['displayError'] = displayError 
    app.jinja_env.filters['displayMessage'] = displayMessage

    return app


def initialize_sid(app):
    if not hasattr(app.config, 'uid'):
        sid = str(uuid.uuid4())
        app.config['uid'] = sid
        print("initialize_params - Session ID stored =", sid)



