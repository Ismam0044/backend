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
from api.views.accounts import CashBookCreateView, CashBookListView
from api.views.parties import PartyDetailView, PartyListView, RecordTransactionView
from api.views.purchase import PurchaseCheckoutView, PurchaseInvoiceDetailView, PurchaseInvoiceListView
from api.views.reports import DailySalesReportView, DuesReportView, LowStockReportView
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
    path("parties/<int:pk>/", PartyDetailView.as_view(), name="party_detail"),
    path("parties/<int:pk>/transactions/", RecordTransactionView.as_view(), name="party_record_transaction"),

    # --- accounts ------------------------------------------------------------
    path("accounts/cashbook/", CashBookListView.as_view(), name="cashbook_list"),
    path("accounts/cashbook/add/", CashBookCreateView.as_view(), name="cashbook_create"),

    # --- reports -------------------------------------------------------------
    path("reports/low-stock/", LowStockReportView.as_view(), name="report_low_stock"),
    path("reports/dues/", DuesReportView.as_view(), name="report_dues"),
    path("reports/daily-sales/", DailySalesReportView.as_view(), name="report_daily_sales"),

    # --- sales -------------------------------------------------------------
    path("sales/checkout/", SalesCheckoutView.as_view(), name="sales_checkout"),
    path("sales/invoices/", SalesInvoiceListView.as_view(), name="sales_invoice_list"),
    path("sales/invoices/<int:pk>/", SalesInvoiceDetailView.as_view(), name="sales_invoice_detail"),

    # --- purchase ----------------------------------------------------------
    path("purchase/checkout/", PurchaseCheckoutView.as_view(), name="purchase_checkout"),
    path("purchase/invoices/", PurchaseInvoiceListView.as_view(), name="purchase_invoice_list"),
    path("purchase/invoices/<int:pk>/", PurchaseInvoiceDetailView.as_view(), name="purchase_invoice_detail"),
]
