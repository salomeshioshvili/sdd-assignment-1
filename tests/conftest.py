import sqlite3
import pytest
import db

@pytest.fixture
def conn():
    """A fresh in-memory database with the real schema and no seed data."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(db.SCHEMA)
    yield connection
    connection.close()