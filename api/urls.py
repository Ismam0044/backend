from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import LoginView, LogoutView, MeView
from api.views.core import DashboardView, WarehouseListView
from api.views.inventory import ItemSearchView
from api.views.parties import PartyListView
from api.views.sales import SalesCheckoutView, SalesInvoiceDetailView, SalesInvoiceListView

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

    # --- inventory ------------------------------------------------------------
    path("inventory/items/", ItemSearchView.as_view(), name="item_search"),

    # --- parties -----------------------------------------------------------
    path("parties/", PartyListView.as_view(), name="party_list"),

    # --- sales -------------------------------------------------------------
    path("sales/checkout/", SalesCheckoutView.as_view(), name="sales_checkout"),
    path("sales/invoices/", SalesInvoiceListView.as_view(), name="sales_invoice_list"),
    path("sales/invoices/<int:pk>/", SalesInvoiceDetailView.as_view(), name="sales_invoice_detail"),
]
