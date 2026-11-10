import os
import time
from urllib.parse import urlparse

import pymssql
import requests
from flask import Flask, jsonify

PORT = int(os.environ.get("PORT", "8002"))
GIT_SHA = os.environ.get("GIT_SHA", "dev")
LOG_URL = os.environ.get("LOG_URL", "http://log:8001").rstrip("/")
LOG_TIMEOUT_S = float(os.environ.get("LOG_TIMEOUT_S", "2"))


def db_params():
    raw = os.environ["DATABASE_URL"]
    for prefix in ("mssql+pymssql://", "mssql://", "pymssql://"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
            break
    parsed = urlparse("mssql://" + raw)
    return {
        "server": parsed.hostname,
        "port": parsed.port or 1433,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip("/"),
    }


def connect(retries=30):
    params = db_params()
    last = None
    for _ in range(retries):
        try:
            return pymssql.connect(as_dict=True, login_timeout=10, **params)
        except Exception as err:
            last = err
            time.sleep(2)
    raise RuntimeError(last)


def setup_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'notes')
        CREATE TABLE notes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            text NVARCHAR(255) NOT NULL
        )
        """
    )
    cur.execute("SELECT COUNT(*) AS n FROM notes")
    if cur.fetchone()["n"] == 0:
        cur.execute("INSERT INTO notes (text) VALUES (%s)", ("insights own data",))
    conn.commit()
    conn.close()


def create_app():
    setup_db()
    app = Flask(__name__)

    @app.get("/health")
    def health():
        try:
            conn = connect(retries=3)
            cur = conn.cursor()
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
            conn.close()
            db_ok = True
        except Exception:
            db_ok = False
        body = {
            "status": "ok" if db_ok else "error",
            "db": "ok" if db_ok else "error",
            "version": GIT_SHA,
            "service": "insights",
        }
        return jsonify(body), (200 if db_ok else 503)

    @app.get("/api/notes")
    def notes():
        conn = connect(retries=5)
        cur = conn.cursor()
        cur.execute("SELECT id, text FROM notes ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return jsonify(rows)

    @app.get("/api/stats")
    def stats():
        try:
            response = requests.get(
                f"{LOG_URL}/api/hackathons",
                timeout=LOG_TIMEOUT_S,
            )
            response.raise_for_status()
            rows = response.json()
        except (requests.RequestException, ValueError) as err:
            return (
                jsonify(
                    {
                        "error": "log_unavailable",
                        "message": "Stats need the log service.",
                        "detail": str(err),
                    }
                ),
                503,
            )
        attended = sum(1 for row in rows if row.get("status") == "attended")
        return jsonify({"hackathons": len(rows), "attended": attended})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
