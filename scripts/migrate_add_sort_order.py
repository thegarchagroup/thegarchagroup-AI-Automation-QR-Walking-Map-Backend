"""
One-time migration for databases created before `sort_order` existed.

Safe to run more than once — it skips the ALTER TABLE if the column
already exists, and backfilling only touches rows where sort_order is
still NULL.

Usage (from the backend/ directory, with the virtualenv active):
    python -m scripts.migrate_add_sort_order
"""
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import Place


def add_column_if_missing():
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(places)"))]
        if "sort_order" in cols:
            print("sort_order column already exists — skipping ALTER TABLE.")
            return
        conn.execute(text("ALTER TABLE places ADD COLUMN sort_order INTEGER"))
        conn.commit()
        print("Added sort_order column.")


def backfill_sort_order():
    db = SessionLocal()
    try:
        categories = [row[0] for row in db.query(Place.category).distinct().all()]
        total_updated = 0

        for category in categories:
            places = db.query(Place).filter(Place.category == category).all()

            # Prefer the numeric value of `n` where it parses cleanly
            # (matches the original document's intended sequence);
            # anything else (letters, blank, already-custom entries)
            # falls back to the end, ordered by creation id so it's at
            # least stable and doesn't reshuffle on every run.
            def sort_key(place):
                if place.n and re.fullmatch(r"\d+", place.n.strip()):
                    return (0, int(place.n))
                return (1, place.id)

            places.sort(key=sort_key)

            for i, place in enumerate(places):
                if place.sort_order is None:
                    place.sort_order = i
                    total_updated += 1

        db.commit()
        print(f"Backfilled sort_order for {total_updated} place(s) across {len(categories)} categor(y/ies).")
    finally:
        db.close()


if __name__ == "__main__":
    add_column_if_missing()
    backfill_sort_order()