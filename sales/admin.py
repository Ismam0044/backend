from django.contrib import admin

from .models import SalesInvoice, SalesInvoiceItem


class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 1


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "warehouse", "party", "date", "payment_type", "total", "paid_amount", "status")
    list_filter = ("warehouse", "payment_type", "status", "date")
    search_fields = ("invoice_no", "party__name")
    inlines = [SalesInvoiceItemInline]
