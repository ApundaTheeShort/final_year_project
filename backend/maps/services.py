import json
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class MapServiceError(Exception):
    pass


def _fallback_distance(lat1, lon1, lat2, lon2):
    radius_km = 6371
    delta_lat = radians(float(lat2) - float(lat1))
    delta_lon = radians(float(lon2) - float(lon1))
    lat1 = radians(float(lat1))
    lat2 = radians(float(lat2))
    arc = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return Decimal(str(2 * radius_km * asin(sqrt(arc)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _load_json(url, params):
    query = urlencode(params)
    request = Request(
        f"{url}?{query}",
        headers={"User-Agent": settings.MAPS_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=settings.MAPS_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise MapServiceError("Map provider request failed.") from exc


def search_places(query, limit=5):
    payload = _load_json(
        settings.NOMINATIM_SEARCH_URL,
        {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": limit,
        },
    )
    return [
        {
            "place_id": str(item.get("place_id", "")),
            "source": "nominatim",
            "osm_type": item.get("osm_type", "").upper()[:1],
            "osm_id": str(item.get("osm_id", "")),
            "name": item.get("name") or item.get("display_name", ""),
            "address": item.get("display_name", ""),
            "latitude": item.get("lat"),
            "longitude": item.get("lon"),
        }
        for item in payload
    ]


def lookup_place(osm_type, osm_id):
    payload = _load_json(
        settings.NOMINATIM_LOOKUP_URL,
        {
            "osm_ids": f"{osm_type.upper()[:1]}{osm_id}",
            "format": "jsonv2",
            "addressdetails": 1,
        },
    )
    if not payload:
        raise MapServiceError("Place not found.")

    item = payload[0]
    return {
        "place_id": str(item.get("place_id", "")),
        "source": "nominatim",
        "osm_type": item.get("osm_type", "").upper()[:1],
        "osm_id": str(item.get("osm_id", "")),
        "name": item.get("name") or item.get("display_name", ""),
        "address": item.get("display_name", ""),
        "latitude": item.get("lat"),
        "longitude": item.get("lon"),
    }


def reverse_geocode(latitude, longitude):
    payload = _load_json(
        settings.NOMINATIM_REVERSE_URL,
        {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
        },
    )
    return {
        "place_id": str(payload.get("place_id", "")),
        "source": "nominatim",
        "osm_type": payload.get("osm_type", "").upper()[:1],
        "osm_id": str(payload.get("osm_id", "")),
        "name": payload.get("name") or payload.get("display_name", ""),
        "address": payload.get("display_name", ""),
        "latitude": payload.get("lat", latitude),
        "longitude": payload.get("lon", longitude),
    }


def get_route_details(pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude):
    coordinates = f"{pickup_longitude},{pickup_latitude};{dropoff_longitude},{dropoff_latitude}"
    try:
        payload = _load_json(
            f"{settings.OSRM_BASE_URL}/route/v1/driving/{coordinates}",
            {
                "overview": "full",
                "geometries": "geojson",
            },
        )
        route = (payload.get("routes") or [])[0]
        return {
            "distance_km": (Decimal(str(route["distance"])) / Decimal("1000")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "duration_minutes": (Decimal(str(route["duration"])) / Decimal("60")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "geometry": route.get("geometry"),
        }
    except Exception:
        return {
            "distance_km": _fallback_distance(
                pickup_latitude,
                pickup_longitude,
                dropoff_latitude,
                dropoff_longitude,
            ),
            "duration_minutes": None,
            "geometry": None,
        }
