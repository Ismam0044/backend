from django.contrib.auth.models import AbstractUser
from django.db import models


class Warehouse(models.Model):
    class Type(models.TextChoices):
        WAREHOUSE = "WAREHOUSE", "Warehouse"
        STORE = "STORE", "Store"
        COUNTER = "COUNTER", "Counter"

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.STORE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        CASHIER = "CASHIER", "Cashier"
        STOCK_KEEPER = "STOCK_KEEPER", "Stock Keeper"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    # Empty means access to all warehouses (typical for Owner/Manager).
    assigned_warehouses = models.ManyToManyField(Warehouse, blank=True, related_name="staff")
    phone = models.CharField(max_length=20, blank=True)

    def has_warehouse_access(self, warehouse):
        if self.role == self.Role.OWNER or not self.assigned_warehouses.exists():
            return True
        return self.assigned_warehouses.filter(pk=warehouse.pk).exists()

    def save(self, *args, **kwargs):
        # createsuperuser doesn't know about our custom role field, so it would
        # otherwise leave superusers on the CASHIER default. A superuser should
        # always be treated as Owner-equivalent.
        if self.is_superuser:
            self.role = self.Role.OWNER
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
