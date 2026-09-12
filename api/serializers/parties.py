from rest_framework import serializers

from parties.models import Party


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
