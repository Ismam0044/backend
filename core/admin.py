from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("ERP", {"fields": ("role", "assigned_warehouses", "phone")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active")
