"""Create the database from the .sql files without needing the `mysql` command.

    python setup_db.py            # schema + sample data (asks first)
    python setup_db.py --empty    # schema only, no sample data
    python setup_db.py --yes      # skip the confirmation question

WARNING: this drops and recreates the four tables.
"""
import sys
from pathlib import Path

import pymysql

import config

HERE = Path(__file__).parent / "database"


def run_file(cur, path):
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            cur.execute(statement)


def main():
    args = sys.argv[1:]
    if "--yes" not in args:
        answer = input("This DROPS and recreates the Passengers, Routes, Buses and "
                       "Tickets tables. Continue? [y/N] ")
        if answer.strip().lower() != "y":
            print("Cancelled.")
            return

    settings = {k: v for k, v in config.DB_CONFIG.items() if k != "database"}
    conn = pymysql.connect(**settings, autocommit=True)
    with conn.cursor() as cur:
        run_file(cur, HERE / "schema.sql")
        print("Schema created.")
        if "--empty" not in args:
            run_file(cur, HERE / "sample_data.sql")
            print("Sample data loaded.")
    conn.close()
    print("Done. Start the site with:  python app.py")


if __name__ == "__main__":
    main()
