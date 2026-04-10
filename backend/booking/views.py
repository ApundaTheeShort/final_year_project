from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, response, serializers, status
from rest_framework.views import APIView

from transporters.models import Vehicle

from .matching import progressive_transporter_matches
from .models import Booking, BookingStatus
from .permissions import IsDriver, IsFarmer
from .serializers import (
    BookingCreateSerializer,
    BookingDecisionSerializer,
    BookingDetailSerializer,
    BookingStatusUpdateSerializer,
    NearbyTransporterSerializer,
    TrackingUpdateCreateSerializer,
)


def match_transporters(booking):
    matches, selected_radius = progressive_transporter_matches(booking)
    if booking.search_radius_km != selected_radius:
        booking.search_radius_km = selected_radius
        booking.save(update_fields=["search_radius_km", "updated_at"])
    return matches


def booking_matches_driver(booking, user):
    for match in match_transporters(booking):
        if match["transporter_id"] == user.id:
            return True
    return False


class BookingCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get_queryset(self):
        return Booking.objects.filter(farmer=self.request.user).select_related("transporter", "vehicle")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookingCreateSerializer
        return BookingDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["matching_service"] = match_transporters
        return context


class BookingDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookingDetailSerializer

    def get_queryset(self):
        return Booking.objects.filter(
            Q(farmer=self.request.user) | Q(transporter=self.request.user)
        ).select_related("transporter", "vehicle", "transporter__transporter_profile")

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.farmer != request.user:
            return response.Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if booking.status != BookingStatus.PENDING:
            raise serializers.ValidationError("Only pending bookings can be deleted by the farmer.")
        booking.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class NearbyTransportersView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, farmer=request.user)
        serializer = NearbyTransporterSerializer(match_transporters(booking), many=True)
        return response.Response(serializer.data)


class DriverOpenBookingsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    serializer_class = BookingDetailSerializer

    def get_queryset(self):
        pending_bookings = Booking.objects.filter(
            status=BookingStatus.PENDING,
            vehicle_type_required__in=Vehicle.objects.filter(
                transporter__user=self.request.user,
                is_available=True,
            ).values_list("vehicle_type", flat=True),
        )
        profile = getattr(self.request.user, "transporter_profile", None)
        if not profile or profile.current_latitude is None or profile.current_longitude is None:
            return pending_bookings
        matching_ids = [
            booking.id for booking in pending_bookings
            if booking_matches_driver(booking, self.request.user)
        ]
        return pending_bookings.filter(id__in=matching_ids)


class DriverAssignedBookingsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    serializer_class = BookingDetailSerializer

    def get_queryset(self):
        return Booking.objects.filter(transporter=self.request.user).select_related(
            "transporter",
            "vehicle",
            "transporter__transporter_profile",
        )


class BookingDecisionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request):
        serializer = BookingDecisionSerializer(
            data=request.data,
            context={"request": request, "booking_matcher": booking_matches_driver},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return response.Response(BookingDetailSerializer(booking).data)


class BookingStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, transporter=request.user)
        serializer = BookingStatusUpdateSerializer(
            data=request.data,
            context={"request": request, "booking": booking},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return response.Response(BookingDetailSerializer(booking).data)


class TrackingUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, transporter=request.user)
        serializer = TrackingUpdateCreateSerializer(
            data=request.data,
            context={"request": request, "booking": booking},
        )
        serializer.is_valid(raise_exception=True)
        tracking_update = serializer.save()
        return response.Response(serializer.to_representation(tracking_update), status=status.HTTP_201_CREATED)


class BookingTrackingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("transporter", "vehicle"),
            id=booking_id,
        )
        if request.user not in {booking.farmer, booking.transporter}:
            return response.Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return response.Response(BookingDetailSerializer(booking).data)
