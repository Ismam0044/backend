from django.contrib import admin

from .models import CashBookEntry, Voucher


@admin.register(CashBookEntry)
class CashBookEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "warehouse", "entry_type", "amount", "category", "reference", "created_by")
    list_filter = ("warehouse", "entry_type", "date")
    search_fields = ("reference", "description")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("id", "voucher_type", "warehouse", "party", "date", "amount", "mode", "approved")
    list_filter = ("voucher_type", "warehouse", "mode", "approved")
    search_fields = ("party__name",)
