# AI Usage Log

| Date/commit | Tool | Prompt | Disposition | What changed & why | In my own words, how this works |
|---|---|---|---|---|---|
| 2026-10-08 / ba22e09 | Claude | Asked for the project plan and day-two files (config, app, requirements, .gitignore) | Accepted | Nothing | `get_port()` reads PORT from the environment with a default of 8000. `app.run(host="0.0.0.0")` makes Flask reachable from outside the container. |
| 2026-10-08 / <e5c0c70> | Claude | Asked for db.py and seed.json | Modified | Replaced the sample seed with my real hackathons, added `travel_funded` and `notes`, and mapped my statuses onto the allowed ones so the CHECK constraint accepts them | `init_db()` creates any missing tables, then `seed_if_empty()` inserts from seed.json only when a table has zero rows, so restarts don't duplicate data. |
| 2026-10-08 / <hash3> | Claude | Asked for ADR 1 and the README skeleton | Modified | Reworded the ADR in my own reasons | ADR 1 explains why I chose Flask over Django and FastAPI. |