from decimal import Decimal

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Warehouse
from core.utils import accessible_warehouses
from inventory.models import Item, Stock, StockTransfer
from inventory.services import InsufficientStockError, complete_transfer

from api.exceptions import ApiValidationError
from api.serializers.inventory import ItemSerializer, StockTransferCheckoutSerializer, StockTransferSerializer


class ItemSearchView(ListAPIView):
    """GET /inventory/items/?q=&code=&warehouse_id= - type-ahead item search for
    POS/Purchase/Transfer item pickers. `code` does an exact lookup (barcode scan
    hits this); `q` does the free-text name/code contains search (mirrors
    sales/views.py::item_search, but with a single Q-object query instead of the
    `queryset | queryset` pattern). Not paginated - a type-ahead grid wants a flat
    array on every keystroke, not a paginated envelope."""

    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        request = self.request
        items_qs = Item.objects.filter(is_active=True).select_related("unit")

        code = request.query_params.get("code", "").strip()
        if code:
            items_qs = items_qs.filter(code__iexact=code)
        else:
            q = request.query_params.get("q", "").strip()
            if q:
                items_qs = items_qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

        items = list(items_qs[:30])

        warehouse_id = request.query_params.get("warehouse_id")
        if warehouse_id:
            warehouse = accessible_warehouses(request.user).filter(pk=warehouse_id).first()
            if warehouse:
                stock_by_item = {
                    s.item_id: s.quantity
                    for s in Stock.objects.filter(warehouse=warehouse, item__in=items)
                }
                for item in items:
                    item._stock_quantity = stock_by_item.get(item.id, Decimal("0"))

        return items


class StockTransferCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StockTransferCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from_warehouse = get_object_or_404(Warehouse, pk=data["from_warehouse_id"], is_active=True)
        to_warehouse = get_object_or_404(Warehouse, pk=data["to_warehouse_id"], is_active=True)
        if not request.user.has_warehouse_access(from_warehouse) or not request.user.has_warehouse_access(to_warehouse):
            raise PermissionDenied("You don't have access to one of these warehouses.")

        # complete_transfer() wants resolved Item objects, not ids - mirrors how
        # assistant/views.py::scan_confirm resolves items before building its cart.
        lines = []
        for line in data["lines"]:
            item = get_object_or_404(Item, pk=line["item_id"])
            lines.append({"item": item, "quantity": line["quantity"]})

        try:
            transfer = complete_transfer(
                from_warehouse=from_warehouse,
                to_warehouse=to_warehouse,
                date=timezone.localdate(),
                lines=lines,
                user=request.user,
                note=data["note"],
            )
        except InsufficientStockError as exc:
            raise ApiValidationError(str(exc), code="insufficient_stock")
        except ValueError as exc:
            raise ApiValidationError(str(exc), code="invalid_transfer")

        return Response(StockTransferSerializer(transfer).data, status=201)


class StockTransferListView(ListAPIView):
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            StockTransfer.objects.select_related("from_warehouse", "to_warehouse")
            .prefetch_related("items__item__unit")
            .order_by("-id")
        )


class StockTransferDetailView(RetrieveAPIView):
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated]
    queryset = StockTransfer.objects.select_related("from_warehouse", "to_warehouse").prefetch_related("items__item__unit")
