from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Voucher
from core.utils import accessible_warehouses, resolve_warehouse

from .models import LedgerEntry, Party
from .services import record_transaction as record_transaction_service


@login_required
def party_list(request):
    q = request.GET.get("q", "").strip()
    parties = Party.objects.filter(is_active=True).with_balance()
    if q:
        parties = parties.filter(name__icontains=q)
    rows = [{"party": p, "balance": p.balance} for p in parties.order_by("name")]
    return render(request, "parties/list.html", {"rows": rows, "q": q})


@login_required
def party_detail(request, pk):
    party = get_object_or_404(Party, pk=pk)
    entries = party.ledger_entries.order_by("date", "id")

    running = party.opening_balance
    history = []
    for e in entries:
        running += e.amount if e.entry_type == LedgerEntry.EntryType.DEBIT else -e.amount
        history.append({"entry": e, "running_balance": running})
    history.reverse()

    context = {
        "party": party,
        "balance": party.get_balance(),
        "history": history,
        "warehouses": accessible_warehouses(request.user),
    }
    return render(request, "parties/detail.html", context)


@login_required
@require_POST
def record_transaction(request, pk):
    party = get_object_or_404(Party, pk=pk)
    warehouses = accessible_warehouses(request.user)
    warehouse = resolve_warehouse(warehouses, request.POST.get("warehouse_id")) or warehouses.first()

    try:
        amount = Decimal(request.POST.get("amount") or "0")
    except InvalidOperation:
        amount = Decimal("0")

    voucher_type = request.POST.get("voucher_type")  # RECEIPT (collect) or PAYMENT (pay out)
    mode = request.POST.get("mode", Voucher.Mode.CASH)

    if amount <= 0:
        messages.error(request, "Enter an amount greater than zero.")
        return redirect("parties:detail", pk=pk)
    if not warehouse:
        messages.error(request, "No warehouse available for this user.")
        return redirect("parties:detail", pk=pk)

    record_transaction_service(
        party=party, warehouse=warehouse, voucher_type=voucher_type, mode=mode, amount=amount, user=request.user,
    )

    messages.success(request, "Transaction recorded.")
    return redirect("parties:detail", pk=pk)
