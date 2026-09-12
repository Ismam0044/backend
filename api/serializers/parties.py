from decimal import Decimal

from rest_framework import serializers

from accounts.models import Voucher
from parties.models import LedgerEntry, Party


class PartySerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Party
        fields = ["id", "name", "phone", "address", "type", "type_display", "balance"]

    def get_balance(self, obj):
        # .with_balance() annotates `balance`; fall back to opening_balance if a
        # plain (non-annotated) queryset is ever used with this serializer.
        return float(getattr(obj, "balance", obj.opening_balance))


class LedgerEntrySerializer(serializers.ModelSerializer):
    entry_type_display = serializers.CharField(source="get_entry_type_display", read_only=True)
    running_balance = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            "id", "date", "entry_type", "entry_type_display", "amount",
            "reference", "description", "running_balance",
        ]

    def get_running_balance(self, obj):
        # Set by PartyDetailSerializer while walking entries chronologically -
        # mirrors parties/views.py::party_detail's running-balance computation.
        return float(getattr(obj, "_running_balance", 0))


class PartyDetailSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    balance = serializers.SerializerMethodField()
    ledger_entries = serializers.SerializerMethodField()

    class Meta:
        model = Party
        fields = [
            "id", "name", "phone", "address", "type", "type_display",
            "opening_balance", "balance", "ledger_entries",
        ]

    def get_balance(self, obj):
        return float(obj.get_balance())

    def get_ledger_entries(self, obj):
        entries = list(obj.ledger_entries.order_by("date", "id"))
        running = obj.opening_balance
        for entry in entries:
            running += entry.amount if entry.entry_type == LedgerEntry.EntryType.DEBIT else -entry.amount
            entry._running_balance = running
        entries.reverse()  # most recent first, matching the HTMX detail view
        return LedgerEntrySerializer(entries, many=True).data


class RecordTransactionSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    voucher_type = serializers.ChoiceField(choices=Voucher.VoucherType.choices)
    mode = serializers.ChoiceField(choices=Voucher.Mode.choices, default=Voucher.Mode.CASH)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
