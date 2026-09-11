from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import render
from django.utils import timezone

from inventory.models import Stock
from parties.models import Party
from sales.models import SalesInvoice


@login_required
def dashboard(request):
    today = timezone.localdate()
    todays_sales = SalesInvoice.objects.filter(date=today).aggregate(total=Sum("total"))["total"] or 0
    low_stock_count = Stock.objects.filter(quantity__lte=F("item__reorder_level")).count()
    balances = [p.balance for p in Party.objects.with_balance() if p.balance > 0]
    total_receivable = sum(balances, 0)

    context = {
        "todays_sales": todays_sales,
        "low_stock_count": low_stock_count,
        "total_receivable": total_receivable,
        "dues_party_count": len(balances),
    }
    return render(request, "dashboard.html", context)
