# Public Transport System

A small DBMS project: **MySQL** database + **Python Flask** website.
Passengers browse routes and buses, pick a seat on a clickable seat map, and
book a ticket. An admin can add, edit and delete rows in every table.

## Folder layout

```
public_transport/
├── app.py               Flask app (all routes, validation, SQL)
├── config.py            DB host / user / password, admin login
├── setup_db.py          Optional: builds the database without the mysql command
├── requirements.txt     Flask, PyMySQL, cryptography
├── database/
│   ├── schema.sql       CREATE TABLE statements  (the core of the project)
│   ├── sample_data.sql  Demo rows (dates are relative to today)
│   └── queries.sql      Joins / GROUP BY examples for demos and viva
├── templates/           HTML pages (Jinja2); admin pages in templates/admin/
└── static/              style.css (about 100 lines) and app.js (small, vanilla)
```

## Database design

```
Routes (route_id PK, route_name, start_point, end_point)
   │ 1
   │
   │ many
Buses (bus_id PK, route_id FK, bus_number UNIQUE, capacity)
   │ 1
   │
   │ many
Tickets (ticket_id PK, passenger_id FK, bus_id FK, travel_date, seat_number)
   │ many
   │
   │ 1
Passengers (passenger_id PK, name, email UNIQUE, phone)
```

| Table | Key points |
|-------|-----------|
| Passengers | `email` is UNIQUE, so one person is one row. |
| Routes | A named path from `start_point` to `end_point`. |
| Buses | Belongs to one route (`route_id` FK). `bus_number` is UNIQUE, `capacity > 0`. |
| Tickets | `UNIQUE (bus_id, travel_date, seat_number)` makes it impossible to sell the same seat twice, even if two people click at the same moment. |

All foreign keys use `ON DELETE RESTRICT` (the MySQL default). A route that still
has buses, or a bus or passenger that still has tickets, cannot be deleted.
The admin pages show a clear message when this happens.

## Setup

You need Python 3.9+ and MySQL 8.0+ (MariaDB 10.5+ also works).

**1. Install the Python packages**

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

**2. Set your MySQL login** in `config.py` (the `password` line), or use
environment variables `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`.

**3. Create the database** (pick one way)

```bash
# A) with the mysql command
mysql -u root -p < database/schema.sql
mysql -u root -p < database/sample_data.sql

# B) without it (works anywhere Python works)
python setup_db.py          # schema + sample data, asks before dropping tables
python setup_db.py --empty  # schema only
```

Warning: both ways **drop and recreate** the four tables.

**4. Run the site**

```bash
python app.py
```

Open <http://127.0.0.1:5000>.

## Using the website

### Passenger side (no login)

| Page | What you can do |
|------|-----------------|
| Home | Search a stop or route name, see totals. |
| Routes | Live filter box, click a column title to sort, click a row to open the route. |
| Route page | See every bus on that route. |
| Buses | Same filter and sort; click a row to open the bus. |
| Bus page | Choose a date, then click a free seat on the seat map (taken seats are greyed out and update when the date changes). Enter name, email and phone, then book. |
| My tickets | Look up bookings with the email **and** phone used to book. Filter, sort, and cancel upcoming tickets. |

Booking rules: not in the past, at most 90 days ahead (change `MAX_DAYS_AHEAD`
in `config.py`), seat must exist on that bus. If the email already exists, the
phone number must match.

### Admin side

Go to **Admin login** in the top bar (or `/admin`).

- Default login: **admin / admin123** (change it in `config.py`)
- Dashboard: record counts and upcoming bookings per bus (a GROUP BY report)
- Passengers, Routes, Buses, Tickets: **Add**, **Edit**, **Delete**, plus filter and sort
- Dropdowns for foreign keys (for example, choosing the route for a bus)
- Extra checks: seat number must fit the bus, capacity cannot drop below an
  already booked seat, duplicates are reported in plain words

## How the pieces connect

- `app.py` opens one PyMySQL connection per request and runs plain SQL with `%s` placeholders (safe against SQL injection).
- The admin pages come from one table in `app.py` (`TABLES`) that lists each table's fields and columns. Adding a column to the database means adding one line there.
- The seat map calls `/api/bus/<id>/seats?date=YYYY-MM-DD`, which returns the taken seats as JSON.
- Every form carries a CSRF token. Admin pages need the session login.

## Try the SQL directly

`database/queries.sql` has ready-made queries: a four-table join, seats free per
bus, buses per route (LEFT JOIN), passengers ranked by tickets, busiest route,
and a commented-out double-booking test that fails with error 1062.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot use the database" page | MySQL not running, wrong password in `config.py`, or `schema.sql` not imported yet. |
| `Access denied for user` | Check `user` / `password` in `config.py`. |
| `cryptography package is required` | Run `pip install -r requirements.txt` again. |
| `mysql` is not recognised (Windows) | Use `python setup_db.py` instead. |
| Port 5000 busy (macOS) | Run `flask --app app run --port 5001`. |

## Notes and limits

- Built for learning and demos. Before putting it on a real server, set a strong `SECRET_KEY` and admin password, and run it with a production server (not `debug=True`).
- Passengers have no passwords: "my tickets" is protected by email plus phone only.
- The schema has no departure times or prices because the brief fixed the four tables. They would be natural next columns.
