"""
Stores the default Running Map route (if none is saved yet) and draws its
real walking line.

Optional — the site works without it, because a missing route just means
"use the built-in default". Run it once after deploying because it also
tells you straight away whether the server can reach a walking-route
service: it prints the distance it computed, or the reason it couldn't.

Safe to re-run: it never overwrites stops/text someone has already edited
in the content editor; with --force-redraw it only redraws the line.

Usage (from the backend/ directory, with the virtualenv active):
    python -m scripts.seed_route
    python -m scripts.seed_route --force-redraw
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal
from app.models import RouteConfig
from app.routers.route import _get_or_create, _recompute


def main():
    force = "--force-redraw" in sys.argv
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existed = db.get(RouteConfig, 1) is not None
        row = _get_or_create(db)
        print(f"Route: {'already saved' if existed else 'created from the built-in default'}; "
              f"{len(row.stops)} stops.")
        if row.geometry is None or force:
            print("Drawing the walking line (asks a public routing service, up to ~30s)...")
            print(_recompute(row))
        else:
            print("Walking line already stored — nothing to do (use --force-redraw to redraw).")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
