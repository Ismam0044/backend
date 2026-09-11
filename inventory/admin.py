from django.contrib import admin

from .models import Item, ItemGroup, Stock, StockTransfer, StockTransferItem, Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name")


@admin.register(ItemGroup)
class ItemGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "group", "unit", "cost_price", "sale_price", "reorder_level", "is_active")
    list_filter = ("group", "is_active")
    search_fields = ("name", "code")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("item", "warehouse", "quantity")
    list_filter = ("warehouse",)
    search_fields = ("item__name",)


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "from_warehouse", "to_warehouse", "date", "status", "created_by")
    list_filter = ("status", "from_warehouse", "to_warehouse")
    inlines = [StockTransferItemInline]
