from django.urls import path
from .views import AdminDashboardView, CustomLoginView, HomeView, ProfileUpdateView, SignUpView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
]
