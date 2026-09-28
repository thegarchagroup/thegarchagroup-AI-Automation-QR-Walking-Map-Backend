"""
Run once to populate the database from the guide's existing content
(seed_content.json, generated from the frontend's original data.js).

Usage (from the backend/ directory, with the virtualenv active):
    python -m scripts.seed_places
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal
from app.models import Place

SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "seed_content.json"


def main():
    Base.metadata.create_all(bind=engine)
    seed = json.loads(SEED_PATH.read_text())

    db = SessionLocal()
    try:
        existing = db.query(Place).count()
        if existing > 0:
            answer = input(
                f"{existing} place(s) already in the database. Wipe and reseed? [y/N] "
            )
            if answer.strip().lower() != "y":
                print("Cancelled — no changes made.")
                return
            db.query(Place).delete()

        count = 0
        for category, stops in seed["DATA"].items():
            for stop in stops:
                place = Place(
                    id=stop["id"],
                    category=category,
                    n=stop.get("n"),
                    name=stop["name"],
                    blurb=stop.get("blurb"),
                    address=stop.get("address"),
                    address_label=stop.get("addressLabel"),
                    hours=stop.get("hours"),
                    phone=stop.get("phone"),
                    website=stop.get("website"),
                    walk_time=stop.get("walkTime"),
                    image=stop.get("image"),
                    lat=stop.get("lat"),
                    lng=stop.get("lng"),
                    map_url=stop.get("map"),
                )
                db.add(place)
                count += 1
        db.commit()
        print(f"Seeded {count} places.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
