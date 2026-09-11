from django.contrib import admin

from .models import PurchaseInvoice, PurchaseInvoiceItem


class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "warehouse", "supplier", "date", "total", "paid_amount", "payment_mode", "status")
    list_filter = ("warehouse", "status", "payment_mode", "date")
    search_fields = ("invoice_no", "supplier__name")
    inlines = [PurchaseInvoiceItemInline]
