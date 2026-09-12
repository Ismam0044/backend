from rest_framework import serializers

from inventory.models import Item


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
