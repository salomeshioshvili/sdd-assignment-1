from contextlib import closing
from flask import Blueprint, abort, redirect, render_template, request, url_for

import db
from log import service

bp = Blueprint("log", __name__)

def _render_detail(conn, hackathon_id, error=None, code=200):
    hackathon = service.get_hackathon(conn, hackathon_id)
    if hackathon is None:
        abort(404)
    next_statuses = sorted(service.ALLOWED_TRANSITIONS[hackathon["status"]])
    page = render_template(
        "log/detail.html",
        h=hackathon,
        next_statuses=next_statuses,
        results=service.RESULTS,
        error=error,
    )
    return page, code

@bp.get("/")
def index():
    with closing(db.get_connection()) as conn:
        hackathons = service.list_hackathons(conn)
    return render_template("log/index.html", hackathons=hackathons)

@bp.route("/hackathons/new", methods=["GET", "POST"])
def new_hackathon():
    if request.method == "POST":
        with closing(db.get_connection()) as conn:
            try:
                new_id = service.add_hackathon(conn, request.form)
            except ValueError as error:
                page = render_template(
                    "log/new.html", error=str(error), form=request.form, modes=service.MODES
                )
                return page, 400
        return redirect(url_for("log.detail", hackathon_id=new_id))
    return render_template("log/new.html", error=None, form={}, modes=service.MODES)

@bp.get("/hackathons/<int:hackathon_id>")
def detail(hackathon_id):
    with closing(db.get_connection()) as conn:
        return _render_detail(conn, hackathon_id)

@bp.post("/hackathons/<int:hackathon_id>/status")
def update_status(hackathon_id):
    with closing(db.get_connection()) as conn:
        try:
            service.change_status(conn, hackathon_id, request.form.get("status", ""))
        except LookupError:
            abort(404)
        except ValueError as error:
            return _render_detail(conn, hackathon_id, error=str(error), code=400)
    return redirect(url_for("log.detail", hackathon_id=hackathon_id))

@bp.post("/hackathons/<int:hackathon_id>/teammates")
def new_teammate(hackathon_id):
    with closing(db.get_connection()) as conn:
        try:
            service.add_teammate(conn, hackathon_id, request.form.get("name", ""))
        except LookupError:
            abort(404)
        except ValueError as error:
            return _render_detail(conn, hackathon_id, error=str(error), code=400)
    return redirect(url_for("log.detail", hackathon_id=hackathon_id))

@bp.post("/hackathons/<int:hackathon_id>/projects")
def new_project(hackathon_id):
    with closing(db.get_connection()) as conn:
        try:
            service.add_project(
                conn,
                hackathon_id,
                request.form.get("name", ""),
                request.form.get("result", ""),
                request.form.get("technologies", ""),
            )
        except LookupError:
            abort(404)
        except ValueError as error:
            return _render_detail(conn, hackathon_id, error=str(error), code=400)
    return redirect(url_for("log.detail", hackathon_id=hackathon_id))