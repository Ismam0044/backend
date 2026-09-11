from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.cash_book, name="cash_book"),
    path("add/", views.add_cash_entry, name="add_cash_entry"),
]
