import pytest

from app import routing
from app.routing import RoutedLoop


@pytest.fixture()
def routed(monkeypatch):
    """Replace the real routing call and count how often it's made."""
    calls = []

    def fake(stops, client=None):
        calls.append(list(stops))
        line = [[a, b] for a, b in stops] + [list(stops[0])]
        return RoutedLoop(geometry=line, distance_km=5.3, provider="FakeRouter"), []

    monkeypatch.setattr(routing, "compute_walking_loop", fake)
    return calls


# ---------------------------------------------------------------- settings --

def test_settings_default_to_the_clients_copy(client):
    s = client.get("/settings").json()
    assert s["home_title"] == "Little India &\nKampong Gelam"
    assert "Kampong Glam" not in s["home_title"] + s["home_intro"]
    assert s["home_intro"].startswith("A walking guide to Singapore's Little India and Kampong Gelam, from the")
    assert s["home_intro"].endswith("a few Garcha Group favorites worth the trip.")


def test_settings_edit_requires_login(client):
    assert client.put("/settings", json={"home_title": "x"}).status_code == 401


def test_settings_edit_persists_and_is_partial(client, auth):
    r = client.put("/settings", json={"home_title": "  New title  "}, headers=auth)
    assert r.status_code == 200 and r.json()["home_title"] == "New title"
    again = client.get("/settings").json()                 # public read sees it
    assert again["home_title"] == "New title"
    assert again["home_intro"].startswith("A walking guide")  # untouched key keeps its default


def test_settings_reject_blank_and_ignore_unknown(client, auth):
    assert client.put("/settings", json={"home_title": "   "}, headers=auth).status_code == 422
    r = client.put("/settings", json={"hack": "x"}, headers=auth)
    assert r.status_code == 200 and "hack" not in r.json()


# ------------------------------------------------------------------- route --

def test_default_route_is_the_clients_new_loop(client):
    r = client.get("/route").json()
    names = [s["name"] for s in r["stops"]]
    assert names == [
        "The Vagabond Club", "The Serangoon House", "Sri Veeramakaliamman Temple",
        "Former House of Tan Teng Niah", "Tekka Centre", "Indian Heritage Centre",
        "National Design Centre", "Haji Lane", "Sultan Mosque",
    ]
    assert "Kallang" not in " ".join(names)
    assert [s["is_start"] for s in r["stops"]][:2] == [True, True]
    assert r["subtitle"] == "A scenic ~5 km heritage loop connecting both hotels with Little India and Kampong Gelam"
    assert r["distance_label"] == "~5 km"
    assert r["geometry"] is None


def test_route_edit_requires_login(client):
    assert client.put("/route", json={"subtitle": "x"}).status_code == 401
    assert client.post("/route/recompute").status_code == 401


def test_first_save_draws_the_line(client, auth, routed):
    r = client.put("/route", json={"distance_label": "~6 km"}, headers=auth).json()
    assert r["distance_label"] == "~6 km"
    assert r["routing_status"] == "ok" and r["computed_km"] == 5.3
    assert r["routing_provider"] == "FakeRouter" and "5.3 km" in r["routing_message"]
    assert len(r["geometry"]) == 10 and len(routed) == 1   # 9 stops + closing point


def test_text_only_and_rename_do_not_call_the_router(client, auth, routed):
    client.put("/route", json={"subtitle": "first"}, headers=auth)      # draws once
    assert len(routed) == 1
    r = client.put("/route", json={"subtitle": "second", "safety_note": "be careful"}, headers=auth).json()
    assert r["subtitle"] == "second" and r["safety_note"] == "be careful"
    assert r["routing_message"] is None and len(routed) == 1            # no new call

    stops = client.get("/route").json()["stops"]
    stops[0]["name"] = "Renamed hotel"                                  # same place, new label
    client.put("/route", json={"stops": stops}, headers=auth)
    assert len(routed) == 1


def test_moving_or_reordering_stops_redraws(client, auth, routed):
    client.put("/route", json={"subtitle": "x"}, headers=auth)
    stops = client.get("/route").json()["stops"]

    moved = [dict(s) for s in stops]
    moved[4]["lat"] += 0.001
    client.put("/route", json={"stops": moved}, headers=auth)
    assert len(routed) == 2

    swapped = [dict(s) for s in moved]
    swapped[2], swapped[3] = swapped[3], swapped[2]
    client.put("/route", json={"stops": swapped}, headers=auth)
    assert len(routed) == 3

    added = swapped + [{"name": "New stop", "lat": 1.30, "lng": 103.85, "is_start": False}]
    r = client.put("/route", json={"stops": added}, headers=auth).json()
    assert len(routed) == 4 and len(r["stops"]) == 10


@pytest.mark.parametrize("bad", [
    [{"name": "Only one", "lat": 1.3, "lng": 103.8}],                                   # < 2 stops
    [{"name": "A", "lat": 1.3, "lng": 103.8}, {"name": "B", "lat": 99, "lng": 103.8}],  # latitude out of range
    [{"name": "A", "lat": 1.3, "lng": 103.8}, {"name": "B", "lat": 1.3, "lng": 999}],   # longitude out of range
    [{"name": "A", "lat": 1.3, "lng": 103.8}, {"name": "  ", "lat": 1.3, "lng": 103.9}],  # blank name
    [{"name": f"S{i}", "lat": 1.3, "lng": 103.8 + i / 1000} for i in range(21)],        # too many
])
def test_route_rejects_bad_stops(client, auth, routed, bad):
    assert client.put("/route", json={"stops": bad}, headers=auth).status_code == 422
    assert routed == []


def test_outage_saves_anyway_with_straight_lines_and_says_so(client, auth, monkeypatch):
    monkeypatch.setattr(routing, "compute_walking_loop", lambda stops, client=None: (None, ["OSRM: down", "Valhalla: down"]))
    r = client.put("/route", json={"subtitle": "still saves"}, headers=auth).json()
    assert r["subtitle"] == "still saves"
    assert r["routing_status"] == "fallback" and r["computed_km"] is None
    assert len(r["geometry"]) == 10                       # straight segments, closed
    assert "Recalculate route line" in r["routing_message"] and "OSRM: down" in r["routing_message"]


def test_recompute_recovers_after_an_outage(client, auth, monkeypatch):
    monkeypatch.setattr(routing, "compute_walking_loop", lambda stops, client=None: (None, ["down"]))
    client.put("/route", json={"subtitle": "x"}, headers=auth)
    assert client.get("/route").json()["routing_status"] == "fallback"

    monkeypatch.setattr(routing, "compute_walking_loop",
                        lambda stops, client=None: (RoutedLoop([[1.0, 2.0], [1.1, 2.1]], 5.2, "Back online"), []))
    r = client.post("/route/recompute", headers=auth).json()
    assert r["routing_status"] == "ok" and r["computed_km"] == 5.2 and r["routing_provider"] == "Back online"


def test_public_read_never_calls_the_router(client, routed):
    client.get("/route"); client.get("/route")
    assert routed == []
