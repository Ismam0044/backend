from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Warehouse
from parties.models import Party
from sales.models import SalesInvoice
from sales.services import InsufficientStockError, complete_sale

from api.exceptions import ApiValidationError
from api.serializers.sales import SalesCheckoutSerializer, SalesInvoiceSerializer


class _ApiCart:
    """Duck-typed cart for complete_sale() - same shape as assistant/views.py's
    ReceiptCart (__iter__ yielding {item_id, quantity, unit_price}, __len__,
    .subtotal, .clear()), built from validated request data instead of a
    session. complete_sale() itself is called completely unmodified."""

    def __init__(self, lines):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)

    def __len__(self):
        return len(self._lines)

    @property
    def subtotal(self):
        return sum((line["quantity"] * line["unit_price"] for line in self._lines), Decimal("0"))

    def clear(self):
        pass  # nothing to clear - the cart never lived server-side


class SalesCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SalesCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        warehouse = get_object_or_404(Warehouse, pk=data["warehouse_id"], is_active=True)
        if not request.user.has_warehouse_access(warehouse):
            raise PermissionDenied("You don't have access to this warehouse.")

        party = None
        if data.get("party_id"):
            party = get_object_or_404(Party, pk=data["party_id"])

        try:
            invoice = complete_sale(
                warehouse=warehouse,
                party=party,
                payment_type=data["payment_type"],
                paid_amount=data["paid_amount"],
                discount=data["discount"],
                cart=_ApiCart(data["lines"]),
                user=request.user,
            )
        except InsufficientStockError as exc:
            raise ApiValidationError(str(exc), code="insufficient_stock")
        except ValueError as exc:
            raise ApiValidationError(str(exc), code="invalid_cart")

        return Response(SalesInvoiceSerializer(invoice).data, status=201)


class SalesInvoiceListView(ListAPIView):
    serializer_class = SalesInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            SalesInvoice.objects.select_related("warehouse", "party")
            .prefetch_related("items__item__unit")
            .order_by("-id")
        )


class SalesInvoiceDetailView(RetrieveAPIView):
    serializer_class = SalesInvoiceSerializer
    permission_classes = [IsAuthenticated]
    queryset = SalesInvoice.objects.select_related("warehouse", "party").prefetch_related("items__item__unit")
