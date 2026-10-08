# Architecture Decision Record

## 1. Backend language and framework: Flask with sqlite3
Date: 2026-10-08
Status: Decided
Context: The app is a small single-user tracker with two domains, one SQLite file and one process, and I must explain all of its code on paper at the comprehension check. It needs server-rendered pages, simple routing and nothing more.
Decision: I chose Python 3.12 with Flask and the built-in sqlite3 module, rendering Jinja templates from the same process.
Alternatives considered: Django, rejected because its ORM, migrations and admin add hidden behaviour I would have to explain and the app needs none of it. FastAPI, rejected because the app serves HTML pages rather than a JSON API, so its async support and generated schemas buy nothing here. SQLAlchemy on top of Flask, rejected because plain SQL keeps every query visible and the schema is only seven tables.
Consequences: The code stays small and each request path is easy to follow, but I write validation and SQL by hand. Flask's built-in server is only for development, so Assignment 2 would need a production server.