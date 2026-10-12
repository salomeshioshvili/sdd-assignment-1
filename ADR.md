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
Decision: The log domain (log/) owns hackathons, projects, teammates and the status rules, and the insights domain (insights/) will own reflections, checklist rules and statistics. Insights reads log data only through log.service.list_hackathon_records(), which returns a list of plain dictionaries (each including the hackathon id), and log never imports insights.
Alternatives considered: One shared module holding every query, rejected because it hides which tables belong to which domain. Letting insights run its own joins on the log's tables, rejected because splitting later would mean rewriting those queries.
Consequences: Only one read-only function and hackathon_id cross the seam, so Assignment 2 can turn that call into an API request. For now both domains still share one schema in db.py and one database file.

## 3. Schema: join tables for many-to-many data and a single hackathon_id link between domains
Date: 2026-10-11
Status: Decided
Context: A hackathon has many teammates and a project has many technologies, and the insights domain needs to count both. The insights tables must also refer to a hackathon without owning any of the log's data.
Decision: Teammates and technologies live in join tables (hackathon_teammates and project_technologies) with composite primary keys, and the insights tables (reflections and checklist_rules) connect to the log only through hackathon_id. CHECK constraints on status, mode and result stop invalid values from being stored.
Alternatives considered: Comma-separated names in a text column, rejected because every count would need string parsing and spelling clean-up. A single wide hackathons table with JSON columns, rejected because SQLite cannot enforce allowed values or foreign keys inside JSON.
Consequences: Counting teammates and technologies becomes a plain query over rows, and each domain's tables could move to their own database with only hackathon_id to reconnect them. The cost is that CREATE TABLE IF NOT EXISTS never alters an existing table, so changing a column later needs a real migration.

## 4. Testing approach: test the rules directly, leave routes thin
Date: 2026-10-11
Status: Decided
Context: The 70% bar applies to the business logic of the two domains, and my code is split into pure rule functions and functions that use SQLite.
Decision: I test log/service.py and insights/service.py directly with pytest, using an in-memory SQLite database built from the real schema for the database functions, and measure coverage only on those two packages, leaving out routes. I also test that booting twice keeps the seed data unchanged and keeps rows added later.
Alternatives considered: Testing through Flask's test client, rejected because it exercises routing and templates instead of the rules and makes a failure harder to trace. Mocking the database, rejected because the SQL is part of the logic and an in-memory SQLite is just as fast.
Consequences: Coverage is highest on the code I have to defend, but routes.py, the templates and app.py have no automated tests and are only checked by hand and with container/run.sh.

## 5. Deliberately not built: authentication and multiple users
Date: 2026-10-12
Status: Decided
Context: The journal is a personal tool for one student and holds no sensitive data, and the container contract needs the app to start with no manual setup.
Decision: I did not build login, user accounts or per-user data, so every page is open to anyone who can reach the app's port.
Alternatives considered: Flask sessions with a users table and password hashing, rejected because it adds a table, a secret key to configure and a login flow that I would have to test and defend, none of which a one-user tool needs. A single shared password in an environment variable, rejected because it protects little and would be one more required setting for the container.
Consequences: The app stays simple and every feature belongs to one of the two domains, but it must only run locally or on a private network. Assignment 2's Azure deployment would need authentication before the app is reachable from the internet.