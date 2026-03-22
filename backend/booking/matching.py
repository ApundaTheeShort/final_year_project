from transporters.models import Vehicle, get_price_per_km

from .models import haversine_distance


SEARCH_RADIUS_STEPS_KM = (5, 10, 25, 50, 100, 200, 500, 1000)


def progressive_transporter_matches(booking):
    vehicles = (
        Vehicle.objects.filter(
            is_available=True,
            vehicle_type=booking.vehicle_type_required,
            capacity_kg__gte=booking.weight_kg,
            transporter__current_latitude__isnull=False,
            transporter__current_longitude__isnull=False,
        )
        .select_related("transporter__user")
        .order_by("registration_number")
    )

    all_matches = []
    for vehicle in vehicles:
        distance = haversine_distance(
            booking.pickup_latitude,
            booking.pickup_longitude,
            vehicle.transporter.current_latitude,
            vehicle.transporter.current_longitude,
        )
        all_matches.append(
            {
                "transporter_id": vehicle.transporter.user_id,
                "transporter_name": (
                    f"{vehicle.transporter.user.first_name} {vehicle.transporter.user.last_name}".strip()
                ),
                "company_name": vehicle.transporter.company_name,
                "distance_km": distance,
                "vehicle": vehicle,
                "estimated_price": booking.quoted_price
                or (get_price_per_km(booking.vehicle_type_required) * booking.estimated_distance_km),
            }
        )

    all_matches.sort(key=lambda item: (item["distance_km"], item["vehicle"].registration_number))

    if not all_matches:
        return [], SEARCH_RADIUS_STEPS_KM[-1]

    farthest_distance = all_matches[-1]["distance_km"]
    for radius in SEARCH_RADIUS_STEPS_KM:
        if farthest_distance <= radius:
            return all_matches, radius

    return all_matches, farthest_distance
