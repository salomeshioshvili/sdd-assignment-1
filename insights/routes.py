from contextlib import closing
from flask import Blueprint, abort, redirect, render_template, request, url_for

import db
from insights import service
from log.service import list_hackathon_records

bp = Blueprint("insights", __name__, url_prefix="/insights")

@bp.get("/")
def index():
    with closing(db.get_connection()) as conn:
        records = list_hackathon_records(conn)
        reflections = service.label_reflections(service.list_reflections(conn), records)
    return render_template(
        "insights/index.html",
        stats=service.compute_stats(records),
        gaps=service.skill_gaps(records),
        upcoming=service.upcoming(records),
        reflections=reflections,
    )

@bp.get("/checklist/<int:hackathon_id>")
def checklist(hackathon_id):
    with closing(db.get_connection()) as conn:
        records = list_hackathon_records(conn)
        rules = service.list_checklist_rules(conn)
    record = service.find_record(records, hackathon_id)
    if record is None:
        abort(404)
    return render_template(
        "insights/checklist.html", h=record, items=service.generate_checklist(record, rules)
    )

@bp.route("/reflections/new", methods=["GET", "POST"])
def new_reflection():
    error = None
    with closing(db.get_connection()) as conn:
        records = list_hackathon_records(conn)
        if request.method == "POST":
            try:
                hackathon_id = int(request.form.get("hackathon_id", ""))
            except ValueError:
                hackathon_id = None
            try:
                data = service.validate_reflection(
                    service.find_record(records, hackathon_id),
                    request.form.get("went_well"),
                    request.form.get("went_badly"),
                    request.form.get("lesson"),
                )
                service.add_reflection(conn, data)
                return redirect(url_for("insights.index"))
            except ValueError as problem:
                error = str(problem)
    page = render_template(
        "insights/reflection_new.html",
        attended=service.attended(records),
        error=error,
        form=request.form,
    )
    return page, (400 if error else 200)