from decimal import Decimal

from rest_framework import serializers

from assistant.models import ChatQuery, ScannedReceipt


class ChatQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatQuery
        fields = ["id", "question", "answer", "error", "created_at"]


class ChatAskSerializer(serializers.Serializer):
    question = serializers.CharField(allow_blank=False)


class ReorderSummarizeSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField(required=False, allow_null=True)


class ScannedReceiptSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ScannedReceipt
        fields = [
            "id", "image_url", "status", "status_display",
            "extracted_data", "purchase_invoice", "error", "created_at",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class ReceiptConfirmLineSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class ReceiptConfirmSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField()
    supplier_id = serializers.IntegerField()
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    lines = ReceiptConfirmLineSerializer(many=True, allow_empty=False)
