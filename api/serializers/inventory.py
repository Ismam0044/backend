from decimal import Decimal

from rest_framework import serializers

from inventory.models import Item, StockTransfer, StockTransferItem


class ItemSerializer(serializers.ModelSerializer):
    unit_short_name = serializers.CharField(source="unit.short_name", read_only=True)
    stock_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ["id", "name", "code", "unit_short_name", "sale_price", "cost_price", "stock_quantity"]

    def get_stock_quantity(self, obj):
        # Set by the view when a warehouse_id filter is given (see ItemSearchView) -
        # None means "no warehouse context", not "zero stock".
        value = getattr(obj, "_stock_quantity", None)
        return float(value) if value is not None else None


class StockTransferItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit_short_name = serializers.CharField(source="item.unit.short_name", read_only=True)

    class Meta:
        model = StockTransferItem
        fields = ["id", "item", "item_name", "unit_short_name", "quantity"]


class StockTransferSerializer(serializers.ModelSerializer):
    from_warehouse_name = serializers.CharField(source="from_warehouse.name", read_only=True)
    to_warehouse_name = serializers.CharField(source="to_warehouse.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = StockTransferItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id", "from_warehouse", "from_warehouse_name", "to_warehouse", "to_warehouse_name",
            "date", "status", "status_display", "note", "created_at", "items",
        ]


class TransferLineSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class StockTransferCheckoutSerializer(serializers.Serializer):
    from_warehouse_id = serializers.IntegerField()
    to_warehouse_id = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
    lines = TransferLineSerializer(many=True, allow_empty=False)
