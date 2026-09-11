from django.contrib import admin

from .models import ChatQuery, ScannedReceipt


@admin.register(ChatQuery)
class ChatQueryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "created_at")
    list_filter = ("user", "created_at")
    search_fields = ("question", "answer")


@admin.register(ScannedReceipt)
class ScannedReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_by", "status", "purchase_invoice", "created_at")
    list_filter = ("status", "created_at")
