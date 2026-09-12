from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.models import ChatQuery, ScannedReceipt
from assistant.services import (
    ask_business_question,
    compute_reorder_suggestions,
    extract_receipt_data,
    match_item_by_name,
    summarize_reorder_suggestions,
)
from core.models import Warehouse
from parties.models import Party
from purchase.services import complete_purchase

from api.exceptions import ApiValidationError
from api.serializers.assistant import (
    ChatAskSerializer,
    ChatQuerySerializer,
    ReceiptConfirmSerializer,
    ReorderSummarizeSerializer,
    ScannedReceiptSerializer,
)
from api.serializers.purchase import PurchaseInvoiceSerializer
from api.views.purchase import _ApiCart


class ChatAskView(APIView):
    """POST {question} -> ask_business_question() unmodified. That function
    already catches its own exceptions onto ChatQuery.error and always
    returns a saved record, so nothing extra to catch here."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = ask_business_question(serializer.validated_data["question"], request.user)
        return Response(ChatQuerySerializer(query).data, status=201)


class ChatHistoryView(ListAPIView):
    serializer_class = ChatQuerySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ChatQuery.objects.filter(user=self.request.user)[:20]


class ReorderSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id) if warehouse_id else None
        suggestions = compute_reorder_suggestions(warehouse=warehouse)
        return Response([
            {
                "item_id": s["item"].id,
                "item_name": s["item"].name,
                "unit_short_name": s["item"].unit.short_name,
                "warehouse_id": s["warehouse"].id,
                "warehouse_name": s["warehouse"].name,
                "current_stock": float(s["current_stock"]),
                "daily_velocity": float(s["daily_velocity"]),
                "suggested_qty": float(s["suggested_qty"]),
            }
            for s in suggestions
        ])


class ReorderSummarizeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReorderSummarizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse_id = serializer.validated_data.get("warehouse_id")
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id) if warehouse_id else None
        suggestions = compute_reorder_suggestions(warehouse=warehouse)
        try:
            summary = summarize_reorder_suggestions(suggestions)
        except Exception as exc:  # noqa: BLE001 - surface any Gemini/API error to the app
            raise ApiValidationError(str(exc), code="ai_error")
        return Response({"summary": summary})


class ReceiptListView(ListAPIView):
    serializer_class = ScannedReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ScannedReceipt.objects.select_related("uploaded_by", "purchase_invoice")[:30]

    def get_serializer_context(self):
        return {"request": self.request}


class ReceiptUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            raise ApiValidationError("Choose an image to upload.", code="missing_image")

        receipt = ScannedReceipt.objects.create(image=image, uploaded_by=request.user)
        try:
            with receipt.image.open("rb") as f:
                image_bytes = f.read()
            mime_type = image.content_type or "image/jpeg"
            data = extract_receipt_data(image_bytes, mime_type=mime_type)
            receipt.extracted_data = data
            receipt.save(update_fields=["extracted_data"])
        except Exception as exc:  # noqa: BLE001 - surface any API/parse error to the app
            receipt.status = ScannedReceipt.Status.FAILED
            receipt.error = str(exc)
            receipt.save(update_fields=["status", "error"])

        return Response(ScannedReceiptSerializer(receipt, context={"request": request}).data, status=201)


class ReceiptDetailView(APIView):
    """GET a receipt with per-line item matches - mirrors assistant/views.py::scan_review."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        receipt = get_object_or_404(ScannedReceipt, pk=pk)
        data = receipt.extracted_data or {}

        lines = []
        for line in data.get("items", []):
            matched = match_item_by_name(line.get("name", ""))
            lines.append({
                "raw_name": line.get("name", ""),
                "quantity": line.get("quantity", 1),
                "unit_price": line.get("unit_price", 0),
                "matched_item_id": matched.id if matched else None,
                "matched_item_name": matched.name if matched else None,
            })

        payload = ScannedReceiptSerializer(receipt, context={"request": request}).data
        payload["lines"] = lines
        payload["extracted_supplier"] = data.get("supplier_name", "")
        payload["extracted_date"] = data.get("date", "")
        return Response(payload)


class ReceiptConfirmView(APIView):
    """POST matched lines -> complete_purchase() unmodified, same duck-typed
    cart pattern as assistant/views.py::scan_confirm."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        receipt = get_object_or_404(ScannedReceipt, pk=pk)
        serializer = ReceiptConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        warehouse = get_object_or_404(Warehouse, pk=data["warehouse_id"], is_active=True)
        if not request.user.has_warehouse_access(warehouse):
            raise PermissionDenied("You don't have access to this warehouse.")
        supplier = get_object_or_404(Party, pk=data["supplier_id"])

        try:
            invoice = complete_purchase(
                warehouse=warehouse,
                supplier=supplier,
                paid_amount=data["paid_amount"],
                discount=Decimal("0"),
                cart=_ApiCart(data["lines"]),
                user=request.user,
            )
        except ValueError as exc:
            raise ApiValidationError(str(exc), code="invalid_cart")

        receipt.status = ScannedReceipt.Status.CONVERTED
        receipt.purchase_invoice = invoice
        receipt.save(update_fields=["status", "purchase_invoice"])

        return Response(PurchaseInvoiceSerializer(invoice).data, status=201)


class ReceiptDiscardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        receipt = get_object_or_404(ScannedReceipt, pk=pk)
        receipt.status = ScannedReceipt.Status.DISCARDED
        receipt.save(update_fields=["status"])
        return Response(status=204)
