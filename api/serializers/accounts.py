from decimal import Decimal

from rest_framework import serializers

from accounts.models import CashBookEntry


class CashBookEntrySerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    entry_type_display = serializers.CharField(source="get_entry_type_display", read_only=True)

    class Meta:
        model = CashBookEntry
        fields = [
            "id", "warehouse", "warehouse_name", "date", "entry_type", "entry_type_display",
            "amount", "category", "reference", "description", "created_at",
        ]


class CashBookEntryCreateSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    date = serializers.DateField(required=False)
    entry_type = serializers.ChoiceField(choices=CashBookEntry.EntryType.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    category = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
