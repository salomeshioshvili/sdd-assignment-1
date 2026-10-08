import os

def get_port() -> int:
    """Port to listen on. Read from the PORT env var, default 8000."""
    return int(os.environ.get("PORT", "8000"))

def get_data_dir() -> str:
    """Directory that holds the SQLite file. Read from DATA_DIR, default ./data."""
    return os.environ.get("DATA_DIR", "./data")

def get_db_path() -> str:
    """Full path of the SQLite file, always inside DATA_DIR."""
    return os.path.join(get_data_dir(), "hackathon_journal.db")