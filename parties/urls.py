from django.urls import path

from . import views

app_name = "parties"

urlpatterns = [
    path("", views.party_list, name="list"),
    path("<int:pk>/", views.party_detail, name="detail"),
    path("<int:pk>/transaction/", views.record_transaction, name="record_transaction"),
]
