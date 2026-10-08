import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import config

SEED_PATH = Path(__file__).parent / "seed.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS hackathons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('in_person', 'online', 'hybrid')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    application_deadline TEXT,
    status TEXT NOT NULL DEFAULT 'interested'
        CHECK (status IN ('interested', 'applied', 'accepted',
                          'attended', 'rejected', 'skipped')),
    travel_funded INTEGER NOT NULL DEFAULT 0 CHECK (travel_funded IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teammates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS hackathon_teammates (
    hackathon_id INTEGER NOT NULL REFERENCES hackathons(id) ON DELETE CASCADE,
    teammate_id INTEGER NOT NULL REFERENCES teammates(id) ON DELETE CASCADE,
    PRIMARY KEY (hackathon_id, teammate_id)
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hackathon_id INTEGER NOT NULL REFERENCES hackathons(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    result TEXT NOT NULL DEFAULT 'participated'
        CHECK (result IN ('participated', 'finalist', 'winner')),
    url TEXT
);

CREATE TABLE IF NOT EXISTS project_technologies (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    technology TEXT NOT NULL,
    PRIMARY KEY (project_id, technology)
);

CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hackathon_id INTEGER NOT NULL REFERENCES hackathons(id) ON DELETE CASCADE,
    went_well TEXT,
    went_badly TEXT,
    lesson TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checklist_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_field TEXT NOT NULL,
    condition_value TEXT NOT NULL,
    item TEXT NOT NULL,
    UNIQUE (condition_field, condition_value, item)
);
"""

def get_connection() -> sqlite3.Connection:
    """Open the SQLite file, creating DATA_DIR first if it doesn't exist."""
    os.makedirs(config.get_data_dir(), exist_ok=True)
    conn = sqlite3.connect(config.get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def seed_if_empty(conn: sqlite3.Connection) -> None:
    """Load seed.json into each seeded table only when that table is empty."""
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    if conn.execute("SELECT COUNT(*) FROM hackathons").fetchone()[0] == 0:
        conn.executemany(
            """INSERT INTO hackathons
               (name, location, mode, start_date, end_date,
                application_deadline, status, travel_funded, notes)
               VALUES (:name, :location, :mode, :start_date, :end_date,
                       :application_deadline, :status, :travel_funded, :notes)""",
            seed["hackathons"],
        )

    if conn.execute("SELECT COUNT(*) FROM checklist_rules").fetchone()[0] == 0:
        conn.executemany(
            """INSERT INTO checklist_rules
               (condition_field, condition_value, item)
               VALUES (:condition_field, :condition_value, :item)""",
            seed["checklist_rules"],
        )

def init_db() -> None:
    """Create any missing tables and seed empty ones. Never drops anything."""
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        with conn:  # commits the seed inserts as one transaction
            seed_if_empty(conn)