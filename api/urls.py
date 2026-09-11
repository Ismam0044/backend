from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import LoginView, LogoutView, MeView
from api.views.core import DashboardView, WarehouseListView

app_name = "api"

urlpatterns = [
    # --- auth -------------------------------------------------------------
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),

    # --- core ---------------------------------------------------------------
    path("warehouses/", WarehouseListView.as_view(), name="warehouses"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
