from django.contrib import admin

from .models import LedgerEntry, Party


class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    readonly_fields = ("created_by", "created_at")


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "phone", "opening_balance", "current_balance", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name", "phone")
    inlines = [LedgerEntryInline]

    def current_balance(self, obj):
        return obj.get_balance()


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("party", "date", "entry_type", "amount", "reference", "created_by")
    list_filter = ("entry_type", "date")
    search_fields = ("party__name", "reference")
