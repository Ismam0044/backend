from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import Warehouse
from inventory.models import Item
from parties.models import Party


class SalesInvoice(models.Model):
    class PaymentType(models.TextChoices):
        CASH = "CASH", "Cash"
        CREDIT = "CREDIT", "Credit"
        BKASH = "BKASH", "bKash"
        NAGAD = "NAGAD", "Nagad"
        CARD = "CARD", "Card"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice_no = models.CharField(max_length=30, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="sales_invoices")
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="sales_invoices", null=True, blank=True)
    date = models.DateField()
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.CASH)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    @property
    def due_amount(self):
        return self.total - self.paid_amount

    def __str__(self):
        return self.invoice_no


class SalesInvoiceItem(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price
