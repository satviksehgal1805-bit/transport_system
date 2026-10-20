"""Public Transport System - Flask + MySQL (PyMySQL).

User side : browse routes and buses, pick a seat, book, view/cancel own tickets.
Admin side: add / edit / delete rows in all four tables (/admin).
"""
import hmac
import re
import secrets
from datetime import date, timedelta
from functools import wraps

import pymysql
import pymysql.cursors
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# --------------------------------------------------------------------------
# Database helpers (one connection per request)
# --------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**config.DB_CONFIG,
                               cursorclass=pymysql.cursors.DictCursor,
                               autocommit=False)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    """Run a SELECT. Returns a list of dicts, or one dict (or None)."""
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        rows = cur.fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run INSERT / UPDATE / DELETE and commit. Returns the new row id."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(sql, args)
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def friendly(err):
    """Turn a MySQL integrity error into a sentence a person can read."""
    code = err.args[0]
    if code == 1062:
        return ("That value already exists (duplicate email, bus number, "
                "or seat for that bus and date).")
    if code == 1451:
        return "Cannot delete: other records still refer to this row."
    if code == 1452:
        return "The selected related record does not exist."
    return "Database rejected the change (error %s)." % code


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9]{7,14}$")
INT_MAX = 2147483647


def clean_phone(raw):
    return re.sub(r"[\s\-]", "", raw or "")


def validate(fields, form):
    """Check form values against a field list. Returns (clean_values, errors)."""
    clean, errors = {}, []
    for f in fields:
        label, kind = f["label"], f["type"]
        raw = (form.get(f["name"]) or "").strip()
        if not raw:
            errors.append("%s is required." % label)
            continue
        if kind in ("text", "email"):
            if len(raw) > f.get("maxlen", 100):
                errors.append("%s is too long." % label)
            elif kind == "email" and not EMAIL_RE.match(raw):
                errors.append("Enter a valid email address.")
            else:
                clean[f["name"]] = raw.lower() if kind == "email" else raw
        elif kind == "phone":
            phone = clean_phone(raw)
            if PHONE_RE.match(phone):
                clean[f["name"]] = phone
            else:
                errors.append("Phone must be 7 to 14 digits (a leading + is allowed).")
        elif kind in ("number", "select"):
            top = f.get("maxval", INT_MAX)
            if not raw.isdigit() or not 1 <= int(raw) <= top:
                if kind == "select":
                    errors.append("Choose a valid %s." % label.lower())
                else:
                    errors.append("%s must be a whole number from 1 to %d." % (label, top))
            else:
                clean[f["name"]] = int(raw)
        elif kind == "date":
            try:
                d = date.fromisoformat(raw)
                if not 2000 <= d.year <= 2100:
                    raise ValueError
                clean[f["name"]] = d
            except ValueError:
                errors.append("%s must be a valid date." % label)
    return clean, errors


# --------------------------------------------------------------------------
# CSRF protection for every POST form
# --------------------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not hmac.compare_digest(sent.encode(), session.get("_csrf", "").encode()):
            abort(400)


# --------------------------------------------------------------------------
# Error pages
# --------------------------------------------------------------------------
def error_page(code, message, detail=None):
    return render_template("error.html", code=code, message=message, detail=detail), code


@app.errorhandler(404)
def not_found(_e):
    return error_page(404, "Page not found.")


@app.errorhandler(403)
def forbidden(_e):
    return error_page(403, "You are not allowed to do that.")


@app.errorhandler(400)
def bad_request(_e):
    return error_page(400, "The form expired or was invalid. Go back, reload the page and try again.")


@app.errorhandler(pymysql.err.OperationalError)
def db_unreachable(e):
    return error_page(503, "Cannot use the database. Check config.py, that MySQL is "
                           "running, and that database/schema.sql has been imported.", str(e))


# --------------------------------------------------------------------------
# User side
# --------------------------------------------------------------------------
@app.route("/")
def index():
    stats = query(
        "SELECT (SELECT COUNT(*) FROM Routes) AS routes,"
        "       (SELECT COUNT(*) FROM Buses)  AS buses,"
        "       (SELECT COUNT(*) FROM Tickets WHERE travel_date >= %s) AS upcoming",
        (date.today(),), one=True)
    return render_template("index.html", stats=stats)


@app.route("/routes")
def routes_list():
    rows = query(
        "SELECT r.route_id, r.route_name, r.start_point, r.end_point,"
        "       COUNT(b.bus_id) AS bus_count "
        "FROM Routes r LEFT JOIN Buses b ON b.route_id = r.route_id "
        "GROUP BY r.route_id, r.route_name, r.start_point, r.end_point "
        "ORDER BY r.route_id")
    return render_template("routes.html", routes=rows, q=request.args.get("q", ""))


@app.route("/routes/<int:route_id>")
def route_detail(route_id):
    route = query("SELECT * FROM Routes WHERE route_id = %s", (route_id,), one=True)
    if not route:
        abort(404)
    buses = query("SELECT bus_id, bus_number, capacity FROM Buses "
                  "WHERE route_id = %s ORDER BY bus_number", (route_id,))
    return render_template("route.html", route=route, buses=buses)


@app.route("/buses")
def buses_list():
    rows = query(
        "SELECT b.bus_id, b.bus_number, b.capacity, r.route_id, r.route_name,"
        "       r.start_point, r.end_point "
        "FROM Buses b JOIN Routes r ON r.route_id = b.route_id "
        "ORDER BY b.bus_number")
    return render_template("buses.html", buses=rows)


def get_bus(bus_id):
    return query(
        "SELECT b.bus_id, b.bus_number, b.capacity, r.route_id, r.route_name,"
        "       r.start_point, r.end_point "
        "FROM Buses b JOIN Routes r ON r.route_id = b.route_id "
        "WHERE b.bus_id = %s", (bus_id,), one=True)


def render_bus(bus, values, errors, status=200):
    today = date.today()
    html = render_template(
        "bus.html", bus=bus, values=values, errors=errors,
        today=today.isoformat(),
        last_day=(today + timedelta(days=config.MAX_DAYS_AHEAD)).isoformat())
    return html, status


@app.route("/bus/<int:bus_id>")
def bus_detail(bus_id):
    bus = get_bus(bus_id)
    if not bus:
        abort(404)
    return render_bus(bus, {}, [])


@app.route("/api/bus/<int:bus_id>/seats")
def api_seats(bus_id):
    """JSON used by the seat map: which seats are taken on a given date."""
    bus = query("SELECT capacity FROM Buses WHERE bus_id = %s", (bus_id,), one=True)
    if not bus:
        abort(404)
    try:
        day = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        return jsonify(error="Pick a valid date."), 400
    rows = query("SELECT seat_number FROM Tickets WHERE bus_id = %s AND travel_date = %s",
                 (bus_id, day))
    return jsonify(capacity=bus["capacity"], taken=[r["seat_number"] for r in rows])


BOOK_FIELDS = [
    {"name": "name", "label": "Name", "type": "text", "maxlen": 100},
    {"name": "email", "label": "Email", "type": "email", "maxlen": 100},
    {"name": "phone", "label": "Phone", "type": "phone"},
    {"name": "travel_date", "label": "Travel date", "type": "date"},
    {"name": "seat_number", "label": "Seat number", "type": "number", "maxval": 500},
]


@app.route("/bus/<int:bus_id>/book", methods=["POST"])
def book(bus_id):
    bus = get_bus(bus_id)
    if not bus:
        abort(404)

    v, errors = validate(BOOK_FIELDS, request.form)
    if not errors:
        today = date.today()
        if v["travel_date"] < today:
            errors.append("Travel date cannot be in the past.")
        elif v["travel_date"] > today + timedelta(days=config.MAX_DAYS_AHEAD):
            errors.append("Bookings open only %d days ahead." % config.MAX_DAYS_AHEAD)
        if v["seat_number"] > bus["capacity"]:
            errors.append("This bus has only %d seats." % bus["capacity"])
    if errors:
        return render_bus(bus, request.form, errors, 400)

    # Find or create the passenger, then insert the ticket, all in one transaction.
    db = get_db()
    ticket_id = pid = None
    try:
        with db.cursor() as cur:
            cur.execute("SELECT passenger_id, phone FROM Passengers WHERE email = %s",
                        (v["email"],))
            p = cur.fetchone()
            if p is None:
                cur.execute("INSERT INTO Passengers (name, email, phone) VALUES (%s, %s, %s)",
                            (v["name"], v["email"], v["phone"]))
                pid = cur.lastrowid
            elif p["phone"] == v["phone"]:
                pid = p["passenger_id"]
            else:
                errors.append("That email is already registered with a different phone number.")
            if pid is not None:
                cur.execute("INSERT INTO Tickets (passenger_id, bus_id, travel_date, seat_number) "
                            "VALUES (%s, %s, %s, %s)",
                            (pid, bus_id, v["travel_date"], v["seat_number"]))
                ticket_id = cur.lastrowid
        if errors:
            db.rollback()
        else:
            db.commit()
    except pymysql.err.IntegrityError as e:
        db.rollback()
        if e.args[0] == 1062:
            errors.append("That seat is already taken for this date. Please choose another.")
        else:
            errors.append(friendly(e))

    if errors:
        return render_bus(bus, request.form, errors, 400)

    session["pid"] = pid
    flash("Ticket #%d booked: seat %d on bus %s, %s."
          % (ticket_id, v["seat_number"], bus["bus_number"], v["travel_date"].isoformat()))
    return redirect(url_for("my_tickets"))


@app.route("/my-tickets", methods=["GET", "POST"])
def my_tickets():
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        phone = clean_phone((request.form.get("phone") or "").strip())
        p = query("SELECT passenger_id FROM Passengers WHERE email = %s AND phone = %s",
                  (email, phone), one=True)
        if p:
            session["pid"] = p["passenger_id"]
            return redirect(url_for("my_tickets"))
        error = "No passenger found with that email and phone number."

    passenger, tickets = None, []
    pid = session.get("pid")
    if pid:
        passenger = query("SELECT * FROM Passengers WHERE passenger_id = %s", (pid,), one=True)
        if passenger:
            tickets = query(
                "SELECT t.ticket_id, t.travel_date, t.seat_number, b.bus_id, b.bus_number,"
                "       r.route_name, r.start_point, r.end_point "
                "FROM Tickets t "
                "JOIN Buses b  ON b.bus_id = t.bus_id "
                "JOIN Routes r ON r.route_id = b.route_id "
                "WHERE t.passenger_id = %s "
                "ORDER BY t.travel_date DESC, t.ticket_id DESC", (pid,))
        else:
            session.pop("pid", None)
    return render_template("my_tickets.html", passenger=passenger, tickets=tickets,
                           today=date.today(), error=error)


@app.route("/ticket/<int:ticket_id>/cancel", methods=["POST"])
def cancel_ticket(ticket_id):
    pid = session.get("pid")
    if not pid:
        abort(403)
    t = query("SELECT travel_date FROM Tickets WHERE ticket_id = %s AND passenger_id = %s",
              (ticket_id, pid), one=True)
    if not t:
        abort(404)
    if t["travel_date"] < date.today():
        flash("Past tickets cannot be cancelled.", "error")
    else:
        execute("DELETE FROM Tickets WHERE ticket_id = %s", (ticket_id,))
        flash("Ticket #%d cancelled." % ticket_id)
    return redirect(url_for("my_tickets"))


@app.route("/my-tickets/forget", methods=["POST"])
def forget():
    session.pop("pid", None)
    return redirect(url_for("my_tickets"))


# --------------------------------------------------------------------------
# Admin side
# --------------------------------------------------------------------------
def col(name, label, num=False):
    return {"name": name, "label": label, "num": num}


# Every admin page is generated from this table, so adding a column in the
# database only needs one new line here.
TABLES = {
    "passengers": {
        "title": "Passengers", "table": "Passengers", "pk": "passenger_id",
        "fields": [
            {"name": "name", "label": "Name", "type": "text", "maxlen": 100},
            {"name": "email", "label": "Email", "type": "email", "maxlen": 100},
            {"name": "phone", "label": "Phone", "type": "phone"},
        ],
        "columns": [col("passenger_id", "ID", True), col("name", "Name"),
                    col("email", "Email"), col("phone", "Phone")],
        "sql": "SELECT passenger_id, name, email, phone FROM Passengers ORDER BY passenger_id",
    },
    "routes": {
        "title": "Routes", "table": "Routes", "pk": "route_id",
        "fields": [
            {"name": "route_name", "label": "Route name", "type": "text", "maxlen": 100},
            {"name": "start_point", "label": "Start point", "type": "text", "maxlen": 100},
            {"name": "end_point", "label": "End point", "type": "text", "maxlen": 100},
        ],
        "columns": [col("route_id", "ID", True), col("route_name", "Route"),
                    col("start_point", "From"), col("end_point", "To")],
        "sql": "SELECT route_id, route_name, start_point, end_point FROM Routes ORDER BY route_id",
    },
    "buses": {
        "title": "Buses", "table": "Buses", "pk": "bus_id",
        "fields": [
            {"name": "route_id", "label": "Route", "type": "select", "options": "routes"},
            {"name": "bus_number", "label": "Bus number", "type": "text", "maxlen": 20},
            {"name": "capacity", "label": "Capacity", "type": "number", "maxval": 500},
        ],
        "columns": [col("bus_id", "ID", True), col("bus_number", "Bus number"),
                    col("route_name", "Route"), col("capacity", "Capacity", True)],
        "sql": "SELECT b.bus_id, b.bus_number, r.route_name, b.capacity "
               "FROM Buses b JOIN Routes r ON r.route_id = b.route_id ORDER BY b.bus_id",
    },
    "tickets": {
        "title": "Tickets", "table": "Tickets", "pk": "ticket_id",
        "fields": [
            {"name": "passenger_id", "label": "Passenger", "type": "select", "options": "passengers"},
            {"name": "bus_id", "label": "Bus", "type": "select", "options": "buses"},
            {"name": "travel_date", "label": "Travel date", "type": "date"},
            {"name": "seat_number", "label": "Seat number", "type": "number", "maxval": 500},
        ],
        "columns": [col("ticket_id", "ID", True), col("name", "Passenger"),
                    col("bus_number", "Bus"), col("route_name", "Route"),
                    col("travel_date", "Date"), col("seat_number", "Seat", True)],
        "sql": "SELECT t.ticket_id, p.name, b.bus_number, r.route_name, t.travel_date, t.seat_number "
               "FROM Tickets t "
               "JOIN Passengers p ON p.passenger_id = t.passenger_id "
               "JOIN Buses b ON b.bus_id = t.bus_id "
               "JOIN Routes r ON r.route_id = b.route_id "
               "ORDER BY t.travel_date DESC, t.ticket_id DESC",
    },
}


def options_for(kind):
    """Dropdown choices for foreign-key fields."""
    if kind == "routes":
        sql = ("SELECT route_id AS id, CONCAT(route_name, ' (', start_point, ' to ', end_point, ')') "
               "AS label FROM Routes ORDER BY route_id")
    elif kind == "passengers":
        sql = ("SELECT passenger_id AS id, CONCAT(name, ' - ', email) AS label "
               "FROM Passengers ORDER BY name")
    else:  # buses
        sql = ("SELECT b.bus_id AS id, CONCAT(b.bus_number, ' - ', r.route_name) AS label "
               "FROM Buses b JOIN Routes r ON r.route_id = b.route_id ORDER BY b.bus_number")
    return query(sql)


def extra_checks(key, v, pk):
    """Rules that need the database, beyond simple field checks."""
    errs = []
    if key == "tickets":
        bus = query("SELECT capacity FROM Buses WHERE bus_id = %s", (v["bus_id"],), one=True)
        if bus and v["seat_number"] > bus["capacity"]:
            errs.append("Seat number exceeds that bus's capacity (%d)." % bus["capacity"])
    if key == "buses" and pk is not None:
        top = query("SELECT MAX(seat_number) AS m FROM Tickets WHERE bus_id = %s", (pk,), one=True)
        if top and top["m"] and v["capacity"] < top["m"]:
            errs.append("Capacity cannot be below seat %d, which is already booked." % top["m"])
    return errs


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


def same(a, b):
    return hmac.compare_digest(a.encode(), b.encode())


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if (same(request.form.get("username", ""), config.ADMIN_USER)
                and same(request.form.get("password", ""), config.ADMIN_PASSWORD)):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Wrong username or password."
    return render_template("admin/login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    counts = query(
        "SELECT (SELECT COUNT(*) FROM Passengers) AS passengers,"
        "       (SELECT COUNT(*) FROM Routes)     AS routes,"
        "       (SELECT COUNT(*) FROM Buses)      AS buses,"
        "       (SELECT COUNT(*) FROM Tickets)    AS tickets", one=True)
    load = query(
        "SELECT b.bus_id, b.bus_number, r.route_name, b.capacity, COUNT(t.ticket_id) AS booked "
        "FROM Buses b JOIN Routes r ON r.route_id = b.route_id "
        "LEFT JOIN Tickets t ON t.bus_id = b.bus_id AND t.travel_date >= %s "
        "GROUP BY b.bus_id, b.bus_number, r.route_name, b.capacity "
        "ORDER BY booked DESC, b.bus_number", (date.today(),))
    return render_template("admin/dashboard.html", counts=counts, load=load)


def get_cfg(key):
    cfg = TABLES.get(key)
    if cfg is None:
        abort(404)
    return cfg


@app.route("/admin/<key>")
@admin_required
def admin_list(key):
    cfg = get_cfg(key)
    return render_template("admin/list.html", cfg=cfg, key=key, rows=query(cfg["sql"]))


def handle_form(key, pk):
    cfg = get_cfg(key)
    row = None
    if pk is not None:
        row = query("SELECT * FROM %s WHERE %s = %%s" % (cfg["table"], cfg["pk"]), (pk,), one=True)
        if row is None:
            abort(404)

    values, errors = (row or {}), []
    if request.method == "POST":
        values = request.form
        clean, errors = validate(cfg["fields"], request.form)
        if not errors:
            errors = extra_checks(key, clean, pk)
        if not errors:
            names = [f["name"] for f in cfg["fields"]]
            args = [clean[n] for n in names]
            try:
                if pk is None:
                    execute("INSERT INTO %s (%s) VALUES (%s)"
                            % (cfg["table"], ", ".join(names), ", ".join(["%s"] * len(names))), args)
                    flash("Added to %s." % cfg["title"].lower())
                else:
                    execute("UPDATE %s SET %s WHERE %s = %%s"
                            % (cfg["table"], ", ".join(n + " = %s" for n in names), cfg["pk"]),
                            args + [pk])
                    flash("Row %d updated." % pk)
                return redirect(url_for("admin_list", key=key))
            except pymysql.err.IntegrityError as e:
                errors = [friendly(e)]

    options = {f["options"]: options_for(f["options"])
               for f in cfg["fields"] if f["type"] == "select"}
    return render_template("admin/form.html", cfg=cfg, key=key, pk=pk, values=values,
                           errors=errors, options=options), (400 if errors else 200)


@app.route("/admin/<key>/add", methods=["GET", "POST"])
@admin_required
def admin_add(key):
    return handle_form(key, None)


@app.route("/admin/<key>/<int:pk>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit(key, pk):
    return handle_form(key, pk)


@app.route("/admin/<key>/<int:pk>/delete", methods=["POST"])
@admin_required
def admin_delete(key, pk):
    cfg = get_cfg(key)
    try:
        execute("DELETE FROM %s WHERE %s = %%s" % (cfg["table"], cfg["pk"]), (pk,))
        flash("Row %d deleted." % pk)
    except pymysql.err.IntegrityError as e:
        flash(friendly(e), "error")
    return redirect(url_for("admin_list", key=key))


if __name__ == "__main__":
    app.run(debug=True)
