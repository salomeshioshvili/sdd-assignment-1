from datetime import date
import pytest
from log import service

def form(**overrides):
    data = {
        "name": "Test Hack",
        "location": "Madrid",
        "mode": "in_person",
        "start_date": "2026-11-01",
        "end_date": "2026-11-02",
        "application_deadline": "",
        "notes": "",
    }
    data.update(overrides)
    return data

def attended_hackathon(conn):
    hackathon_id = service.add_hackathon(conn, form())
    for status in ("applied", "accepted", "attended"):
        service.change_status(conn, hackathon_id, status)
    return hackathon_id

def test_can_transition_allows_valid_move():
    assert service.can_transition("interested", "applied") is True

def test_can_transition_blocks_invalid_moves():
    assert service.can_transition("rejected", "attended") is False
    assert service.can_transition("attended", "applied") is False
    assert service.can_transition("nonsense", "applied") is False

def test_urgency_buckets():
    today = date(2026, 10, 9)
    assert service.urgency(None, today) == "no_deadline"
    assert service.urgency("2026-10-08", today) == "overdue"
    assert service.urgency("2026-10-09", today) == "urgent" # 0 days left
    assert service.urgency("2026-10-12", today) == "urgent" # 3 days left
    assert service.urgency("2026-10-13", today) == "soon" # 4 days left
    assert service.urgency("2026-10-23", today) == "soon" # 14 days left
    assert service.urgency("2026-10-24", today) == "later" # 15 days left

def test_parse_technologies_cleans_and_dedupes():
    assert service.parse_technologies("Python, flask,, python") == ["flask", "python"]
    assert service.parse_technologies("") == []
    assert service.parse_technologies(None) == []

def test_validate_hackathon_returns_clean_values():
    cleaned = service.validate_hackathon(form(name="  Test Hack  ", travel_funded="on"))
    assert cleaned["name"] == "Test Hack"
    assert cleaned["travel_funded"] == 1
    assert cleaned["application_deadline"] is None
    assert cleaned["notes"] is None

@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"name": "  "}, "Name is required"),
        ({"mode": "teleport"}, "Mode must be"),
        ({"start_date": ""}, "Start date is required"),
        ({"end_date": "not-a-date"}, "End date must look like"),
        ({"end_date": "2026-10-30"}, "End date cannot be before"),
        ({"application_deadline": "30/10/2026"}, "Application deadline must look like"),
    ],
)
def test_validate_hackathon_rejects_bad_input(overrides, message):
    with pytest.raises(ValueError, match=message):
        service.validate_hackathon(form(**overrides))

# SQLite functions
def test_add_hackathon_starts_as_interested(conn):
    hackathon_id = service.add_hackathon(conn, form())
    saved = service.get_hackathon(conn, hackathon_id)
    assert saved["status"] == "interested"
    assert saved["name"] == "Test Hack"
    assert saved["projects"] == []
    assert saved["teammates"] == []

def test_add_hackathon_rejects_invalid_form(conn):
    with pytest.raises(ValueError):
        service.add_hackathon(conn, form(name=""))
    assert service.list_hackathons(conn) == []

def test_get_hackathon_missing_returns_none(conn):
    assert service.get_hackathon(conn, 999) is None

def test_change_status_follows_rules(conn):
    hackathon_id = service.add_hackathon(conn, form())
    service.change_status(conn, hackathon_id, "applied")
    assert service.get_hackathon(conn, hackathon_id)["status"] == "applied"
    with pytest.raises(ValueError):
        service.change_status(conn, hackathon_id, "attended")
    assert service.get_hackathon(conn, hackathon_id)["status"] == "applied"

def test_change_status_unknown_hackathon(conn):
    with pytest.raises(LookupError):
        service.change_status(conn, 999, "applied")

def test_add_project_requires_attended(conn):
    hackathon_id = service.add_hackathon(conn, form())
    with pytest.raises(ValueError, match="attended"):
        service.add_project(conn, hackathon_id, "App", "winner", "python")

def test_add_project_saves_technologies(conn):
    hackathon_id = attended_hackathon(conn)
    service.add_project(conn, hackathon_id, "  Sleep Inbox ", "winner", "Python, Flask")
    project = service.get_hackathon(conn, hackathon_id)["projects"][0]
    assert project["name"] == "Sleep Inbox"
    assert project["result"] == "winner"
    assert project["technologies"] == ["flask", "python"]

def test_add_project_rejects_bad_input(conn):
    hackathon_id = attended_hackathon(conn)
    with pytest.raises(ValueError, match="Project name"):
        service.add_project(conn, hackathon_id, " ", "winner", "")
    with pytest.raises(ValueError, match="Result"):
        service.add_project(conn, hackathon_id, "App", "champion", "")

def test_add_project_unknown_hackathon(conn):
    with pytest.raises(LookupError):
        service.add_project(conn, 999, "App", "winner", "")

def test_add_teammate_links_once(conn):
    hackathon_id = service.add_hackathon(conn, form())
    service.add_teammate(conn, hackathon_id, "Ana")
    service.add_teammate(conn, hackathon_id, " Ana ")
    assert service.get_hackathon(conn, hackathon_id)["teammates"] == ["Ana"]


def test_add_teammate_reuses_person_across_hackathons(conn):
    first = service.add_hackathon(conn, form(name="One"))
    second = service.add_hackathon(conn, form(name="Two"))
    service.add_teammate(conn, first, "Ana")
    service.add_teammate(conn, second, "Ana")
    assert conn.execute("SELECT COUNT(*) FROM teammates").fetchone()[0] == 1

def test_add_teammate_rejects_blank_or_unknown(conn):
    hackathon_id = service.add_hackathon(conn, form())
    with pytest.raises(ValueError):
        service.add_teammate(conn, hackathon_id, "  ")
    with pytest.raises(LookupError):
        service.add_teammate(conn, 999, "Ana")

def test_list_hackathons_flags_urgency_only_while_interested(conn):
    service.add_hackathon(conn, form(name="A", application_deadline="2026-10-11"))
    applied = service.add_hackathon(conn, form(name="B", application_deadline="2026-10-11"))
    service.change_status(conn, applied, "applied")
    result = {h["name"]: h["urgency"] for h in service.list_hackathons(conn, today=date(2026, 10, 9))}
    assert result == {"A": "urgent", "B": "none"}

def test_list_hackathon_records_returns_plain_dicts_with_children(conn):
    hackathon_id = attended_hackathon(conn)
    service.add_teammate(conn, hackathon_id, "Ana")
    service.add_project(conn, hackathon_id, "App", "finalist", "python")
    records = service.list_hackathon_records(conn)
    assert len(records) == 1
    assert isinstance(records[0], dict)
    assert records[0]["teammates"] == ["Ana"]
    assert records[0]["projects"][0]["technologies"] == ["python"]