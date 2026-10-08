from flask import Flask, jsonify

import config

def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return jsonify(app="Hackathon Journal", status="ok")

    return app

if __name__ == "__main__":
    # 0.0.0.0 makes the server reachable from outside the container.
    # 127.0.0.1 would only accept connections from inside it.
    create_app().run(host="0.0.0.0", port=config.get_port())