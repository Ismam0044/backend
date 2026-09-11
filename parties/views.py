from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Voucher
from core.models import Warehouse
from core.utils import resolve_warehouse

from .models import LedgerEntry, Party


def _accessible_warehouses(user):
    if user.role == user.Role.OWNER or not user.assigned_warehouses.exists():
        return Warehouse.objects.filter(is_active=True)
    return user.assigned_warehouses.filter(is_active=True)


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
        "warehouses": _accessible_warehouses(request.user),
    }
    return render(request, "parties/detail.html", context)


@login_required
@require_POST
def record_transaction(request, pk):
    party = get_object_or_404(Party, pk=pk)
    warehouses = _accessible_warehouses(request.user)
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

    today = timezone.localdate()
    Voucher.objects.create(
        voucher_type=voucher_type,
        warehouse=warehouse,
        party=party,
        date=today,
        amount=amount,
        mode=mode,
        description=f"{voucher_type.title()} against {party.name}",
        created_by=request.user,
    )
    LedgerEntry.objects.create(
        party=party,
        date=today,
        entry_type=LedgerEntry.EntryType.CREDIT if voucher_type == Voucher.VoucherType.RECEIPT else LedgerEntry.EntryType.DEBIT,
        amount=amount,
        reference=f"{voucher_type}-{timezone.now():%Y%m%d%H%M%S}",
        description=f"{voucher_type.title()} ({mode})",
        created_by=request.user,
    )

    messages.success(request, "Transaction recorded.")
    return redirect("parties:detail", pk=pk)
