from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("transfer/", views.transfer_entry, name="transfer_entry"),
    path("transfer/from-warehouse/", views.set_from_warehouse, name="set_from_warehouse"),
    path("transfer/item-search/", views.item_search, name="item_search"),
    path("transfer/cart/add/", views.add_to_cart, name="add_to_cart"),
    path("transfer/cart/update/", views.update_cart_line, name="update_cart_line"),
    path("transfer/cart/remove/", views.remove_cart_line, name="remove_cart_line"),
    path("transfer/checkout/", views.checkout, name="checkout"),
]
