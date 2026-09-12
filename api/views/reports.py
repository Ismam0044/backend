from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Stock
from parties.models import Party
from sales.models import SalesInvoice


class LowStockReportView(APIView):
    """GET /reports/low-stock/?warehouse_id= - mirrors reports/views.py::low_stock."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        stocks = (
            Stock.objects.select_related("item", "warehouse", "item__unit")
            .filter(quantity__lte=F("item__reorder_level"))
            .order_by("quantity")
        )
        if warehouse_id:
            stocks = stocks.filter(warehouse_id=warehouse_id)

        return Response([
            {
                "item_id": s.item_id,
                "item_name": s.item.name,
                "unit_short_name": s.item.unit.short_name,
                "warehouse_name": s.warehouse.name,
                "quantity": float(s.quantity),
                "reorder_level": float(s.item.reorder_level),
            }
            for s in stocks
        ])


class DuesReportView(APIView):
    """GET /reports/dues/ - mirrors reports/views.py::dues."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        parties = Party.objects.filter(is_active=True).with_balance()
        rows = [(p, p.balance) for p in parties if p.balance != 0]

        receivables = sorted([r for r in rows if r[1] > 0], key=lambda r: -r[1])
        payables = sorted([r for r in rows if r[1] < 0], key=lambda r: r[1])

        return Response({
            "receivables": [{"party_id": p.id, "name": p.name, "balance": float(b)} for p, b in receivables],
            "payables": [{"party_id": p.id, "name": p.name, "balance": float(-b)} for p, b in payables],
            "total_receivable": float(sum((b for _, b in receivables), Decimal("0"))),
            "total_payable": float(sum((-b for _, b in payables), Decimal("0"))),
        })


class DailySalesReportView(APIView):
    """GET /reports/daily-sales/?warehouse_id=&date= - mirrors reports/views.py::daily_sales."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        the_date = request.query_params.get("date") or timezone.localdate().isoformat()

        invoices = SalesInvoice.objects.filter(date=the_date).select_related("warehouse", "party")
        if warehouse_id:
            invoices = invoices.filter(warehouse_id=warehouse_id)
        invoices = invoices.order_by("-id")

        totals = invoices.aggregate(total=Sum("total"), paid=Sum("paid_amount"))
        total_sales = totals["total"] or 0
        total_paid = totals["paid"] or 0

        return Response({
            "date": the_date,
            "invoices": [
                {
                    "id": inv.id,
                    "invoice_no": inv.invoice_no,
                    "warehouse_name": inv.warehouse.name,
                    "party_name": inv.party.name if inv.party else None,
                    "payment_type": inv.payment_type,
                    "total": float(inv.total),
                    "paid_amount": float(inv.paid_amount),
                    "due_amount": float(inv.due_amount),
                }
                for inv in invoices
            ],
            "total_sales": float(total_sales),
            "total_paid": float(total_paid),
            "total_due": float(total_sales - total_paid),
        })
