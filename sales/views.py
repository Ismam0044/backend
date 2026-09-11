from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.cart import SessionCart
from core.models import Warehouse
from core.utils import resolve_warehouse
from inventory.models import Item, Stock
from parties.models import Party

from .models import SalesInvoice
from .services import InsufficientStockError, complete_sale

CART_SESSION_KEY = "sales_cart"


def _accessible_warehouses(user):
    if user.role == user.Role.OWNER or not user.assigned_warehouses.exists():
        return Warehouse.objects.filter(is_active=True)
    return user.assigned_warehouses.filter(is_active=True)


def _current_warehouse(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse_id = request.session.get("pos_warehouse_id")
    warehouse = resolve_warehouse(warehouses, warehouse_id)
    return warehouse or warehouses.first()


def _cart_context(request, warehouse):
    cart = SessionCart(request, CART_SESSION_KEY)
    lines = list(cart)
    subtotal = cart.subtotal
    return {"cart_lines": lines, "cart_subtotal": subtotal, "warehouse": warehouse}


@login_required
def pos(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse = _current_warehouse(request)
    if warehouse:
        request.session["pos_warehouse_id"] = warehouse.id

    context = {
        "warehouses": warehouses,
        "parties": Party.objects.filter(is_active=True, type__in=[Party.Type.CUSTOMER, Party.Type.BOTH]).order_by("name"),
        "payment_types": SalesInvoice.PaymentType.choices,
        **_cart_context(request, warehouse),
    }
    return render(request, "sales/pos.html", context)


@login_required
def set_warehouse(request):
    warehouse_id = request.GET.get("warehouse_id") or request.POST.get("warehouse_id")
    warehouses = _accessible_warehouses(request.user)
    warehouse = resolve_warehouse(warehouses, warehouse_id)
    if warehouse:
        request.session["pos_warehouse_id"] = warehouse.id
    return item_search(request)


@login_required
def item_search(request):
    warehouse = _current_warehouse(request)
    q = request.GET.get("q", "").strip()
    items = Item.objects.filter(is_active=True)
    if q:
        items = items.filter(name__icontains=q) | items.filter(code__icontains=q)
    items = items.select_related("unit")[:30]

    stock_by_item = {}
    if warehouse:
        stock_by_item = {
            s.item_id: s.quantity
            for s in Stock.objects.filter(warehouse=warehouse, item__in=items)
        }

    tiles = [
        {"item": item, "stock": stock_by_item.get(item.id, 0)}
        for item in items
    ]
    return render(request, "sales/_item_grid.html", {"tiles": tiles, "warehouse": warehouse})


@login_required
@require_POST
def add_to_cart(request):
    warehouse = _current_warehouse(request)
    item = get_object_or_404(Item, pk=request.POST.get("item_id"), is_active=True)
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.add(item, quantity=1, unit_price=item.sale_price)
    return render(request, "sales/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def update_cart_line(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    try:
        quantity = Decimal(request.POST.get("quantity", "0"))
    except InvalidOperation:
        quantity = Decimal("0")
    cart.set_quantity(request.POST.get("item_id"), quantity)
    return render(request, "sales/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def remove_cart_line(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.remove(request.POST.get("item_id"))
    return render(request, "sales/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def checkout(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    party_id = request.POST.get("party_id")
    party = Party.objects.filter(pk=party_id).first() if party_id else None

    try:
        discount = Decimal(request.POST.get("discount") or "0")
        paid_amount = Decimal(request.POST.get("paid_amount") or "0")
    except InvalidOperation:
        messages.error(request, "Invalid amount entered.")
        return redirect("sales:pos")

    if not warehouse:
        messages.error(request, "No warehouse available for this user.")
        return redirect("sales:pos")

    try:
        invoice = complete_sale(
            warehouse=warehouse,
            party=party,
            payment_type=request.POST.get("payment_type", SalesInvoice.PaymentType.CASH),
            paid_amount=paid_amount,
            discount=discount,
            cart=cart,
            user=request.user,
        )
    except InsufficientStockError as exc:
        messages.error(request, str(exc))
        return redirect("sales:pos")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("sales:pos")

    messages.success(request, f"Sale completed: {invoice.invoice_no}")
    return redirect("sales:receipt", pk=invoice.pk)


@login_required
def receipt(request, pk):
    invoice = get_object_or_404(SalesInvoice.objects.select_related("party", "warehouse"), pk=pk)
    return render(request, "sales/receipt.html", {"invoice": invoice, "items": invoice.items.select_related("item")})
