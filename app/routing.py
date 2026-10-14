"""
Walking-route computation for the Running Map.

Given the ordered stops of a loop, ask a routing service for the real
street-and-footpath line that connects them (instead of the straight
lines the map used to draw through buildings and across the river).

This only runs when staff save a route in the content editor (or press
"Recalculate route line") — never when a guest opens the page. The result
is stored in the database and simply drawn by the frontend.

Two free, key-less public services are tried in order, so one being down
doesn't break anything:

  1. The OpenStreetMap community's OSRM instance with the walking
     profile (routing.openstreetmap.de/routed-foot).
  2. The OpenStreetMap community's Valhalla instance, "pedestrian"
     costing (valhalla1.openstreetmap.de).

Both are fair-use demo servers — fine for the handful of calls an editor
makes, not for per-guest traffic (which is why we store the result).
If both fail, the caller falls back to straight lines and says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence

import httpx

OSRM_FOOT_BASE = "https://routing.openstreetmap.de/routed-foot/route/v1/driving"
VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"
TIMEOUT_SECONDS = 15.0
# OSM's usage policies ask API clients to identify themselves.
USER_AGENT = "WalkGuide/1.0 (Garcha Group walking guide; editor-triggered route builds)"

Point = tuple[float, float]  # (lat, lng)


class RoutingError(Exception):
    """A provider answered, but not with a usable route."""


@dataclass
class RoutedLoop:
    geometry: list[list[float]]  # [[lat, lng], ...] following real streets
    distance_km: float
    provider: str


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def decode_polyline(encoded: str, precision: int = 6) -> list[Point]:
    """Decode a Google-style encoded polyline (Valhalla uses 6 decimals)."""
    factor = 10**precision
    index = lat = lng = 0
    points: list[Point] = []
    while index < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63  # IndexError here => truncated string
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lng += delta
        points.append((lat / factor, lng / factor))
    return points


def tidy(points: Iterable[Point]) -> list[list[float]]:
    """Round to ~1 m (5 decimals) and drop consecutive duplicates, so the
    stored line is compact without visibly changing shape."""
    out: list[list[float]] = []
    for lat, lng in points:
        pt = [round(lat, 5), round(lng, 5)]
        if not out or out[-1] != pt:
            out.append(pt)
    return out


def closed_loop(stops: Sequence[Point]) -> list[Point]:
    """The route is a loop: after the last stop, return to the first."""
    return list(stops) + [stops[0]]


def straight_line_geometry(stops: Sequence[Point]) -> list[list[float]]:
    """Last-resort geometry: straight segments between stops, closed."""
    return tidy(closed_loop(stops))


# --------------------------------------------------------------------------
# providers
# --------------------------------------------------------------------------

def route_with_osrm(points: Sequence[Point], client: httpx.Client) -> RoutedLoop:
    coords = ";".join(f"{lng},{lat}" for lat, lng in points)
    resp = client.get(
        f"{OSRM_FOOT_BASE}/{coords}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError(f"OSRM said {data.get('code')}: {data.get('message', 'no route')}")
    route = data["routes"][0]
    geometry = tidy((lat, lng) for lng, lat in route["geometry"]["coordinates"])
    if len(geometry) < 2:
        raise RoutingError("OSRM returned an empty line")
    return RoutedLoop(geometry, float(route["distance"]) / 1000.0, "OSRM (OpenStreetMap, walking)")


def route_with_valhalla(points: Sequence[Point], client: httpx.Client) -> RoutedLoop:
    body = {
        "locations": [{"lat": lat, "lon": lng, "type": "break"} for lat, lng in points],
        "costing": "pedestrian",
        "directions_options": {"units": "kilometers"},
    }
    resp = client.post(VALHALLA_URL, json=body)
    resp.raise_for_status()
    trip = resp.json()["trip"]
    if trip.get("status", 0) != 0:
        raise RoutingError(f"Valhalla said: {trip.get('status_message', 'no route')}")

    merged: list[Point] = []
    for leg in trip["legs"]:
        decoded = decode_polyline(leg["shape"], precision=6)
        # each leg starts where the previous one ended — don't repeat that point
        if merged and decoded and merged[-1] == decoded[0]:
            decoded = decoded[1:]
        merged.extend(decoded)
    geometry = tidy(merged)
    if len(geometry) < 2:
        raise RoutingError("Valhalla returned an empty line")
    return RoutedLoop(geometry, float(trip["summary"]["length"]), "Valhalla (OpenStreetMap, pedestrian)")


Provider = Callable[[Sequence[Point], httpx.Client], RoutedLoop]
PROVIDERS: list[tuple[str, Provider]] = [
    ("OSRM", route_with_osrm),
    ("Valhalla", route_with_valhalla),
]


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def compute_walking_loop(
    stops: Sequence[Point], client: Optional[httpx.Client] = None
) -> tuple[Optional[RoutedLoop], list[str]]:
    """
    Returns (result, problems). `result` is None if every provider failed;
    `problems` lists what went wrong with each one that was tried (empty on
    a first-try success), so the editor can show something useful.
    """
    points = closed_loop(stops)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})

    problems: list[str] = []
    try:
        for name, provider in PROVIDERS:
            try:
                return provider(points, client), problems
            except (httpx.HTTPError, RoutingError, KeyError, IndexError, TypeError, ValueError) as exc:
                problems.append(f"{name}: {type(exc).__name__}: {exc}")
        return None, problems
    finally:
        if own_client:
            client.close()
