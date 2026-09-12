from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Warehouse
from parties.models import Party
from purchase.models import PurchaseInvoice
from purchase.services import complete_purchase

from api.exceptions import ApiValidationError
from api.serializers.purchase import PurchaseCheckoutSerializer, PurchaseInvoiceSerializer


class _ApiCart:
    """Same duck-typed cart shape as sales' _ApiCart - complete_purchase() is
    called completely unmodified."""

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
        pass


class PurchaseCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseCheckoutSerializer(data=request.data)
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
                discount=data["discount"],
                cart=_ApiCart(data["lines"]),
                user=request.user,
                payment_mode=data["payment_mode"],
            )
        except ValueError as exc:
            raise ApiValidationError(str(exc), code="invalid_cart")

        return Response(PurchaseInvoiceSerializer(invoice).data, status=201)


class PurchaseInvoiceListView(ListAPIView):
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            PurchaseInvoice.objects.select_related("warehouse", "supplier")
            .prefetch_related("items__item__unit")
            .order_by("-id")
        )


class PurchaseInvoiceDetailView(RetrieveAPIView):
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [IsAuthenticated]
    queryset = PurchaseInvoice.objects.select_related("warehouse", "supplier").prefetch_related("items__item__unit")
