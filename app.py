from contextlib import closing
from flask import Flask, jsonify

import config
import db

def create_app() -> Flask:
    app = Flask(__name__)
    db.init_db()  # create missing tables and seed empty ones on every boot

    @app.get("/")
    def index():
        with closing(db.get_connection()) as conn:
            count = conn.execute("SELECT COUNT(*) FROM hackathons").fetchone()[0]
        return jsonify(app="Hackathon Journal", status="ok", hackathons=count)

    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=config.get_port())