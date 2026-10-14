import json

import httpx
import pytest

from app import routing
from app.routing import (
    RoutingError, compute_walking_loop, decode_polyline, route_with_osrm,
    route_with_valhalla, straight_line_geometry, tidy,
)

STOPS = [(1.3070654, 103.8582723), (1.3113979, 103.8548037), (1.3078878, 103.85248)]


def encode_polyline(points, precision=6):
    """Test-only encoder, used to build realistic Valhalla 'shape' strings."""
    factor = 10**precision
    out, prev_lat, prev_lng = [], 0, 0
    for lat, lng in points:
        for cur, prev in ((round(lat * factor), prev_lat), (round(lng * factor), prev_lng)):
            d = cur - prev
            d = ~(d << 1) if d < 0 else d << 1
            while d >= 0x20:
                out.append(chr((0x20 | (d & 0x1F)) + 63))
                d >>= 5
            out.append(chr(d + 63))
        prev_lat, prev_lng = round(lat * factor), round(lng * factor)
    return "".join(out)


def mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---- decoding / cleaning ---------------------------------------------------

def test_decode_known_google_example():
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5)
    assert pts == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_encode_decode_roundtrip_precision6():
    pts = [(1.307065, 103.858272), (1.311398, 103.854804), (1.307888, 103.85248)]
    assert decode_polyline(encode_polyline(pts), 6) == pytest.approx(pts)


def test_tidy_rounds_and_drops_consecutive_duplicates():
    assert tidy([(1.1234561, 2.0), (1.1234559, 2.0), (1.5, 2.5)]) == [[1.12346, 2.0], [1.5, 2.5]]


def test_straight_line_geometry_closes_the_loop():
    g = straight_line_geometry(STOPS)
    assert len(g) == len(STOPS) + 1 and g[0] == g[-1]


# ---- OSRM -------------------------------------------------------------------

def osrm_ok(request):
    return httpx.Response(200, json={
        "code": "Ok",
        "routes": [{
            "distance": 5312.4,
            # GeoJSON order is [lng, lat]
            "geometry": {"coordinates": [[103.8582, 1.3070], [103.8570, 1.3080], [103.8548, 1.3114]]},
        }],
    })


def test_osrm_parses_geojson_and_swaps_to_lat_lng():
    r = route_with_osrm(routing.closed_loop(STOPS), mock_client(osrm_ok))
    assert r.geometry == [[1.307, 103.8582], [1.308, 103.857], [1.3114, 103.8548]]
    assert r.distance_km == pytest.approx(5.3124)
    assert "OSRM" in r.provider


def test_osrm_request_shape():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return osrm_ok(request)

    route_with_osrm(routing.closed_loop(STOPS), mock_client(handler))
    url = seen["url"]
    assert "routed-foot" in url                       # walking profile instance
    assert "overview=full" in url and "geometries=geojson" in url
    coords = url.split("/driving/")[1].split("?")[0].split(";")
    assert coords[0] == "103.8582723,1.3070654"       # lng,lat order
    assert len(coords) == len(STOPS) + 1 and coords[0] == coords[-1]  # closed loop


def test_osrm_no_route_is_an_error():
    c = mock_client(lambda r: httpx.Response(200, json={"code": "NoRoute", "message": "nope"}))
    with pytest.raises(RoutingError):
        route_with_osrm(routing.closed_loop(STOPS), c)


# ---- Valhalla -----------------------------------------------------------------

def valhalla_ok(request):
    leg1 = encode_polyline([(1.3070, 103.8582), (1.3080, 103.8570)])
    leg2 = encode_polyline([(1.3080, 103.8570), (1.3114, 103.8548)])  # starts where leg1 ended
    return httpx.Response(200, json={"trip": {
        "status": 0,
        "summary": {"length": 5.27},
        "legs": [{"shape": leg1}, {"shape": leg2}],
    }})


def test_valhalla_merges_legs_without_repeating_joints():
    r = route_with_valhalla(routing.closed_loop(STOPS), mock_client(valhalla_ok))
    assert r.geometry == [[1.307, 103.8582], [1.308, 103.857], [1.3114, 103.8548]]
    assert r.distance_km == 5.27


def test_valhalla_request_is_pedestrian_with_break_points():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return valhalla_ok(request)

    route_with_valhalla(routing.closed_loop(STOPS), mock_client(handler))
    body = seen["body"]
    assert body["costing"] == "pedestrian"
    assert all(loc["type"] == "break" for loc in body["locations"])
    assert body["locations"][0] == body["locations"][-1]
    assert body["directions_options"]["units"] == "kilometers"


# ---- fallback chain --------------------------------------------------------------

def test_first_provider_works_no_problems():
    result, problems = compute_walking_loop(STOPS, client=mock_client(osrm_ok))
    assert result and "OSRM" in result.provider and problems == []


def test_falls_back_to_valhalla_when_osrm_is_down():
    def handler(request):
        if "valhalla" in str(request.url):
            return valhalla_ok(request)
        return httpx.Response(503, text="busy")

    result, problems = compute_walking_loop(STOPS, client=mock_client(handler))
    assert result and "Valhalla" in result.provider
    assert len(problems) == 1 and problems[0].startswith("OSRM")


def test_falls_back_when_osrm_says_no_route():
    def handler(request):
        if "valhalla" in str(request.url):
            return valhalla_ok(request)
        return httpx.Response(200, json={"code": "NoRoute"})

    result, _ = compute_walking_loop(STOPS, client=mock_client(handler))
    assert result and "Valhalla" in result.provider


def test_everything_down_returns_none_with_a_reason_per_provider():
    result, problems = compute_walking_loop(STOPS, client=mock_client(lambda r: httpx.Response(500)))
    assert result is None and len(problems) == 2


def test_network_error_and_garbage_are_handled_not_raised():
    def handler(request):
        if "valhalla" in str(request.url):
            return httpx.Response(200, json={"trip": {"status": 0, "summary": {"length": 1}, "legs": [{"shape": "_p~iF~ps|U_ulLnnq"}]}})  # truncated polyline
        raise httpx.ConnectError("no route to host")

    result, problems = compute_walking_loop(STOPS, client=mock_client(handler))
    assert result is None or result.geometry  # must not raise either way
    assert len(problems) >= 1
