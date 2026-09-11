from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.pos, name="pos"),
    path("warehouse/", views.set_warehouse, name="set_warehouse"),
    path("item-search/", views.item_search, name="item_search"),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/", views.update_cart_line, name="update_cart_line"),
    path("cart/remove/", views.remove_cart_line, name="remove_cart_line"),
    path("checkout/", views.checkout, name="checkout"),
    path("invoice/<int:pk>/", views.receipt, name="receipt"),
]
