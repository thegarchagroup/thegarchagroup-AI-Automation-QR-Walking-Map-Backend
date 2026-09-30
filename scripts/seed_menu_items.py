"""
Creates the menu_items table (if it doesn't exist) and seeds it with the
6 home-screen sections, in their current order, using the same
label/tagline text that used to live in seed_content.json's MENU array.

Safe to run more than once — it only inserts rows that don't already
exist (matched by `key`), so re-running won't overwrite any renaming or
reordering you've already done through the content editor.

Usage (from the backend/ directory, with the virtualenv active):
    python -m scripts.seed_menu_items
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal
from app.models import MenuItem

DEFAULT_MENU = [
    {"key": "map", "label": "Neighborhood Map", "tagline": "See it all at a glance", "sort_order": 0},
    {"key": "see", "label": "Worth the Detour", "tagline": "15 places worth wandering over to", "sort_order": 1},
    {"key": "do", "label": "Do More Than Look", "tagline": "10 experiences worth getting involved in", "sort_order": 2},
    {"key": "eat", "label": "Walk. Eat. Repeat.", "tagline": "15 good reasons to arrive hungry", "sort_order": 3},
    {
        "key": "drive",
        "label": "Worth the Drive",
        "tagline": "Four more Garcha Group dining experiences worth crossing town for, with your exclusive F&B discount card received at check-in.",
        "sort_order": 4,
    },
    {"key": "running", "label": "Running Map", "tagline": "A scenic route through the neighborhood.", "sort_order": 5},
]


def main():
    Base.metadata.create_all(bind=engine)  # creates menu_items table if missing

    db = SessionLocal()
    try:
        existing_keys = {row.key for row in db.query(MenuItem.key).all()}
        inserted = 0
        for item in DEFAULT_MENU:
            if item["key"] in existing_keys:
                continue
            db.add(MenuItem(**item))
            inserted += 1
        db.commit()
        print(f"Inserted {inserted} menu item(s); {len(existing_keys)} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    main()