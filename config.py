"""Settings. Edit the defaults here, or set environment variables instead."""
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Madhav@21"),      # <-- your MySQL password
    "database": os.environ.get("DB_NAME", "public_transport"),
    "charset": "utf8mb4",
}

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-before-sharing")

# Admin login for the /admin pages
ADMIN_USER = os.environ.get("ADMIN_USER", "root")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Madhav@21")

# Passengers may book at most this many days ahead
MAX_DAYS_AHEAD = 90
