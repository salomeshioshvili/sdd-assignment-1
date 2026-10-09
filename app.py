from flask import Flask

import config
import db
from log.routes import bp as log_bp

def create_app() -> Flask:
    app = Flask(__name__)
    db.init_db()  # create missing tables and seed empty ones on every boot
    app.register_blueprint(log_bp)
    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=config.get_port())