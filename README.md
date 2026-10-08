# Hackathon Journal

A personal tracker for hackathons I apply to and attend: status, deadlines, projects, teammates and insights. Built as a single-process Flask monolith with SQLite.

## Run locally
    python3.12 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python app.py

The app listens on http://localhost:8000.

## Run with Docker
    docker build -t hj .
    docker run -p 8000:8000 -v hj-data:/data hj

## Environment variables
| Variable | Default | Meaning |
|---|---|---|
| PORT | 8000 | Port the app listens on |
| DATA_DIR | ./data locally, /data in the container | Directory that holds the SQLite file |

SQLite file path: `$DATA_DIR/hackathon_journal.db`

## First boot and seed data
On startup the app creates any missing tables and loads `seed.json` into a table only if that table is empty. Restarting never resets or duplicates data.

## Tests and coverage
(added Oct 11)

## Container contract evidence (run.sh output)
(added Oct 11)

## AI disclosure statement
(added Oct 12)