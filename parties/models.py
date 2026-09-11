from django.conf import settings
from django.db import models
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce


class PartyQuerySet(models.QuerySet):
    def with_balance(self):
        """Annotate every party with its balance in one query instead of N queries."""
        zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        return self.annotate(
            debit_sum=Coalesce(
                Sum("ledger_entries__amount", filter=Q(ledger_entries__entry_type="DEBIT")), zero
            ),
            credit_sum=Coalesce(
                Sum("ledger_entries__amount", filter=Q(ledger_entries__entry_type="CREDIT")), zero
            ),
        ).annotate(balance=F("opening_balance") + F("debit_sum") - F("credit_sum"))


class Party(models.Model):
    class Type(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        SUPPLIER = "SUPPLIER", "Supplier"
        BOTH = "BOTH", "Both"

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.CUSTOMER)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PartyQuerySet.as_manager()

    def __str__(self):
        return self.name

    def get_balance(self):
        """Positive = party owes the shop (receivable). Negative = shop owes party (payable)."""
        total = self.ledger_entries.aggregate(
            debit=models.Sum("amount", filter=models.Q(entry_type=LedgerEntry.EntryType.DEBIT)),
            credit=models.Sum("amount", filter=models.Q(entry_type=LedgerEntry.EntryType.CREDIT)),
        )
        debit = total["debit"] or 0
        credit = total["credit"] or 0
        return self.opening_balance + debit - credit


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        DEBIT = "DEBIT", "Debit"   # party owes more (e.g. credit sale)
        CREDIT = "CREDIT", "Credit"  # party owes less (e.g. payment received)

    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="ledger_entries")
    date = models.DateField()
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Ledger entries"

    def __str__(self):
        return f"{self.party} {self.entry_type} {self.amount}"
