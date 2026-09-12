from decimal import Decimal

from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from core.utils import accessible_warehouses
from inventory.models import Item, Stock

from api.serializers.inventory import ItemSerializer


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
