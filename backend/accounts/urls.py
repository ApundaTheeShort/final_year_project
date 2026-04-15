from django.urls import path
from .views import (
    AdminDashboardView,
    AdminBookingsReportExportView,
    AdminRatesReportExportView,
    CustomLoginView,
    FarmerBookingsReportExportView,
    HomeView,
    ProfileUpdateView,
    ResendVerificationView,
    SignUpView,
    TransporterJobsReportExportView,
    VerifyEmailCodeView,
    VerificationSentView,
    VerifyEmailView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('verification-sent/', VerificationSentView.as_view(), name='verification-sent'),
    path('verify-email/', VerifyEmailCodeView.as_view(), name='verify-email'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name='legacy-verify-email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('reports/farmer-bookings.csv', FarmerBookingsReportExportView.as_view(), name='farmer-bookings-report-export'),
    path('reports/transporter-jobs.csv', TransporterJobsReportExportView.as_view(), name='transporter-jobs-report-export'),
    path('reports/admin-bookings.csv', AdminBookingsReportExportView.as_view(), name='admin-bookings-report-export'),
    path('reports/admin-rates.csv', AdminRatesReportExportView.as_view(), name='admin-rates-report-export'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
]
