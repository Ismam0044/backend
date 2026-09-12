from django.utils import timezone

from accounts.models import Voucher

from .models import LedgerEntry


def record_transaction(*, party, warehouse, voucher_type, mode, amount, user):
    """Records a payment/receipt against a party: a Voucher (audit trail) plus
    the LedgerEntry that actually moves the party's balance. Extracted from
    parties/views.py::record_transaction so both the HTMX view and the API can
    call the same logic."""
    today = timezone.localdate()
    voucher = Voucher.objects.create(
        voucher_type=voucher_type,
        warehouse=warehouse,
        party=party,
        date=today,
        amount=amount,
        mode=mode,
        description=f"{voucher_type.title()} against {party.name}",
        created_by=user,
    )
    LedgerEntry.objects.create(
        party=party,
        date=today,
        entry_type=LedgerEntry.EntryType.CREDIT if voucher_type == Voucher.VoucherType.RECEIPT else LedgerEntry.EntryType.DEBIT,
        amount=amount,
        reference=f"{voucher_type}-{timezone.now():%Y%m%d%H%M%S}",
        description=f"{voucher_type.title()} ({mode})",
        created_by=user,
    )
    return voucher
