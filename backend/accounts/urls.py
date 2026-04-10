from django.urls import path
from .views import (
    AdminDashboardView,
    CustomLoginView,
    HomeView,
    ProfileUpdateView,
    ResendVerificationView,
    SignUpView,
    VerificationSentView,
    VerifyEmailView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('verification-sent/', VerificationSentView.as_view(), name='verification-sent'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
]
