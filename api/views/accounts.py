from datetime import timedelta

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CashBookEntry
from core.models import Warehouse

from api.serializers.accounts import CashBookEntryCreateSerializer, CashBookEntrySerializer


class CashBookListView(ListAPIView):
    """GET /accounts/cashbook/?warehouse_id=&date_from=&date_to= - mirrors
    accounts/views.py::cash_book (defaults to the last 30 days)."""

    serializer_class = CashBookEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = self.request
        today = timezone.localdate()
        date_from = request.query_params.get("date_from") or (today - timedelta(days=30)).isoformat()
        date_to = request.query_params.get("date_to") or today.isoformat()

        entries = CashBookEntry.objects.filter(date__gte=date_from, date__lte=date_to).select_related("warehouse")
        warehouse_id = request.query_params.get("warehouse_id")
        if warehouse_id:
            entries = entries.filter(warehouse_id=warehouse_id)
        return entries.order_by("-date", "-id")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        totals = self.get_queryset().aggregate(
            cash_in=Sum("amount", filter=Q(entry_type=CashBookEntry.EntryType.IN)),
            cash_out=Sum("amount", filter=Q(entry_type=CashBookEntry.EntryType.OUT)),
        )
        cash_in = float(totals["cash_in"] or 0)
        cash_out = float(totals["cash_out"] or 0)
        response.data["totals"] = {"cash_in": cash_in, "cash_out": cash_out, "net": cash_in - cash_out}
        return response


class CashBookCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CashBookEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        warehouse = get_object_or_404(Warehouse, pk=data["warehouse_id"], is_active=True)
        if not request.user.has_warehouse_access(warehouse):
            raise PermissionDenied("You don't have access to this warehouse.")

        entry = CashBookEntry.objects.create(
            warehouse=warehouse,
            date=data.get("date") or timezone.localdate(),
            entry_type=data["entry_type"],
            amount=data["amount"],
            category=data.get("category", ""),
            description=data.get("description", ""),
            created_by=request.user,
        )
        return Response(CashBookEntrySerializer(entry).data, status=201)
