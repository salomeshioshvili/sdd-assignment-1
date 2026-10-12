#!/usr/bin/env bash
#
# SDD Individual Assignment 1: contract checker.
#
# Builds your repository with the Dockerfile at its root and checks the output
# contract documented at the top of that file. Run it before you submit and
# paste the output into your README as your §7 evidence.
#
#   ./run.sh                     check the repo in the current directory
#   ./run.sh /path/to/your/repo  check that repo
#   ./run.sh . --keep            leave the app running when the checks pass
#
# Overrides, all optional:
#   PORT=8000       primary port to test     ALT_PORT=9123   port-override test
#   NAME=my-app     image / container name

set -euo pipefail

REPO="${1:-.}"
MODE="${2:-}"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; CYN=$'\033[36m'; OFF=$'\033[0m'
step()  { printf '\n%s==>%s %s\n' "$CYN" "$OFF" "$*"; }
pass()  { printf '  %sPASS%s  %s\n' "$GRN" "$OFF" "$*"; }
warn()  { printf '  %sWARN%s  %s\n' "$YEL" "$OFF" "$*"; }
fail()  { printf '\n  %sFAIL%s  %s\n\n' "$RED" "$OFF" "$*"; cleanup; exit 1; }

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  [ "${KEEP_VOLUME:-0}" = "1" ] || docker volume rm "$VOLUME" >/dev/null 2>&1 || true
}

[ -d "$REPO" ] || { echo "Not a directory: $REPO" >&2; exit 1; }
REPO="$(cd "$REPO" && pwd)"
command -v docker >/dev/null || { echo "Docker is not on PATH." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop." >&2; exit 1; }

PORT="${PORT:-8000}"
ALT_PORT="${ALT_PORT:-9123}"
NAME="${NAME:-sdd-$(basename "$REPO" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9._-')}"
VOLUME="${NAME}-data"
trap cleanup EXIT

printf '%s=== SDD Assignment 1 contract check ===%s\n' "$CYN" "$OFF"
printf 'Repository: %s\n' "$REPO"

# -- 1. Repository shape (§1a, §7.7) ------------------------------------------
step "Repository shape"
[ -f "$REPO/Dockerfile" ] || fail "No Dockerfile at the repo root.
        Copy the provided template there and fill in its TODOs."

manifests=0
for m in requirements.txt pyproject.toml package.json; do
  [ -f "$REPO/$m" ] && { manifests=$((manifests+1)); found="$m"; }
done
[ "$manifests" -eq 0 ] && fail "No dependency manifest at the repo root (§7.7)."
[ "$manifests" -gt 1 ] && fail "More than one dependency manifest at the repo root (§7.7)."
pass "one Dockerfile, one manifest ($found)"

for d in .github/workflows; do
  [ -d "$REPO/$d" ] && warn "$d exists. CI is Assignment 2; it is ignored here."
done
if [ -f "$REPO/.env" ]; then
  if [ -f "$REPO/.gitignore" ] && grep -qE '(^|/)\.env' "$REPO/.gitignore"; then
    pass ".env present but gitignored"
  else
    warn ".env is NOT in .gitignore. Secrets must never reach your repo or image."
  fi
fi

# -- 2. Clean build (§7.4, §7.7) ----------------------------------------------
step "Build from a clean context, no build args"
docker rm -f "$NAME" >/dev/null 2>&1 || true
DOCKER_BUILDKIT=1 docker build --quiet --tag "$NAME" "$REPO" >/dev/null \
  || fail "Build failed. Every package your app imports must be listed in your
        manifest, pinned, and installable on a clean machine."
pass "image built"

size="$(docker image inspect "$NAME" --format '{{.Size}}')"
pass "image size $(( size / 1000000 )) MB"
if docker run --rm --entrypoint sh "$NAME" -c 'test -e /app/.env' 2>/dev/null; then
  fail ".env was copied into the image. Secrets must never be baked into an
        image. See TODO 3 in the Dockerfile: copy your source files explicitly
        instead of \`COPY . .\`, which ignores .gitignore entirely."
fi
for junk in .git node_modules .venv venv; do
  docker run --rm --entrypoint sh "$NAME" -c "test -e /app/$junk" 2>/dev/null \
    && warn "$junk is inside the image. Copy your source explicitly (TODO 3)."
done

# -- 3. Start and reachability (§7.2, §7.10) ----------------------------------
step "Start on PORT=$PORT and reach it from the host"
docker volume create "$VOLUME" >/dev/null
docker run --detach --name "$NAME" \
  --publish "${PORT}:${PORT}" --env "PORT=${PORT}" \
  --volume "${VOLUME}:/data" "$NAME" >/dev/null

code=""
for _ in $(seq 1 30); do
  if ! docker ps --filter "name=^${NAME}$" --filter "status=running" -q | grep -q .; then
    printf '\n'; docker logs "$NAME" 2>&1 | tail -25
    fail "Container exited. Common causes: a crash on startup, waiting for input
        (§7.4 forbids interactive setup), or failing to create its SQLite file."
  fi
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${PORT}/" || true)"
  [ -n "$code" ] && [ "$code" != "000" ] && break
  sleep 1
done
[ -n "$code" ] && [ "$code" != "000" ] \
  || { printf '\n'; docker logs "$NAME" 2>&1 | tail -25
       fail "Nothing answered on http://localhost:${PORT} after 30s.
        Almost always: the app bound 127.0.0.1 instead of 0.0.0.0 (§7.2)."; }
pass "HTTP $code from http://localhost:${PORT}/"

# -- 4. SQLite under DATA_DIR (§7.5) ------------------------------------------
step "SQLite file under DATA_DIR"
db="$(docker exec "$NAME" sh -c 'ls -1 /data 2>/dev/null' | head -5 || true)"
if [ -z "$db" ]; then
  warn "/data is empty. If your app creates the database lazily, exercise a"
  warn "feature in the browser first, then re-run this check."
else
  pass "found in /data: $(echo "$db" | tr '\n' ' ')"
fi

# -- 5. Persistence and idempotent seeding (§7.5, §7.11) ----------------------
# Row counts per table, read on the host so this works whatever language the
# app is written in and whether or not the image ships a sqlite3 binary.
db_counts() {
  local dbfile out
  dbfile="$(docker exec "$NAME" sh -c "ls -1 /data/*.db /data/*.sqlite /data/*.sqlite3 2>/dev/null" | head -1 || true)"
  [ -n "$dbfile" ] || return 1
  command -v python3 >/dev/null || return 2
  rm -f "$TMPDB"
  docker cp "${NAME}:${dbfile}" "$TMPDB" >/dev/null 2>&1 || return 1
  python3 - "$TMPDB" <<'PY' 2>/dev/null || return 1
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
rows = con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' "
    "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
for (t,) in rows:
    try:
        print(f"{t}={con.execute(f'SELECT count(*) FROM \"{t}\"').fetchone()[0]}")
    except sqlite3.Error:
        pass
PY
}

TMPDB="$(mktemp -t sdd-check).db"
step "Data persists, and a second boot does not re-seed"
before="$(db_counts || true)"
docker exec "$NAME" sh -c 'echo marker > /data/.sdd-check' 2>/dev/null || true
docker rm -f "$NAME" >/dev/null
docker run --detach --name "$NAME" \
  --publish "${PORT}:${PORT}" --env "PORT=${PORT}" \
  --volume "${VOLUME}:/data" "$NAME" >/dev/null

for _ in $(seq 1 20); do
  c="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${PORT}/" || true)"
  [ -n "$c" ] && [ "$c" != "000" ] && break
  sleep 1
done

if docker exec "$NAME" sh -c 'test -f /data/.sdd-check' 2>/dev/null; then
  docker exec "$NAME" sh -c 'rm -f /data/.sdd-check' 2>/dev/null || true
  pass "volume at /data persists"
else
  fail "The volume at /data did not persist. Your SQLite file must live under
        \$DATA_DIR, not next to your source in /app."
fi

after="$(db_counts || true)"
if [ -z "$before" ] || [ -z "$after" ]; then
  warn "Could not read row counts, skipping the re-seed check."
elif [ "$before" = "$after" ]; then
  pass "row counts unchanged across restart: $(echo "$before" | tr '\n' ' ')"
else
  printf '    before: %s\n' "$(echo "$before" | tr '\n' ' ')"
  printf '    after:  %s\n' "$(echo "$after" | tr '\n' ' ')"
  fail "Row counts changed on a plain restart. Your seed or migration runs again
        every boot instead of only when the data is missing (§7.11). Guard it:
        seed only when the table is empty, or use INSERT OR IGNORE on a unique
        key. In Assignment 2 this duplicates your data on every redeploy."
fi
rm -f "$TMPDB"

# -- 6. PORT is honoured, not hardcoded (§7.3) --------------------------------
step "PORT override is honoured (not hardcoded)"
docker rm -f "$NAME" >/dev/null
docker run --detach --name "$NAME" \
  --publish "${ALT_PORT}:${ALT_PORT}" --env "PORT=${ALT_PORT}" \
  --volume "${VOLUME}:/data" "$NAME" >/dev/null
alt=""
for _ in $(seq 1 20); do
  alt="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${ALT_PORT}/" || true)"
  [ -n "$alt" ] && [ "$alt" != "000" ] && break
  sleep 1
done
[ -n "$alt" ] && [ "$alt" != "000" ] \
  || fail "App did not come up on PORT=${ALT_PORT}. It is ignoring \$PORT and
        binding a hardcoded one. Matching the default 8000 is not enough (§7.3)."
pass "HTTP $alt from http://localhost:${ALT_PORT}/"

# -- Done ---------------------------------------------------------------------
printf '\n%s=== ALL CHECKS PASSED ===%s\n' "$GRN" "$OFF"
printf 'Paste this output into your README as the §7 evidence.\n'

if [ "$MODE" = "--keep" ]; then
  KEEP_VOLUME=1
  docker rm -f "$NAME" >/dev/null
  docker run --detach --name "$NAME" --publish "${PORT}:${PORT}" \
    --env "PORT=${PORT}" --volume "${VOLUME}:/data" "$NAME" >/dev/null
  trap - EXIT
  printf '\nRunning at http://localhost:%s\n  logs: docker logs -f %s\n  stop: docker rm -f %s\n\n' \
    "$PORT" "$NAME" "$NAME"
fi
