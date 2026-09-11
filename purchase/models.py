from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import Warehouse
from inventory.models import Item
from parties.models import Party


class PurchaseInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentMode(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank"
        BKASH = "BKASH", "bKash"
        NAGAD = "NAGAD", "Nagad"

    invoice_no = models.CharField(max_length=30, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_invoices")
    supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="purchase_invoices")
    date = models.DateField()
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices, default=PaymentMode.CASH)
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


class PurchaseInvoiceItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_cost
