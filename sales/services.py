from django.db import transaction
from django.utils import timezone

from accounts.models import CashBookEntry
from inventory.models import Item, Stock
from parties.models import LedgerEntry

from .models import SalesInvoice, SalesInvoiceItem


class InsufficientStockError(Exception):
    pass


def generate_invoice_no(warehouse):
    today = timezone.localdate()
    count = SalesInvoice.objects.filter(date=today, warehouse=warehouse).count() + 1
    return f"SI-{warehouse.id}-{today:%Y%m%d}-{count:04d}"


@transaction.atomic
def complete_sale(*, warehouse, party, payment_type, paid_amount, discount, cart, user):
    if len(cart) == 0:
        raise ValueError("Cart is empty.")

    subtotal = cart.subtotal
    total = subtotal - discount

    invoice = SalesInvoice.objects.create(
        invoice_no=generate_invoice_no(warehouse),
        warehouse=warehouse,
        party=party,
        date=timezone.localdate(),
        payment_type=payment_type,
        subtotal=subtotal,
        discount=discount,
        total=total,
        paid_amount=paid_amount,
        status=SalesInvoice.Status.CONFIRMED,
        created_by=user,
    )

    for line in cart:
        item = Item.objects.select_for_update().get(pk=line["item_id"])
        stock, _ = Stock.objects.select_for_update().get_or_create(item=item, warehouse=warehouse)
        if stock.quantity < line["quantity"]:
            raise InsufficientStockError(
                f"Not enough stock for {item.name} at {warehouse.name} "
                f"(have {stock.quantity}, need {line['quantity']})."
            )
        stock.quantity -= line["quantity"]
        stock.save()

        SalesInvoiceItem.objects.create(
            invoice=invoice, item=item, quantity=line["quantity"], unit_price=line["unit_price"]
        )

    due = total - paid_amount
    if party and due != 0:
        LedgerEntry.objects.create(
            party=party,
            date=invoice.date,
            entry_type=LedgerEntry.EntryType.DEBIT if due > 0 else LedgerEntry.EntryType.CREDIT,
            amount=abs(due),
            reference=invoice.invoice_no,
            description=f"Sales invoice {invoice.invoice_no}",
            created_by=user,
        )

    if payment_type == SalesInvoice.PaymentType.CASH and paid_amount > 0:
        CashBookEntry.objects.create(
            warehouse=warehouse,
            date=invoice.date,
            entry_type=CashBookEntry.EntryType.IN,
            amount=paid_amount,
            category="Sales",
            reference=invoice.invoice_no,
            description=f"Sale {invoice.invoice_no}" + (f" ({party.name})" if party else ""),
            created_by=user,
        )

    cart.clear()
    return invoice
