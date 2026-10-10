from collections import Counter

# Technologies to compare against, lowercase to match log.service.parse_technologies().
KNOWN_TECHNOLOGIES = (
    "python", "javascript", "typescript", "react", "node",
    "sql", "docker", "flask", "fastapi", "swift",
)
UPCOMING_STATUSES = ("interested", "applied", "accepted")

def attended(records) -> list:
    """Records of hackathons I actually went to."""
    return [r for r in records if r["status"] == "attended"]

def upcoming(records) -> list:
    """Records of hackathons that are still ahead of me."""
    return [r for r in records if r["status"] in UPCOMING_STATUSES]

def find_record(records, hackathon_id):
    """The record with this id, or None."""
    for record in records:
        if record["id"] == hackathon_id:
            return record
    return None

def _ranked(counter: Counter, limit: int) -> list:
    """Most frequent first; ties broken alphabetically so the order is stable."""
    return sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]

def compute_stats(records, limit: int = 5) -> dict:
    """Numbers shown on the insights page, based on attended hackathons only."""
    done = attended(records)
    technologies = Counter()
    teammates = Counter()
    project_count = 0
    won = 0
    for record in done:
        teammates.update(record["teammates"])
        for project in record["projects"]:
            project_count += 1
            technologies.update(project["technologies"])
        if any(project["result"] == "winner" for project in record["projects"]):
            won += 1
    win_rate_percent = round(100 * won / len(done)) if done else 0
    return {
        "attended": len(done),
        "projects": project_count,
        "won": won,  # hackathons where at least one project won
        "win_rate_percent": win_rate_percent,
        "top_technologies": _ranked(technologies, limit),
        "top_teammates": _ranked(teammates, limit),
    }

def skill_gaps(records, known=KNOWN_TECHNOLOGIES) -> list:
    """Known technologies that no project of mine has used yet."""
    used = {t for r in records for p in r["projects"] for t in p["technologies"]}
    return [technology for technology in known if technology not in used]

def generate_checklist(record, rules) -> list:
    """Items from every rule that applies to this hackathon, without duplicates.

    A rule applies if its field is 'always', or if the hackathon's value for that
    field equals the rule's value (e.g. field 'mode', value 'in_person').
    """
    items = []
    for rule in rules:
        field, value = rule["condition_field"], rule["condition_value"]
        applies = field == "always" or str(record.get(field)) == value
        if applies and rule["item"] not in items:
            items.append(rule["item"])
    return items

def validate_reflection(record, went_well, went_badly, lesson) -> dict:
    """Return a cleaned reflection, or raise ValueError with a message."""
    if record is None or record["status"] != "attended":
        raise ValueError("Choose an attended hackathon.")
    texts = {
        "went_well": (went_well or "").strip() or None,
        "went_badly": (went_badly or "").strip() or None,
        "lesson": (lesson or "").strip() or None,
    }
    if not any(texts.values()):
        raise ValueError("Write at least one of: what went well, what went badly, or a lesson.")
    return {"hackathon_id": record["id"], **texts}

def label_reflections(reflections, records) -> list:
    """Attach each reflection's hackathon name, using the records from the log."""
    names = {record["id"]: record["name"] for record in records}
    return [
        {**reflection, "hackathon_name": names.get(reflection["hackathon_id"], "Unknown")}
        for reflection in reflections
    ]

# SQLite access
def list_checklist_rules(conn) -> list:
    rows = conn.execute(
        "SELECT condition_field, condition_value, item FROM checklist_rules ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]

def list_reflections(conn) -> list:
    rows = conn.execute("SELECT * FROM reflections ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]

def add_reflection(conn, data: dict) -> int:
    """Insert a reflection that validate_reflection() already cleaned."""
    with conn:
        cursor = conn.execute(
            """INSERT INTO reflections (hackathon_id, went_well, went_badly, lesson)
               VALUES (:hackathon_id, :went_well, :went_badly, :lesson)""",
            data,
        )
    return cursor.lastrowid