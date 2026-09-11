from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Warehouse
from core.utils import resolve_warehouse

from .models import CashBookEntry


def _accessible_warehouses(user):
    if user.role == user.Role.OWNER or not user.assigned_warehouses.exists():
        return Warehouse.objects.filter(is_active=True)
    return user.assigned_warehouses.filter(is_active=True)


@login_required
def cash_book(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse_id = request.GET.get("warehouse_id")
    today = timezone.localdate()
    date_from = request.GET.get("date_from") or (today - timedelta(days=30)).isoformat()
    date_to = request.GET.get("date_to") or today.isoformat()

    entries = CashBookEntry.objects.filter(date__gte=date_from, date__lte=date_to).select_related("warehouse", "created_by")
    if warehouse_id:
        entries = entries.filter(warehouse_id=warehouse_id)
    entries = entries.order_by("-date", "-id")

    totals = entries.aggregate(
        cash_in=Sum("amount", filter=Q(entry_type=CashBookEntry.EntryType.IN)),
        cash_out=Sum("amount", filter=Q(entry_type=CashBookEntry.EntryType.OUT)),
    )
    cash_in = totals["cash_in"] or Decimal("0")
    cash_out = totals["cash_out"] or Decimal("0")

    context = {
        "warehouses": warehouses,
        "entries": entries,
        "selected_warehouse_id": warehouse_id,
        "date_from": date_from,
        "date_to": date_to,
        "cash_in": cash_in,
        "cash_out": cash_out,
        "net_cash": cash_in - cash_out,
    }
    return render(request, "accounts/cash_book.html", context)


@login_required
@require_POST
def add_cash_entry(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse = resolve_warehouse(warehouses, request.POST.get("warehouse_id"))
    try:
        amount = Decimal(request.POST.get("amount") or "0")
    except InvalidOperation:
        amount = Decimal("0")

    if not warehouse or amount <= 0:
        messages.error(request, "Select a warehouse and enter a valid amount.")
        return redirect("accounts:cash_book")

    CashBookEntry.objects.create(
        warehouse=warehouse,
        date=request.POST.get("date") or timezone.localdate(),
        entry_type=request.POST.get("entry_type", CashBookEntry.EntryType.OUT),
        amount=amount,
        category=request.POST.get("category", ""),
        description=request.POST.get("description", ""),
        created_by=request.user,
    )
    messages.success(request, "Cash book entry recorded.")
    return redirect("accounts:cash_book")
