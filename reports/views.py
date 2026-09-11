from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import render
from django.utils import timezone

from core.models import Warehouse
from inventory.models import Stock
from parties.models import Party
from sales.models import SalesInvoice


@login_required
def index(request):
    return render(request, "reports/index.html")


@login_required
def low_stock(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse_id = request.GET.get("warehouse_id")

    stocks = Stock.objects.select_related("item", "warehouse", "item__unit").filter(
        quantity__lte=F("item__reorder_level")
    ).order_by("quantity")
    if warehouse_id:
        stocks = stocks.filter(warehouse_id=warehouse_id)

    low_items = list(stocks)

    return render(request, "reports/low_stock.html", {
        "warehouses": warehouses,
        "selected_warehouse_id": warehouse_id,
        "low_items": low_items,
    })


@login_required
def dues(request):
    parties = Party.objects.filter(is_active=True).with_balance()
    rows = [{"party": p, "balance": p.balance} for p in parties]
    rows = [r for r in rows if r["balance"] != 0]

    receivables = sorted([r for r in rows if r["balance"] > 0], key=lambda r: -r["balance"])
    payables = sorted([r for r in rows if r["balance"] < 0], key=lambda r: r["balance"])

    total_receivable = sum((r["balance"] for r in receivables), 0)
    total_payable = sum((-r["balance"] for r in payables), 0)

    return render(request, "reports/dues.html", {
        "receivables": receivables,
        "payables": payables,
        "total_receivable": total_receivable,
        "total_payable": total_payable,
    })


@login_required
def daily_sales(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse_id = request.GET.get("warehouse_id")
    the_date = request.GET.get("date") or timezone.localdate().isoformat()

    invoices = SalesInvoice.objects.filter(date=the_date).select_related("warehouse", "party")
    if warehouse_id:
        invoices = invoices.filter(warehouse_id=warehouse_id)
    invoices = invoices.order_by("-id")

    totals = invoices.aggregate(total=Sum("total"), paid=Sum("paid_amount"))
    total_sales = totals["total"] or 0
    total_paid = totals["paid"] or 0

    return render(request, "reports/daily_sales.html", {
        "warehouses": warehouses,
        "selected_warehouse_id": warehouse_id,
        "the_date": the_date,
        "invoices": invoices,
        "total_sales": total_sales,
        "total_paid": total_paid,
        "total_due": total_sales - total_paid,
    })
