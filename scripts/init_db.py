"""Initialize SQLite schema and FTS adjunct objects (run from project root)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import init_db  # noqa: E402


def main() -> None:
    """Create application tables and FTS indexes if missing."""
    init_db()
    print("Database initialized OK.")


if __name__ == "__main__":
    main()
