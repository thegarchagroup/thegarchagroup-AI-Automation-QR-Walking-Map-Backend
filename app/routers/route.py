from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import routing
from ..database import get_db
from ..models import RouteConfig, User
from ..schemas import RouteOut, RouteUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/route", tags=["route"])

# The loop staff asked for (about 5.3 km on Google Maps walking directions).
# It's a closed loop: after the last stop you return to the first. Used
# until someone saves a route in the content editor, so a fresh database
# works without any seed step.
DEFAULT_ROUTE = {
    "subtitle": (
        "A scenic ~5 km heritage loop connecting both hotels with Little "
        "India and Kampong Gelam"
    ),
    "distance_label": "~5 km",
    "safety_note": (
        "Suggested route only. Please observe traffic conditions and use "
        "designated pedestrian crossings."
    ),
    "stops": [
        {"name": "The Vagabond Club", "lat": 1.3070654, "lng": 103.8582723, "is_start": True},
        {"name": "The Serangoon House", "lat": 1.3113979, "lng": 103.8548037, "is_start": True},
        {"name": "Sri Veeramakaliamman Temple", "lat": 1.3078878, "lng": 103.85248, "is_start": False},
        {"name": "Former House of Tan Teng Niah", "lat": 1.3070541, "lng": 103.8509602, "is_start": False},
        {"name": "Tekka Centre", "lat": 1.30622, "lng": 103.85053, "is_start": False},
        {"name": "Indian Heritage Centre", "lat": 1.3056816, "lng": 103.8522606, "is_start": False},
        {"name": "National Design Centre", "lat": 1.2986691, "lng": 103.8533635, "is_start": False},
        {"name": "Haji Lane", "lat": 1.3007065, "lng": 103.8591356, "is_start": False},
        {"name": "Sultan Mosque", "lat": 1.3022854, "lng": 103.8589636, "is_start": False},
    ],
}


def _out(row, message=None) -> dict:
    """Shape a stored row (or the built-in default, if there is none yet)."""
    if row is None:
        return {
            **DEFAULT_ROUTE,
            "geometry": None,
            "computed_km": None,
            "routing_status": None,
            "routing_provider": None,
            "routing_message": message,
        }
    return {
        "subtitle": row.subtitle,
        "distance_label": row.distance_label,
        "safety_note": row.safety_note,
        "stops": row.stops,
        "geometry": row.geometry,
        "computed_km": row.computed_km,
        "routing_status": row.routing_status,
        "routing_provider": row.routing_provider,
        "routing_message": message,
    }


def _get_or_create(db: Session) -> RouteConfig:
    row = db.get(RouteConfig, 1)
    if row is None:
        row = RouteConfig(
            id=1,
            subtitle=DEFAULT_ROUTE["subtitle"],
            distance_label=DEFAULT_ROUTE["distance_label"],
            safety_note=DEFAULT_ROUTE["safety_note"],
            stops=[dict(s) for s in DEFAULT_ROUTE["stops"]],
        )
        db.add(row)
        db.flush()
    return row


def _signature(stops) -> list[tuple[float, float]]:
    """What matters for the walking line is only where the stops are and in
    what order — renaming a stop must not trigger a (slow, rate-limited)
    routing call."""
    return [(round(float(s["lat"]), 6), round(float(s["lng"]), 6)) for s in stops]


def _recompute(row: RouteConfig) -> str:
    """Compute and store the real walking line. Never raises: if no routing
    service can be reached, store straight lines and say so."""
    points = [(float(s["lat"]), float(s["lng"])) for s in row.stops]
    result, problems = routing.compute_walking_loop(points)

    if result is not None:
        row.geometry = result.geometry
        row.computed_km = round(result.distance_km, 2)
        row.routing_status = "ok"
        row.routing_provider = result.provider
        message = (
            f"Route line updated: {row.computed_km} km along real walking paths "
            f"({result.provider})."
        )
        if problems:
            message += " The first routing service failed, so a backup was used."
        return message

    row.geometry = routing.straight_line_geometry(points)
    row.computed_km = None
    row.routing_status = "fallback"
    row.routing_provider = None
    return (
        "Saved, but no walking-route service could be reached, so the map is "
        "showing straight lines between stops for now. Use \"Recalculate route "
        "line\" to try again. (" + "; ".join(problems) + ")"
    )


@router.get("", response_model=RouteOut)
def get_route(db: Session = Depends(get_db)):
    """Public — the Running Map page reads everything it shows from here."""
    return _out(db.get(RouteConfig, 1))


@router.put("", response_model=RouteOut)
def update_route(
    payload: RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    row = _get_or_create(db)
    data = payload.model_dump(exclude_unset=True)
    stops_before = _signature(row.stops)

    for field in ("subtitle", "distance_label", "safety_note"):
        if data.get(field) is not None:
            setattr(row, field, data[field])
    if data.get("stops") is not None:
        row.stops = [dict(s) for s in data["stops"]]

    # Only call a routing service when the line actually needs redrawing.
    message = None
    if row.geometry is None or _signature(row.stops) != stops_before:
        message = _recompute(row)

    db.commit()
    db.refresh(row)
    return _out(row, message)


@router.post("/recompute", response_model=RouteOut)
def recompute_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # login required
):
    """Redraw the walking line from the saved stops (e.g. to retry after a
    routing service was unreachable)."""
    row = _get_or_create(db)
    message = _recompute(row)
    db.commit()
    db.refresh(row)
    return _out(row, message)
