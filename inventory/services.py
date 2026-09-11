from django.db import transaction

from .models import Stock, StockTransfer, StockTransferItem


class InsufficientStockError(Exception):
    pass


@transaction.atomic
def complete_transfer(*, from_warehouse, to_warehouse, date, lines, user, note=""):
    """lines: iterable of {"item": Item, "quantity": Decimal}."""
    if from_warehouse == to_warehouse:
        raise ValueError("Source and destination warehouse must be different.")
    if not lines:
        raise ValueError("No items to transfer.")

    transfer = StockTransfer.objects.create(
        from_warehouse=from_warehouse, to_warehouse=to_warehouse, date=date,
        status=StockTransfer.Status.COMPLETED, note=note, created_by=user,
    )

    for line in lines:
        item, quantity = line["item"], line["quantity"]
        source_stock = Stock.objects.select_for_update().filter(item=item, warehouse=from_warehouse).first()
        if not source_stock or source_stock.quantity < quantity:
            have = source_stock.quantity if source_stock else 0
            raise InsufficientStockError(
                f"Not enough stock for {item.name} at {from_warehouse.name} (have {have}, need {quantity})."
            )
        source_stock.quantity -= quantity
        source_stock.save()

        dest_stock, _ = Stock.objects.select_for_update().get_or_create(item=item, warehouse=to_warehouse)
        dest_stock.quantity += quantity
        dest_stock.save()

        StockTransferItem.objects.create(transfer=transfer, item=item, quantity=quantity)

    return transfer
