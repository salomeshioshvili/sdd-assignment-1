from datetime import date

STATUSES = ("interested", "applied", "accepted", "attended", "rejected", "skipped")
MODES = ("in_person", "online", "hybrid")
RESULTS = ("participated", "finalist", "winner")

# For each status, the statuses it is allowed to move to.
ALLOWED_TRANSITIONS = {
    "interested": {"applied", "skipped"},
    "applied": {"accepted", "rejected", "skipped"},
    "accepted": {"attended", "skipped"},
    "attended": set(),
    "rejected": set(),
    "skipped": set(),
}

def can_transition(current: str, new: str) -> bool:
    """True if a hackathon may move from status `current` to status `new`."""
    return new in ALLOWED_TRANSITIONS.get(current, set())

def urgency(deadline, today: date) -> str:
    """Bucket an application deadline (ISO string or None) relative to today."""
    if not deadline:
        return "no_deadline"
    days_left = (date.fromisoformat(deadline) - today).days
    if days_left < 0:
        return "overdue"
    if days_left <= 3:
        return "urgent"
    if days_left <= 14:
        return "soon"
    return "later"

def parse_technologies(text) -> list:
    """'Python, flask,, python' -> ['flask', 'python'] (lowercase, unique, sorted).

    Lowercasing means "Python" and "python" count as one technology later,
    when the insights domain counts how often each one is used.
    """
    names = {part.strip().lower() for part in (text or "").split(",")}
    names.discard("")
    return sorted(names)

def _parse_date(value, label: str, required: bool):
    """Return the date as an ISO string (YYYY-MM-DD), None if optional and empty."""
    value = (value or "").strip()
    if not value:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{label} must look like 2026-10-30.") from None
    return value

def validate_hackathon(data) -> dict:
    """Return a cleaned copy of the form data, or raise ValueError with a message."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Name is required.")
    mode = data.get("mode")
    if mode not in MODES:
        raise ValueError("Mode must be one of: " + ", ".join(MODES) + ".")
    start = _parse_date(data.get("start_date"), "Start date", required=True)
    end = _parse_date(data.get("end_date"), "End date", required=True)
    if end < start:  # ISO dates sort correctly as plain strings
        raise ValueError("End date cannot be before start date.")
    deadline = _parse_date(data.get("application_deadline"), "Application deadline", required=False)
    return {
        "name": name,
        "location": (data.get("location") or "").strip() or None,
        "mode": mode,
        "start_date": start,
        "end_date": end,
        "application_deadline": deadline,
        "travel_funded": 1 if data.get("travel_funded") else 0,
        "notes": (data.get("notes") or "").strip() or None,
    }

# SQLite access
def _get_status(conn, hackathon_id: int) -> str:
    row = conn.execute("SELECT status FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if row is None:
        raise LookupError("Hackathon not found.")
    return row["status"]

def list_hackathons(conn, today=None) -> list:
    """All hackathons by start date. Urgency only matters while still 'interested'."""
    today = today or date.today()
    result = []
    for row in conn.execute("SELECT * FROM hackathons ORDER BY start_date").fetchall():
        h = dict(row)
        if h["status"] == "interested":
            h["urgency"] = urgency(h["application_deadline"], today)
        else:
            h["urgency"] = "none"
        result.append(h)
    return result

def get_hackathon(conn, hackathon_id: int):
    """One hackathon with its projects and teammates, or None if it doesn't exist."""
    row = conn.execute("SELECT * FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if row is None:
        return None
    h = dict(row)

    h["projects"] = []
    for p in conn.execute(
        "SELECT * FROM projects WHERE hackathon_id = ? ORDER BY id", (hackathon_id,)
    ).fetchall():
        project = dict(p)
        project["technologies"] = [
            r["technology"]
            for r in conn.execute(
                "SELECT technology FROM project_technologies WHERE project_id = ? ORDER BY technology",
                (project["id"],),
            ).fetchall()
        ]
        h["projects"].append(project)

    h["teammates"] = [
        r["name"]
        for r in conn.execute(
            """SELECT t.name FROM teammates t
               JOIN hackathon_teammates ht ON ht.teammate_id = t.id
               WHERE ht.hackathon_id = ? ORDER BY t.name""",
            (hackathon_id,),
        ).fetchall()
    ]
    return h

def add_hackathon(conn, data) -> int:
    """Validate and insert a hackathon (status starts as 'interested'). Returns its id."""
    h = validate_hackathon(data)
    with conn:
        cursor = conn.execute(
            """INSERT INTO hackathons
               (name, location, mode, start_date, end_date,
                application_deadline, travel_funded, notes)
               VALUES (:name, :location, :mode, :start_date, :end_date,
                       :application_deadline, :travel_funded, :notes)""",
            h,
        )
    return cursor.lastrowid

def change_status(conn, hackathon_id: int, new_status: str) -> None:
    """Move a hackathon to a new status if the transition is allowed."""
    current = _get_status(conn, hackathon_id)
    if not can_transition(current, new_status):
        raise ValueError(f"Cannot change status from {current} to {new_status}.")
    with conn:
        conn.execute("UPDATE hackathons SET status = ? WHERE id = ?", (new_status, hackathon_id))

def add_teammate(conn, hackathon_id: int, name) -> None:
    """Link a teammate to a hackathon, creating the teammate row if needed."""
    _get_status(conn, hackathon_id)  # raises LookupError if the hackathon is missing
    name = (name or "").strip()
    if not name:
        raise ValueError("Teammate name is required.")
    with conn:
        conn.execute("INSERT OR IGNORE INTO teammates (name) VALUES (?)", (name,))
        teammate_id = conn.execute(
            "SELECT id FROM teammates WHERE name = ?", (name,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO hackathon_teammates (hackathon_id, teammate_id) VALUES (?, ?)",
            (hackathon_id, teammate_id),
        )

def add_project(conn, hackathon_id: int, name, result, technologies_text) -> int:
    """Add a project to an attended hackathon. Returns the project id."""
    if _get_status(conn, hackathon_id) != "attended":
        raise ValueError("Projects can only be added to attended hackathons.")
    name = (name or "").strip()
    if not name:
        raise ValueError("Project name is required.")
    if result not in RESULTS:
        raise ValueError("Result must be one of: " + ", ".join(RESULTS) + ".")
    technologies = parse_technologies(technologies_text)
    with conn:
        cursor = conn.execute(
            "INSERT INTO projects (hackathon_id, name, result) VALUES (?, ?, ?)",
            (hackathon_id, name, result),
        )
        conn.executemany(
            "INSERT INTO project_technologies (project_id, technology) VALUES (?, ?)",
            [(cursor.lastrowid, t) for t in technologies],
        )
    return cursor.lastrowid

# the seam
def list_hackathon_records(conn) -> list:
    """The ONE function the insights domain may call to read log data.

    Returns plain dicts (no sqlite rows), each with its projects and teammates,
    keyed by hackathon id. Read-only: insights never writes to the log's tables.
    """
    ids = [r["id"] for r in conn.execute("SELECT id FROM hackathons ORDER BY start_date").fetchall()]
    return [get_hackathon(conn, hackathon_id) for hackathon_id in ids]