from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import LoginView, LogoutView, MeView
from api.views.core import DashboardView, WarehouseListView
from api.views.inventory import (
    ItemSearchView,
    StockTransferCheckoutView,
    StockTransferDetailView,
    StockTransferListView,
)
from api.views.parties import PartyListView
from api.views.purchase import PurchaseCheckoutView, PurchaseInvoiceDetailView, PurchaseInvoiceListView
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
    path("inventory/transfers/checkout/", StockTransferCheckoutView.as_view(), name="transfer_checkout"),
    path("inventory/transfers/", StockTransferListView.as_view(), name="transfer_list"),
    path("inventory/transfers/<int:pk>/", StockTransferDetailView.as_view(), name="transfer_detail"),

    # --- parties -----------------------------------------------------------
    path("parties/", PartyListView.as_view(), name="party_list"),

    # --- sales -------------------------------------------------------------
    path("sales/checkout/", SalesCheckoutView.as_view(), name="sales_checkout"),
    path("sales/invoices/", SalesInvoiceListView.as_view(), name="sales_invoice_list"),
    path("sales/invoices/<int:pk>/", SalesInvoiceDetailView.as_view(), name="sales_invoice_detail"),

    # --- purchase ----------------------------------------------------------
    path("purchase/checkout/", PurchaseCheckoutView.as_view(), name="purchase_checkout"),
    path("purchase/invoices/", PurchaseInvoiceListView.as_view(), name="purchase_invoice_list"),
    path("purchase/invoices/<int:pk>/", PurchaseInvoiceDetailView.as_view(), name="purchase_invoice_detail"),
]
