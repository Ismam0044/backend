from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("chat/", views.chat_view, name="chat"),
    path("chat/ask/", views.chat_ask, name="chat_ask"),
    path("reorder/", views.reorder_view, name="reorder"),
    path("reorder/summary/", views.reorder_summary, name="reorder_summary"),
    path("scan/", views.scan_list, name="scan_list"),
    path("scan/upload/", views.scan_upload, name="scan_upload"),
    path("scan/<int:pk>/", views.scan_review, name="scan_review"),
    path("scan/<int:pk>/confirm/", views.scan_confirm, name="scan_confirm"),
    path("scan/<int:pk>/discard/", views.scan_discard, name="scan_discard"),
]
