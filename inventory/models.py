from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import Warehouse


class Unit(models.Model):
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10)

    def __str__(self):
        return self.short_name


class ItemGroup(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    group = models.ForeignKey(ItemGroup, on_delete=models.PROTECT, related_name="items")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="items")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Stock(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_levels")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_levels")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("item", "warehouse")

    def __str__(self):
        return f"{self.item} @ {self.warehouse}: {self.quantity}"


class StockTransfer(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        COMPLETED = "COMPLETED", "Completed"

    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="transfers_out")
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="transfers_in")
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Transfer #{self.pk}: {self.from_warehouse} -> {self.to_warehouse}"


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
