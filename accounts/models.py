from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import Warehouse
from parties.models import Party


class CashBookEntry(models.Model):
    class EntryType(models.TextChoices):
        IN = "IN", "Cash In"
        OUT = "OUT", "Cash Out"

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="cashbook_entries")
    date = models.DateField()
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Cash book entries"

    def __str__(self):
        return f"{self.date} {self.entry_type} {self.amount}"


class Voucher(models.Model):
    class VoucherType(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        RECEIPT = "RECEIPT", "Receipt"

    class Mode(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank"
        BKASH = "BKASH", "bKash"
        NAGAD = "NAGAD", "Nagad"

    voucher_type = models.CharField(max_length=10, choices=VoucherType.choices)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="vouchers")
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="vouchers", null=True, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CASH)
    description = models.CharField(max_length=255, blank=True)
    approved = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.voucher_type} #{self.pk} - {self.amount}"
