from django.utils import timezone
from rest_framework import generics, permissions, response

from .models import TransporterProfile
from .permissions import IsDriver
from .serializers import DriverVehicleSetupSerializer, TransporterProfileSerializer


class DriverVehicleSetupView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    serializer_class = DriverVehicleSetupSerializer

    def get_object(self):
        return TransporterProfile.objects.filter(user=self.request.user).first()

    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        if profile is None:
            return response.Response({"profile": None, "vehicles": []})

        serializer = self.get_serializer(instance=profile)
        return response.Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        output = self.get_serializer(instance=profile)
        return response.Response(output.data)


class DriverLocationUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    serializer_class = TransporterProfileSerializer

    def get_object(self):
        profile, _ = TransporterProfile.objects.get_or_create(user=self.request.user)
        return profile

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_location_update=timezone.now())
        return response.Response(serializer.data)
