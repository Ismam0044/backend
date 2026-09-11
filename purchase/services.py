from django.db import transaction
from django.utils import timezone

from accounts.models import CashBookEntry
from inventory.models import Item, Stock
from parties.models import LedgerEntry

from .models import PurchaseInvoice, PurchaseInvoiceItem


def generate_invoice_no(warehouse):
    today = timezone.localdate()
    count = PurchaseInvoice.objects.filter(date=today, warehouse=warehouse).count() + 1
    return f"PI-{warehouse.id}-{today:%Y%m%d}-{count:04d}"


@transaction.atomic
def complete_purchase(*, warehouse, supplier, paid_amount, discount, cart, user, payment_mode=PurchaseInvoice.PaymentMode.CASH):
    if len(cart) == 0:
        raise ValueError("Cart is empty.")

    subtotal = cart.subtotal
    total = subtotal - discount

    invoice = PurchaseInvoice.objects.create(
        invoice_no=generate_invoice_no(warehouse),
        warehouse=warehouse,
        supplier=supplier,
        date=timezone.localdate(),
        subtotal=subtotal,
        discount=discount,
        total=total,
        paid_amount=paid_amount,
        payment_mode=payment_mode,
        status=PurchaseInvoice.Status.CONFIRMED,
        created_by=user,
    )

    for line in cart:
        item = Item.objects.select_for_update().get(pk=line["item_id"])
        stock, _ = Stock.objects.select_for_update().get_or_create(item=item, warehouse=warehouse)
        stock.quantity += line["quantity"]
        stock.save()

        PurchaseInvoiceItem.objects.create(
            invoice=invoice, item=item, quantity=line["quantity"], unit_cost=line["unit_price"]
        )

    due = total - paid_amount
    if due != 0:
        # Owing the supplier more (due > 0) lowers the party's balance (CREDIT);
        # overpaying (due < 0) means the supplier now owes the shop (DEBIT).
        LedgerEntry.objects.create(
            party=supplier,
            date=invoice.date,
            entry_type=LedgerEntry.EntryType.CREDIT if due > 0 else LedgerEntry.EntryType.DEBIT,
            amount=abs(due),
            reference=invoice.invoice_no,
            description=f"Purchase invoice {invoice.invoice_no}",
            created_by=user,
        )

    if payment_mode == PurchaseInvoice.PaymentMode.CASH and paid_amount > 0:
        CashBookEntry.objects.create(
            warehouse=warehouse,
            date=invoice.date,
            entry_type=CashBookEntry.EntryType.OUT,
            amount=paid_amount,
            category="Purchase",
            reference=invoice.invoice_no,
            description=f"Payment for purchase {invoice.invoice_no} ({supplier.name})",
            created_by=user,
        )

    cart.clear()
    return invoice
