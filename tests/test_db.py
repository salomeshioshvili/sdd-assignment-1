import db

def table_count(table):
    conn = db.get_connection()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()

def test_init_db_twice_keeps_row_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db()
    first = {t: table_count(t) for t in ("hackathons", "checklist_rules")}
    db.init_db()
    second = {t: table_count(t) for t in ("hackathons", "checklist_rules")}
    assert first["hackathons"] > 0
    assert first == second

def test_init_db_keeps_data_added_after_first_boot(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db.init_db()
    conn = db.get_connection()
    try:
        conn.execute("INSERT INTO teammates (name) VALUES ('Ana')")
        conn.commit()
    finally:
        conn.close()
    db.init_db()
    assert table_count("teammates") == 1