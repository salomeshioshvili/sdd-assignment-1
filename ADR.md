# Architecture Decision Record

## 1. Backend language and framework: Flask with sqlite3
Date: 2026-10-08
Status: Decided
Context: The app is a small single-user tracker with two domains, one SQLite file and one process, and I must explain all of its code on paper at the comprehension check. It needs server-rendered pages, simple routing and nothing more.
Decision: I chose Python 3.12 with Flask and the built-in sqlite3 module, rendering Jinja templates from the same process.
Alternatives considered: Django, rejected because its ORM, migrations and admin add hidden behaviour I would have to explain and the app needs none of it. FastAPI, rejected because the app serves HTML pages rather than a JSON API, so its async support and generated schemas buy nothing here. SQLAlchemy on top of Flask, rejected because plain SQL keeps every query visible and the schema is only seven tables.
Consequences: The code stays small and each request path is easy to follow, but I write validation and SQL by hand. Flask's built-in server is only for development, so Assignment 2 would need a production server.

## 2. Scoping the two domains so they can be split later
Date: 2026-10-09
Status: Decided
Context: Assignment 2 splits the app into separate services, so the hackathon log and the insights engine need a clear seam now. Both read and write one SQLite file.
Decision: The log domain (log/) owns hackathons, projects, teammates and the status rules, and the insights domain (insights/) will own reflections, checklist rules and statistics. Insights reads log data only through log.service.list_hackathon_records(), which returns plain dictionaries keyed by hackathon id, and log never imports insights.
Alternatives considered: One shared module holding every query, rejected because it hides which tables belong to which domain. Letting insights run its own joins on the log's tables, rejected because splitting later would mean rewriting those queries.
Consequences: Only one read-only function and hackathon_id cross the seam, so Assignment 2 can turn that call into an API request. For now both domains still share one schema in db.py and one database file.