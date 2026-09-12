from decimal import Decimal

from rest_framework import serializers

from sales.models import SalesInvoice, SalesInvoiceItem


class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit_short_name = serializers.CharField(source="item.unit.short_name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = SalesInvoiceItem
        fields = ["id", "item", "item_name", "unit_short_name", "quantity", "unit_price", "line_total"]

    def get_line_total(self, obj):
        return float(obj.line_total)


class SalesInvoiceSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    party_name = serializers.CharField(source="party.name", read_only=True, default=None)
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    due_amount = serializers.SerializerMethodField()
    items = SalesInvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = SalesInvoice
        fields = [
            "id", "invoice_no", "warehouse", "warehouse_name", "party", "party_name",
            "date", "payment_type", "payment_type_display", "subtotal", "discount",
            "total", "paid_amount", "due_amount", "status", "status_display",
            "created_at", "items",
        ]

    def get_due_amount(self, obj):
        return float(obj.due_amount)


class CartLineSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class SalesCheckoutSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    party_id = serializers.IntegerField(required=False, allow_null=True)
    payment_type = serializers.ChoiceField(choices=SalesInvoice.PaymentType.choices)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    lines = CartLineSerializer(many=True, allow_empty=False)
