from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("dues/", views.dues, name="dues"),
    path("daily-sales/", views.daily_sales, name="daily_sales"),
]
