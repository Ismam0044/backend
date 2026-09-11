from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import accessible_warehouses
from inventory.models import Stock
from parties.models import Party
from sales.models import SalesInvoice

from api.serializers.core import WarehouseSerializer


class WarehouseListView(ListAPIView):
    """Warehouses this user can operate in. Flat list (not paginated) - a warehouse
    picker wants a plain array, and the set is always small."""

    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return accessible_warehouses(self.request.user)


class DashboardView(APIView):
    """Mirrors core.views.dashboard's summary numbers for the mobile home screen."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        todays_sales = SalesInvoice.objects.filter(date=today).aggregate(total=Sum("total"))["total"] or 0
        low_stock_count = Stock.objects.filter(quantity__lte=F("item__reorder_level")).count()
        balances = [p.balance for p in Party.objects.with_balance() if p.balance > 0]
        total_receivable = sum(balances, 0)

        return Response({
            "todays_sales_bdt": float(todays_sales),
            "low_stock_count": low_stock_count,
            "total_receivable_bdt": float(total_receivable),
            "dues_party_count": len(balances),
        })
