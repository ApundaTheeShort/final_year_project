from rest_framework import serializers

from .models import (
    TransporterProfile,
    Vehicle,
    get_transport_rules,
    normalize_vehicle_type_key,
)


class TransporterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransporterProfile
        fields = (
            "id",
            "company_name",
            "current_latitude",
            "current_longitude",
            "last_location_update",
        )
        read_only_fields = ("last_location_update",)


class VehicleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "registration_number",
            "vehicle_type",
            "capacity_kg",
            "is_available",
        )
        extra_kwargs = {
            "registration_number": {"validators": []},
        }

    def validate_vehicle_type(self, value):
        vehicle_type = normalize_vehicle_type_key(value)
        available_types = {rule.vehicle_type for rule in get_transport_rules()}
        if vehicle_type not in available_types:
            raise serializers.ValidationError("Choose a vehicle type that has been configured by the system admin.")
        return vehicle_type


class DriverVehicleSetupSerializer(serializers.Serializer):
    profile = TransporterProfileSerializer()
    vehicles = VehicleSerializer(many=True)

    def validate_vehicles(self, vehicles):
        seen = set()
        for vehicle in vehicles:
            registration_number = vehicle["registration_number"]
            if registration_number in seen:
                raise serializers.ValidationError("Vehicle registration numbers must be unique.")
            seen.add(registration_number)

            vehicle_id = vehicle.get("id")
            existing = Vehicle.objects.filter(registration_number=registration_number)
            if vehicle_id:
                existing = existing.exclude(id=vehicle_id)
            if existing.exists():
                raise serializers.ValidationError(
                    f"Vehicle registration number {registration_number} already exists."
                )
        return vehicles

    def create(self, validated_data):
        profile_data = validated_data["profile"]
        vehicles_data = validated_data["vehicles"]
        user = self.context["request"].user

        profile, _ = TransporterProfile.objects.update_or_create(
            user=user,
            defaults=profile_data,
        )

        existing_ids = []
        for vehicle_data in vehicles_data:
            vehicle_id = vehicle_data.pop("id", None)
            if vehicle_id:
                vehicle = Vehicle.objects.get(id=vehicle_id, transporter=profile)
                for field, value in vehicle_data.items():
                    setattr(vehicle, field, value)
                vehicle.save()
            else:
                vehicle = Vehicle.objects.create(transporter=profile, **vehicle_data)
            existing_ids.append(vehicle.id)

        profile.vehicles.exclude(id__in=existing_ids).delete()
        return profile

    def to_representation(self, instance):
        return {
            "profile": TransporterProfileSerializer(instance).data,
            "vehicles": VehicleSerializer(instance.vehicles.all(), many=True).data,
        }
