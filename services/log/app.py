import os
import time
from urllib.parse import urlparse

import pymssql
from flask import Flask, jsonify

PORT = int(os.environ.get("PORT", "8001"))
GIT_SHA = os.environ.get("GIT_SHA", "dev")


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
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'hackathons')
        CREATE TABLE hackathons (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            status NVARCHAR(32) NOT NULL
        )
        """
    )
    cur.execute("SELECT COUNT(*) AS n FROM hackathons")
    if cur.fetchone()["n"] == 0:
        cur.execute(
            "INSERT INTO hackathons (name, status) VALUES (%s, %s)",
            ("AdventureX 2026", "attended"),
        )
        cur.execute(
            "INSERT INTO hackathons (name, status) VALUES (%s, %s)",
            ("Turin Hackathon", "skipped"),
        )
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
            "service": "log",
        }
        return jsonify(body), (200 if db_ok else 503)

    @app.get("/api/hackathons")
    def hackathons():
        conn = connect(retries=5)
        cur = conn.cursor()
        cur.execute("SELECT id, name, status FROM hackathons ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return jsonify(rows)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
