from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.cart import SessionCart
from core.models import Warehouse
from core.utils import resolve_warehouse
from inventory.models import Item
from parties.models import Party

from .models import PurchaseInvoice
from .services import complete_purchase

CART_SESSION_KEY = "purchase_cart"


def _accessible_warehouses(user):
    if user.role == user.Role.OWNER or not user.assigned_warehouses.exists():
        return Warehouse.objects.filter(is_active=True)
    return user.assigned_warehouses.filter(is_active=True)


def _current_warehouse(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse_id = request.session.get("purchase_warehouse_id")
    warehouse = resolve_warehouse(warehouses, warehouse_id)
    return warehouse or warehouses.first()


def _cart_context(request, warehouse):
    cart = SessionCart(request, CART_SESSION_KEY)
    lines = list(cart)
    return {"cart_lines": lines, "cart_subtotal": cart.subtotal, "warehouse": warehouse}


@login_required
def entry(request):
    warehouses = _accessible_warehouses(request.user)
    warehouse = _current_warehouse(request)
    if warehouse:
        request.session["purchase_warehouse_id"] = warehouse.id

    context = {
        "warehouses": warehouses,
        "suppliers": Party.objects.filter(is_active=True, type__in=[Party.Type.SUPPLIER, Party.Type.BOTH]).order_by("name"),
        **_cart_context(request, warehouse),
    }
    return render(request, "purchase/entry.html", context)


@login_required
def set_warehouse(request):
    warehouse_id = request.GET.get("warehouse_id") or request.POST.get("warehouse_id")
    warehouses = _accessible_warehouses(request.user)
    warehouse = resolve_warehouse(warehouses, warehouse_id)
    if warehouse:
        request.session["purchase_warehouse_id"] = warehouse.id
    return item_search(request)


@login_required
def item_search(request):
    q = request.GET.get("q", "").strip()
    items = Item.objects.filter(is_active=True)
    if q:
        items = items.filter(name__icontains=q) | items.filter(code__icontains=q)
    items = items.select_related("unit")[:30]
    return render(request, "purchase/_item_grid.html", {"items": items})


@login_required
@require_POST
def add_to_cart(request):
    warehouse = _current_warehouse(request)
    item = get_object_or_404(Item, pk=request.POST.get("item_id"), is_active=True)
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.add(item, quantity=1, unit_price=item.cost_price)
    return render(request, "purchase/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def update_cart_line(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    field = request.POST.get("field", "quantity")
    item_id = request.POST.get("item_id")
    try:
        value = Decimal(request.POST.get("value", "0"))
    except InvalidOperation:
        value = Decimal("0")

    if field == "unit_price":
        cart.set_unit_price(item_id, value)
    else:
        cart.set_quantity(item_id, value)
    return render(request, "purchase/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def remove_cart_line(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    cart.remove(request.POST.get("item_id"))
    return render(request, "purchase/_cart_update.html", _cart_context(request, warehouse))


@login_required
@require_POST
def checkout(request):
    warehouse = _current_warehouse(request)
    cart = SessionCart(request, CART_SESSION_KEY)
    supplier = get_object_or_404(Party, pk=request.POST.get("supplier_id")) if request.POST.get("supplier_id") else None

    try:
        discount = Decimal(request.POST.get("discount") or "0")
        paid_amount = Decimal(request.POST.get("paid_amount") or "0")
    except InvalidOperation:
        messages.error(request, "Invalid amount entered.")
        return redirect("purchase:entry")

    if not warehouse:
        messages.error(request, "No warehouse available for this user.")
        return redirect("purchase:entry")
    if not supplier:
        messages.error(request, "Please select a supplier.")
        return redirect("purchase:entry")

    try:
        invoice = complete_purchase(
            warehouse=warehouse,
            supplier=supplier,
            paid_amount=paid_amount,
            discount=discount,
            cart=cart,
            user=request.user,
            payment_mode=request.POST.get("payment_mode", PurchaseInvoice.PaymentMode.CASH),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("purchase:entry")

    messages.success(request, f"Purchase recorded: {invoice.invoice_no}")
    return redirect("purchase:detail", pk=invoice.pk)


@login_required
def detail(request, pk):
    invoice = get_object_or_404(PurchaseInvoice.objects.select_related("supplier", "warehouse"), pk=pk)
    return render(request, "purchase/detail.html", {"invoice": invoice, "items": invoice.items.select_related("item")})
