# Hackathon Journal

A personal tracker for hackathons I apply to and attend: deadlines, status, projects, teammates, plus insights (stats, skill gaps, prep checklists and reflections). One Flask process, one SQLite file, one Docker container.

## What it does

- **Log domain (`log/`):** hackathons with a status flow (interested → applied → accepted → attended / rejected / skipped), deadline urgency, projects with technologies, and teammates.
- **Insights domain (`insights/`):** win rate, most-used technologies and teammates, unused technologies, prep checklists from rules, and post-event reflections.

The domains are separate packages. Insights reads log data only through `log.service.list_hackathon_records()` (the Assignment 2 seam). See `ADR.md`, `docs/architecture.md`, and `docs/schema.md`.

## Run locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Starts with that one command and listens on http://localhost:8000. No interactive setup.

## Run with Docker

```bash
docker build -t hj .
docker run -p 8000:8000 -v hj-data:/data hj
```

Another port:

```bash
docker run -e PORT=9000 -p 9000:9000 -v hj-data:/data hj
```

Removing the container and starting again on the same `hj-data` volume keeps the data.

## Configuration

Configured only via environment variables. No `.env` file is required.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Listen port (binds `0.0.0.0`) |
| `DATA_DIR` | `./data` locally, `/data` in the container | Directory for the SQLite file |

SQLite path: `$DATA_DIR/hackathon_journal.db`  
(local: `./data/hackathon_journal.db` · container: `/data/hackathon_journal.db`)

## First boot and seed data

On startup the app creates any missing tables and loads `seed.json` into a table **only if that table is empty**. Restarts do not reset or duplicate data; nothing is dropped. No `.db` file is committed — seed ships as `seed.json`.

## Pages

| URL | Page |
|---|---|
| `/` | Hackathon dashboard / list |
| `/hackathons/new` | Add a hackathon |
| `/hackathons/<id>` | Detail, status change, teammates, projects |
| `/insights/` | Stats, skill gaps, checklists, reflections |
| `/insights/checklist/<id>` | Prep checklist for one hackathon |
| `/insights/reflections/new` | Write a reflection |

## Project layout

```
sdd-assignment-1/
├── app.py                 # Flask entrypoint
├── config.py              # PORT and DATA_DIR
├── db.py                  # schema, connection, seed-if-empty
├── seed.json
├── requirements.txt
├── Dockerfile
├── ADR.md
├── AI_USAGE.md
├── log/                   # domain 1
│   ├── routes.py
│   └── service.py
├── insights/              # domain 2
│   ├── routes.py
│   └── service.py
├── templates/
│   ├── base.html
│   ├── log/
│   └── insights/
├── static/
│   ├── styles.css
│   └── img/
├── tests/
├── docs/
│   ├── schema.md
│   └── architecture.md
└── container/
    └── run.sh             # §7 contract checker
```

## Tests and coverage

```bash
pytest --cov=log --cov=insights --cov-report=term-missing
```

Coverage is measured on the two domain packages; `routes.py` is omitted (see `.coveragerc`). Result from a local run:

```
44 passed

Name                  Stmts   Miss  Cover
-----------------------------------------
insights/service.py      60      0   100%
log/service.py          109      0   100%
-----------------------------------------
TOTAL                   169      0   100%
```

## Container contract check (§7 evidence)

From the repo root (Docker Desktop running):

```bash
./container/run.sh .
```

Output of the final passing run:

```
=== SDD Assignment 1 contract check ===
Repository: /Users/salomeshioshvili/sdd-assignment-1

==> Repository shape
  PASS  one Dockerfile, one manifest (requirements.txt)

==> Build from a clean context, no build args
  PASS  image built
  PASS  image size 51 MB

==> Start on PORT=8000 and reach it from the host
  PASS  HTTP 200 from http://localhost:8000/

==> SQLite file under DATA_DIR
  PASS  found in /data: hackathon_journal.db 

==> Data persists, and a second boot does not re-seed
  PASS  volume at /data persists
  PASS  row counts unchanged across restart: checklist_rules=8 hackathon_teammates=0 hackathons=6 project_technologies=0 projects=0 reflections=0 teammates=0 

==> PORT override is honoured (not hardcoded)
  PASS  HTTP 200 from http://localhost:9123/

=== ALL CHECKS PASSED ===
```

## Documentation

- `ADR.md` — five architecture decision records
- `AI_USAGE.md` — row-by-row AI usage log
- `docs/schema.md` — database diagram (matches ADR 3)
- `docs/architecture.md` — architecture diagram with the domain seam

## AI disclosure statement

I acknowledge the use of Claude (Anthropic) to plan the project, draft application code, unit tests, and documentation (ADRs, README, report), and to explain the container contract; and the use of Cursor to restyle the UI. The prompts used include requests for app ideas within the assignment constraints, the project skeleton and schema, each domain’s service and routes, unit tests with coverage, and documentation drafts. The output of these prompts was used to build the Flask app, SQLite schema and seed loading, tests, and the documents in this repository. I ran the app, modified parts (for example seed data, allowed statuses, and ADR wording), and made the visual design changes in Cursor. The detailed record is in `AI_USAGE.md`.
