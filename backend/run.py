"""Backend entry point.

Usage:
    python run.py            # start the dev server (port 5000)
    python run.py init-db    # create all tables (idempotent)
"""
import os
import sys

import config
from app import app
from app.extensions import db
import models  # noqa: F401  (ensure all tables are registered)


def init_db():
    with app.app_context():
        db.create_all()
        print(f"Database ready: {config.DATABASE_URL}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init-db":
        init_db()
        sys.exit(0)
    raw_port = os.environ.get("PORT", "5000")
    port = int(raw_port) if raw_port not in ("", "0") else 5000
    app.run(host="127.0.0.1", port=port, debug=False)