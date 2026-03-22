from rest_framework import serializers

from .models import TransporterProfile, Vehicle


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
    class Meta:
        model = Vehicle
        fields = (
            "id",
            "registration_number",
            "vehicle_type",
            "capacity_kg",
            "is_available",
        )


class DriverVehicleSetupSerializer(serializers.Serializer):
    profile = TransporterProfileSerializer()
    vehicles = VehicleSerializer(many=True)

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
