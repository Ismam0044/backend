from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Warehouse
from parties.models import Party
from parties.services import record_transaction

from api.serializers.parties import PartyDetailSerializer, PartySerializer, RecordTransactionSerializer


class PartyListView(ListAPIView):
    """GET /parties/?q=&type= - customer/supplier picker (POS/Purchase) and the
    parties list screen. Built on Party.objects.with_balance() (reused as-is)."""

    serializer_class = PartySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        request = self.request
        parties = Party.objects.filter(is_active=True).with_balance()

        q = request.query_params.get("q", "").strip()
        if q:
            parties = parties.filter(name__icontains=q)

        party_type = request.query_params.get("type")
        if party_type:
            parties = parties.filter(type=party_type)

        return parties.order_by("name")[:50]


class PartyDetailView(APIView):
    """GET a party with its full ledger history (running balance included) -
    mirrors parties/views.py::party_detail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        return Response(PartyDetailSerializer(party).data)


class RecordTransactionView(APIView):
    """POST a payment/receipt against a party - creates the Voucher + LedgerEntry
    pair via parties.services.record_transaction() unmodified."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        serializer = RecordTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        warehouse = get_object_or_404(Warehouse, pk=data["warehouse_id"], is_active=True)
        if not request.user.has_warehouse_access(warehouse):
            raise PermissionDenied("You don't have access to this warehouse.")

        record_transaction(
            party=party,
            warehouse=warehouse,
            voucher_type=data["voucher_type"],
            mode=data["mode"],
            amount=data["amount"],
            user=request.user,
        )
        return Response(PartyDetailSerializer(party).data, status=201)
