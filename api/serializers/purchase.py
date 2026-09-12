from decimal import Decimal

from rest_framework import serializers

from purchase.models import PurchaseInvoice, PurchaseInvoiceItem


class PurchaseInvoiceItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit_short_name = serializers.CharField(source="item.unit.short_name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseInvoiceItem
        fields = ["id", "item", "item_name", "unit_short_name", "quantity", "unit_cost", "line_total"]

    def get_line_total(self, obj):
        return float(obj.line_total)


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    payment_mode_display = serializers.CharField(source="get_payment_mode_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    due_amount = serializers.SerializerMethodField()
    items = PurchaseInvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseInvoice
        fields = [
            "id", "invoice_no", "warehouse", "warehouse_name", "supplier", "supplier_name",
            "date", "payment_mode", "payment_mode_display", "subtotal", "discount",
            "total", "paid_amount", "due_amount", "status", "status_display",
            "created_at", "items",
        ]

    def get_due_amount(self, obj):
        return float(obj.due_amount)


class PurchaseCartLineSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class PurchaseCheckoutSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    supplier_id = serializers.IntegerField()
    payment_mode = serializers.ChoiceField(choices=PurchaseInvoice.PaymentMode.choices)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    lines = PurchaseCartLineSerializer(many=True, allow_empty=False)
