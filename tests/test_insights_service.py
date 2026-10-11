import pytest
from insights import service

def record(id, status="attended", mode="in_person", teammates=(), projects=()):
    return {
        "id": id,
        "name": f"Hack {id}",
        "status": status,
        "mode": mode,
        "teammates": list(teammates),
        "projects": list(projects),
    }

def project(result="participated", technologies=()):
    return {"name": "P", "result": result, "technologies": list(technologies)}

RULES = [
    {"condition_field": "always", "condition_value": "*", "item": "Laptop"},
    {"condition_field": "mode", "condition_value": "online", "item": "Headset"},
    {"condition_field": "mode", "condition_value": "in_person", "item": "Snacks"},
    {"condition_field": "mode", "condition_value": "in_person", "item": "Laptop"},
]

def test_attended_and_upcoming_filter_by_status():
    records = [record(1, "attended"), record(2, "interested"), record(3, "rejected"), record(4, "accepted")]
    assert [r["id"] for r in service.attended(records)] == [1]
    assert [r["id"] for r in service.upcoming(records)] == [2, 4]

def test_find_record():
    records = [record(1), record(2)]
    assert service.find_record(records, 2)["id"] == 2
    assert service.find_record(records, 9) is None
    assert service.find_record(records, None) is None

def test_compute_stats_with_no_data():
    stats = service.compute_stats([])
    assert stats["attended"] == 0
    assert stats["win_rate_percent"] == 0
    assert stats["top_technologies"] == []

def test_compute_stats_counts_only_attended():
    records = [
        record(1, teammates=["Ana", "Bo"], projects=[project("winner", ["python", "flask"])]),
        record(2, teammates=["Ana"], projects=[project("finalist", ["python"]), project("participated", ["react"])]),
        record(3, status="skipped", teammates=["Zed"], projects=[project("winner", ["swift"])]),
    ]
    stats = service.compute_stats(records)
    assert stats["attended"] == 2
    assert stats["projects"] == 3
    assert stats["won"] == 1
    assert stats["win_rate_percent"] == 50
    assert stats["top_technologies"][0] == ("python", 2)
    assert ("swift", 1) not in stats["top_technologies"]
    assert stats["top_teammates"][0] == ("Ana", 2)

def test_compute_stats_ranks_ties_alphabetically_and_respects_limit():
    records = [record(1, projects=[project(technologies=["b", "a", "c"])])]
    stats = service.compute_stats(records, limit=2)
    assert stats["top_technologies"] == [("a", 1), ("b", 1)]

def test_win_rate_is_rounded():
    records = [record(1, projects=[project("winner")]), record(2), record(3)]
    assert service.compute_stats(records)["win_rate_percent"] == 33

def test_skill_gaps_lists_unused_known_technologies():
    records = [record(1, projects=[project(technologies=["python", "flask"])])]
    assert service.skill_gaps(records, known=("python", "flask", "swift", "sql")) == ["swift", "sql"]

def test_skill_gaps_ignores_unknown_technologies():
    records = [record(1, projects=[project(technologies=["cobol"])])]
    assert service.skill_gaps(records, known=("python",)) == ["python"]

def test_checklist_uses_always_and_matching_mode_rules():
    assert service.generate_checklist(record(1, mode="online"), RULES) == ["Laptop", "Headset"]

def test_checklist_removes_duplicates():
    assert service.generate_checklist(record(1, mode="in_person"), RULES) == ["Laptop", "Snacks"]

def test_checklist_ignores_unknown_fields():
    rules = [{"condition_field": "colour", "condition_value": "red", "item": "Hat"}]
    assert service.generate_checklist(record(1), rules) == []

def test_validate_reflection_accepts_attended_with_text():
    cleaned = service.validate_reflection(record(1), "  Good team ", "", None)
    assert cleaned == {"hackathon_id": 1, "went_well": "Good team", "went_badly": None, "lesson": None}

def test_validate_reflection_needs_attended_record():
    with pytest.raises(ValueError, match="attended"):
        service.validate_reflection(None, "x", "", "")
    with pytest.raises(ValueError, match="attended"):
        service.validate_reflection(record(1, status="rejected"), "x", "", "")

def test_validate_reflection_needs_some_text():
    with pytest.raises(ValueError, match="at least one"):
        service.validate_reflection(record(1), " ", "", None)

def test_label_reflections_adds_names():
    reflections = [{"hackathon_id": 1, "lesson": "x"}, {"hackathon_id": 99, "lesson": "y"}]
    labelled = service.label_reflections(reflections, [record(1)])
    assert labelled[0]["hackathon_name"] == "Hack 1"
    assert labelled[1]["hackathon_name"] == "Unknown"

# SQLite functions
def test_add_and_list_reflections_newest_first(conn):
    conn.execute(
        "INSERT INTO hackathons (name, mode, start_date, end_date) "
        "VALUES ('H', 'online', '2026-01-01', '2026-01-02')"
    )
    conn.commit()
    service.add_reflection(conn, {"hackathon_id": 1, "went_well": "a", "went_badly": None, "lesson": "first"})
    service.add_reflection(conn, {"hackathon_id": 1, "went_well": None, "went_badly": "b", "lesson": "second"})
    assert [r["lesson"] for r in service.list_reflections(conn)] == ["second", "first"]

def test_list_checklist_rules_keeps_insert_order(conn):
    conn.execute("INSERT INTO checklist_rules (condition_field, condition_value, item) VALUES ('always', '*', 'A')")
    conn.execute("INSERT INTO checklist_rules (condition_field, condition_value, item) VALUES ('mode', 'online', 'B')")
    conn.commit()
    assert service.list_checklist_rules(conn) == [
        {"condition_field": "always", "condition_value": "*", "item": "A"},
        {"condition_field": "mode", "condition_value": "online", "item": "B"},
    ]