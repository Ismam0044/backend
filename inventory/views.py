from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.cart import SessionCart
from core.models import Warehouse
from core.utils import resolve_warehouse

from .models import Item, Stock
from .services import InsufficientStockError, complete_transfer

CART_SESSION_KEY = "transfer_cart"


def _cart_context(request):
    cart = SessionCart(request, CART_SESSION_KEY)
    return {"cart_lines": list(cart)}


@login_required
def transfer_entry(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    from_warehouse = resolve_warehouse(warehouses, request.session.get("transfer_from_id")) or warehouses.first()
    context = {
        "warehouses": warehouses,
        "from_warehouse": from_warehouse,
        **_cart_context(request),
    }
    return render(request, "inventory/transfer.html", context)


@login_required
def set_from_warehouse(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse = resolve_warehouse(warehouses, request.GET.get("from_warehouse_id"))
    if warehouse:
        request.session["transfer_from_id"] = warehouse.id
    return item_search(request)


@login_required
def item_search(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    from_warehouse = resolve_warehouse(warehouses, request.session.get("transfer_from_id")) or warehouses.first()
    q = request.GET.get("q", "").strip()
    items = Item.objects.filter(is_active=True)
    if q:
        items = items.filter(name__icontains=q) | items.filter(code__icontains=q)
    items = items.select_related("unit")[:30]

    stock_by_item = {}
    if from_warehouse:
        stock_by_item = {s.item_id: s.quantity for s in Stock.objects.filter(warehouse=from_warehouse, item__in=items)}

    tiles = [{"item": item, "stock": stock_by_item.get(item.id, 0)} for item in items]
    return render(request, "inventory/_item_grid.html", {"tiles": tiles})


@login_required
@require_POST
def add_to_cart(request):
    item = get_object_or_404(Item, pk=request.POST.get("item_id"), is_active=True)
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.add(item, quantity=1, unit_price=Decimal("0"))
    return render(request, "inventory/_cart_items.html", _cart_context(request))


@login_required
@require_POST
def update_cart_line(request):
    cart = SessionCart(request, CART_SESSION_KEY)
    try:
        quantity = Decimal(request.POST.get("quantity", "0"))
    except InvalidOperation:
        quantity = Decimal("0")
    cart.set_quantity(request.POST.get("item_id"), quantity)
    return render(request, "inventory/_cart_items.html", _cart_context(request))


@login_required
@require_POST
def remove_cart_line(request):
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.remove(request.POST.get("item_id"))
    return render(request, "inventory/_cart_items.html", _cart_context(request))


@login_required
@require_POST
def checkout(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    from_warehouse = resolve_warehouse(warehouses, request.POST.get("from_warehouse_id"))
    to_warehouse = resolve_warehouse(warehouses, request.POST.get("to_warehouse_id"))
    cart = SessionCart(request, CART_SESSION_KEY)

    if not from_warehouse or not to_warehouse:
        messages.error(request, "Select both a source and destination warehouse.")
        return redirect("inventory:transfer_entry")

    lines = [{"item": Item.objects.get(pk=l["item_id"]), "quantity": l["quantity"]} for l in cart]

    try:
        transfer = complete_transfer(
            from_warehouse=from_warehouse, to_warehouse=to_warehouse, date=timezone.localdate(),
            lines=lines, user=request.user, note=request.POST.get("note", ""),
        )
    except (InsufficientStockError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect("inventory:transfer_entry")

    cart.clear()
    messages.success(request, f"Transfer #{transfer.pk} completed: {from_warehouse.name} -> {to_warehouse.name}")
    return redirect("inventory:transfer_entry")
