from decimal import Decimal

from rest_framework import serializers

from maps.serializers import MapPlaceSelectionSerializer
from maps.services import get_route_details
from transporters.models import TransporterProfile, Vehicle, get_price_per_km
from transporters.serializers import TransporterProfileSerializer, VehicleSerializer

from .matching import progressive_transporter_matches
from .models import (
    Booking,
    BookingPaymentStatus,
    BookingStatus,
    BookingStatusHistory,
    TrackingUpdate,
    determine_vehicle_type,
    haversine_distance,
)


class NearbyTransporterSerializer(serializers.Serializer):
    transporter_id = serializers.IntegerField()
    transporter_name = serializers.CharField()
    company_name = serializers.CharField(allow_blank=True)
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2)
    vehicle = VehicleSerializer()
    estimated_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class BookingCreateSerializer(serializers.ModelSerializer):
    pickup_place = MapPlaceSelectionSerializer(write_only=True)
    dropoff_place = MapPlaceSelectionSerializer(write_only=True)
    matched_transporters = serializers.SerializerMethodField(read_only=True)
    route_geometry = serializers.JSONField(read_only=True)
    estimated_duration_minutes = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "produce_name",
            "produce_description",
            "weight_kg",
            "pickup_place",
            "dropoff_place",
            "pickup_place_id",
            "pickup_place_source",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_place_id",
            "dropoff_place_source",
            "dropoff_address",
            "dropoff_latitude",
            "dropoff_longitude",
            "search_radius_km",
            "estimated_distance_km",
            "estimated_duration_minutes",
            "route_geometry",
            "vehicle_type_required",
            "quoted_price",
            "status",
            "payment_status",
            "matched_transporters",
        )
        read_only_fields = (
            "pickup_place_id",
            "pickup_place_source",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_place_id",
            "dropoff_place_source",
            "dropoff_address",
            "dropoff_latitude",
            "dropoff_longitude",
            "search_radius_km",
            "estimated_distance_km",
            "estimated_duration_minutes",
            "route_geometry",
            "vehicle_type_required",
            "quoted_price",
            "status",
            "payment_status",
            "matched_transporters",
        )

    def create(self, validated_data):
        pickup_place = validated_data.pop("pickup_place")
        dropoff_place = validated_data.pop("dropoff_place")
        route = get_route_details(
            pickup_place["latitude"],
            pickup_place["longitude"],
            dropoff_place["latitude"],
            dropoff_place["longitude"],
        )
        distance_km = Decimal(str(route["distance_km"]))
        duration_minutes = route["duration_minutes"]
        if duration_minutes is not None:
            duration_minutes = Decimal(str(duration_minutes))
        vehicle_type_required = determine_vehicle_type(validated_data["weight_kg"])
        quoted_price = get_price_per_km(vehicle_type_required) * distance_km
        booking = Booking(
            farmer=self.context["request"].user,
            pickup_place_id=pickup_place.get("place_id", ""),
            pickup_place_source=pickup_place.get("source", ""),
            pickup_address=pickup_place["address"],
            pickup_latitude=pickup_place["latitude"],
            pickup_longitude=pickup_place["longitude"],
            dropoff_place_id=dropoff_place.get("place_id", ""),
            dropoff_place_source=dropoff_place.get("source", ""),
            dropoff_address=dropoff_place["address"],
            dropoff_latitude=dropoff_place["latitude"],
            dropoff_longitude=dropoff_place["longitude"],
            vehicle_type_required=vehicle_type_required,
            estimated_distance_km=distance_km,
            estimated_duration_minutes=duration_minutes,
            route_geometry=route["geometry"],
            quoted_price=quoted_price,
            search_radius_km="0.00",
            status=BookingStatus.PENDING_PAYMENT,
            payment_status=BookingPaymentStatus.UNPAID,
            **validated_data,
        )
        _, selected_radius = progressive_transporter_matches(booking)
        booking.search_radius_km = selected_radius
        booking.save()
        BookingStatusHistory.objects.create(
            booking=booking,
            status=BookingStatus.PENDING_PAYMENT,
            created_by=self.context["request"].user,
            notes="Booking created and waiting for payment confirmation.",
        )
        return booking

    def get_matched_transporters(self, obj):
        return NearbyTransporterSerializer(
            self.context["matching_service"](obj),
            many=True,
        ).data


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusHistory
        fields = ("id", "status", "notes", "created_at", "created_by")


class TrackingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingUpdate
        fields = ("id", "latitude", "longitude", "speed_kph", "notes", "created_at")


class BookingDetailSerializer(serializers.ModelSerializer):
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    tracking_updates = TrackingUpdateSerializer(many=True, read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    transporter_profile = serializers.SerializerMethodField()
    pickup_place = serializers.SerializerMethodField()
    dropoff_place = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "produce_name",
            "produce_description",
            "weight_kg",
            "pickup_place",
            "dropoff_place",
            "pickup_place_id",
            "pickup_place_source",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_place_id",
            "dropoff_place_source",
            "dropoff_address",
            "dropoff_latitude",
            "dropoff_longitude",
            "search_radius_km",
            "estimated_distance_km",
            "estimated_duration_minutes",
            "route_geometry",
            "vehicle_type_required",
            "quoted_price",
            "status",
            "payment_status",
            "transporter",
            "vehicle",
            "accepted_at",
            "delivered_at",
            "created_at",
            "updated_at",
            "status_history",
            "tracking_updates",
            "transporter_profile",
        )

    def get_transporter_profile(self, obj):
        if obj.transporter is None or not hasattr(obj.transporter, "transporter_profile"):
            return None
        return TransporterProfileSerializer(obj.transporter.transporter_profile).data

    def _place_payload(self, obj, prefix):
        return {
            "place_id": getattr(obj, f"{prefix}_place_id"),
            "source": getattr(obj, f"{prefix}_place_source"),
            "address": getattr(obj, f"{prefix}_address"),
            "latitude": getattr(obj, f"{prefix}_latitude"),
            "longitude": getattr(obj, f"{prefix}_longitude"),
        }

    def get_pickup_place(self, obj):
        return self._place_payload(obj, "pickup")

    def get_dropoff_place(self, obj):
        return self._place_payload(obj, "dropoff")


class BookingDecisionSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField(required=False)
    action = serializers.ChoiceField(choices=("accept", "decline"))

    def validate(self, attrs):
        try:
            booking = Booking.objects.get(id=attrs["booking_id"])
        except Booking.DoesNotExist as exc:
            raise serializers.ValidationError({"booking_id": "We could not find that booking."}) from exc
        request = self.context["request"]
        attrs["booking"] = booking

        if attrs["action"] == "accept":
            if booking.status != BookingStatus.CONFIRMED:
                raise serializers.ValidationError("This job is not ready to be accepted yet.")
            if booking.payment_status != BookingPaymentStatus.PAID:
                raise serializers.ValidationError("The farmer still needs to complete payment before you can accept this job.")
            if "vehicle_id" not in attrs:
                raise serializers.ValidationError({"vehicle_id": "Select a vehicle before accepting this job."})
            if not self.context["booking_matcher"](booking, request.user):
                raise serializers.ValidationError("This job is not available for your current dispatch area.")

            try:
                vehicle = Vehicle.objects.get(
                    id=attrs["vehicle_id"],
                    transporter__user=request.user,
                    is_available=True,
                )
            except Vehicle.DoesNotExist as exc:
                raise serializers.ValidationError({"vehicle_id": "That vehicle is not available right now."}) from exc
            if vehicle.vehicle_type != booking.vehicle_type_required:
                raise serializers.ValidationError("Choose a vehicle that matches this delivery request.")
            if not vehicle.can_carry(booking.weight_kg):
                raise serializers.ValidationError("Choose a vehicle that can carry this load.")
            attrs["vehicle"] = vehicle
        return attrs

    def save(self, **kwargs):
        booking = self.validated_data["booking"]
        user = self.context["request"].user
        action = self.validated_data["action"]

        if action == "decline":
            BookingStatusHistory.objects.create(
                booking=booking,
                status=BookingStatus.DECLINED,
                created_by=user,
                notes="Booking declined by transporter",
            )
            booking.save(update_fields=["updated_at"])
            return booking

        vehicle = self.validated_data["vehicle"]
        booking.transporter = user
        booking.vehicle = vehicle
        booking.status = BookingStatus.ACCEPTED
        from django.utils import timezone
        booking.accepted_at = timezone.now()
        booking.save()

        vehicle.is_available = False
        vehicle.save(update_fields=["is_available", "updated_at"])

        BookingStatusHistory.objects.create(
            booking=booking,
            status=BookingStatus.ACCEPTED,
            created_by=user,
            notes="Booking accepted by transporter",
        )
        if hasattr(booking, "payment"):
            payment = booking.payment
            changed = []
            if payment.transporter_id != user.id:
                payment.transporter = user
                changed.append("transporter")
            if changed:
                payment.save(update_fields=[*changed, "updated_at"])
            if hasattr(payment, "payout"):
                payout = payment.payout
                if payout.transporter_id != user.id:
                    payout.transporter = user
                    payout.save(update_fields=["transporter", "updated_at"])
        return booking


class BookingStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(BookingStatus.PICKED_UP, BookingStatus.DELIVERED)
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    location_radius_km = Decimal("0.05")

    def validate_status(self, value):
        booking = self.context["booking"]
        valid_transitions = {
            BookingStatus.ACCEPTED: BookingStatus.PICKED_UP,
            BookingStatus.IN_TRANSIT: BookingStatus.DELIVERED,
        }
        expected = valid_transitions.get(booking.status)
        if expected != value:
            raise serializers.ValidationError("That update is not available for this delivery right now.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        booking = self.context["booking"]
        user = self.context["request"].user
        transporter_profile = TransporterProfile.objects.filter(user=user).first()
        if (
            transporter_profile is None
            or transporter_profile.current_latitude is None
            or transporter_profile.current_longitude is None
        ):
            raise serializers.ValidationError("Turn on location access before updating this delivery.")

        if attrs["status"] == BookingStatus.PICKED_UP:
            target_latitude = booking.pickup_latitude
            target_longitude = booking.pickup_longitude
            message = "Arrive at the pickup location before marking this booking as picked up."
        else:
            target_latitude = booking.dropoff_latitude
            target_longitude = booking.dropoff_longitude
            message = "Arrive at the delivery location before marking this booking as delivered."

        distance = haversine_distance(
            transporter_profile.current_latitude,
            transporter_profile.current_longitude,
            target_latitude,
            target_longitude,
        )
        if distance > self.location_radius_km:
            raise serializers.ValidationError(message)

        attrs["transporter_profile"] = transporter_profile
        return attrs

    def save(self, **kwargs):
        booking = self.context["booking"]
        booking.status = self.validated_data["status"]
        if booking.status == BookingStatus.DELIVERED:
            from django.utils import timezone
            booking.delivered_at = timezone.now()
            if booking.vehicle:
                booking.vehicle.is_available = True
                booking.vehicle.save(update_fields=["is_available", "updated_at"])
        booking.save()
        BookingStatusHistory.objects.create(
            booking=booking,
            status=booking.status,
            notes=self.validated_data.get("notes", ""),
            created_by=self.context["request"].user,
        )
        return booking


class TrackingUpdateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingUpdate
        fields = ("latitude", "longitude", "speed_kph", "notes")

    def create(self, validated_data):
        booking = self.context["booking"]
        update = TrackingUpdate.objects.create(
            booking=booking,
            transporter=self.context["request"].user,
            **validated_data,
        )
        transporter_profile = TransporterProfile.objects.filter(user=self.context["request"].user).first()
        if transporter_profile:
            transporter_profile.current_latitude = update.latitude
            transporter_profile.current_longitude = update.longitude
            from django.utils import timezone
            transporter_profile.last_location_update = timezone.now()
            transporter_profile.save(
                update_fields=["current_latitude", "current_longitude", "last_location_update"]
            )
        if booking.status == BookingStatus.PICKED_UP:
            distance_from_pickup = haversine_distance(
                update.latitude,
                update.longitude,
                booking.pickup_latitude,
                booking.pickup_longitude,
            )
            if distance_from_pickup > Decimal("0.05"):
                booking.status = BookingStatus.IN_TRANSIT
                booking.save(update_fields=["status", "updated_at"])
                BookingStatusHistory.objects.create(
                    booking=booking,
                    status=BookingStatus.IN_TRANSIT,
                    notes="Driver departed pickup location and transport is now in transit.",
                    created_by=self.context["request"].user,
                )
        return update
