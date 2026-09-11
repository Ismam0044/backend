from django.conf import settings
from django.db import models


class ChatQuery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_chat_queries")
    question = models.TextField()
    answer = models.TextField(blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Chat queries"

    def __str__(self):
        return self.question[:60]


class ScannedReceipt(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        CONVERTED = "CONVERTED", "Converted to Purchase"
        DISCARDED = "DISCARDED", "Discarded"
        FAILED = "FAILED", "Extraction Failed"

    image = models.ImageField(upload_to="receipts/%Y/%m/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scanned_receipts")
    extracted_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    purchase_invoice = models.ForeignKey(
        "purchase.PurchaseInvoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="scanned_receipt"
    )
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Receipt #{self.pk} ({self.status})"
