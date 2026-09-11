from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import Warehouse
from core.utils import resolve_warehouse
from inventory.models import Item
from parties.models import Party
from purchase.services import complete_purchase

from .models import ChatQuery, ScannedReceipt
from .services import (
    ask_business_question,
    compute_reorder_suggestions,
    extract_receipt_data,
    match_item_by_name,
    summarize_reorder_suggestions,
)


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------

@login_required
def chat_view(request):
    history = list(ChatQuery.objects.filter(user=request.user)[:20])
    history.reverse()
    return render(request, "assistant/chat.html", {"history": history})


@login_required
@require_POST
def chat_ask(request):
    question = request.POST.get("question", "").strip()
    query = ask_business_question(question, request.user) if question else None
    return render(request, "assistant/_chat_turn.html", {"query": query})


# --------------------------------------------------------------------------
# Reorder suggestions
# --------------------------------------------------------------------------

@login_required
def reorder_view(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse = resolve_warehouse(warehouses, request.GET.get("warehouse_id"))
    suggestions = compute_reorder_suggestions(warehouse=warehouse)
    return render(request, "assistant/reorder.html", {
        "warehouses": warehouses,
        "selected_warehouse_id": request.GET.get("warehouse_id"),
        "suggestions": suggestions,
    })


@login_required
@require_POST
def reorder_summary(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse = resolve_warehouse(warehouses, request.POST.get("warehouse_id"))
    suggestions = compute_reorder_suggestions(warehouse=warehouse)
    try:
        summary = summarize_reorder_suggestions(suggestions)
        error = ""
    except Exception as exc:  # noqa: BLE001 - surface API/config errors to the UI
        summary = ""
        error = str(exc)
    return render(request, "assistant/_reorder_summary.html", {"summary": summary, "error": error})


# --------------------------------------------------------------------------
# Receipt scanning
# --------------------------------------------------------------------------

@login_required
def scan_list(request):
    receipts = ScannedReceipt.objects.select_related("uploaded_by", "purchase_invoice")[:30]
    return render(request, "assistant/scan_list.html", {"receipts": receipts})


@login_required
@require_POST
def scan_upload(request):
    image = request.FILES.get("image")
    if not image:
        messages.error(request, "Choose an image to upload.")
        return redirect("assistant:scan_list")

    receipt = ScannedReceipt.objects.create(image=image, uploaded_by=request.user)
    try:
        with receipt.image.open("rb") as f:
            image_bytes = f.read()
        mime_type = image.content_type or "image/jpeg"
        data = extract_receipt_data(image_bytes, mime_type=mime_type)
        receipt.extracted_data = data
        receipt.save(update_fields=["extracted_data"])
    except Exception as exc:  # noqa: BLE001 - surface API/parse errors to the UI
        receipt.status = ScannedReceipt.Status.FAILED
        receipt.error = str(exc)
        receipt.save(update_fields=["status", "error"])
        messages.error(request, f"Couldn't read that receipt: {exc}")
        return redirect("assistant:scan_list")

    return redirect("assistant:scan_review", pk=receipt.pk)


@login_required
def scan_review(request, pk):
    receipt = get_object_or_404(ScannedReceipt, pk=pk)
    warehouses = Warehouse.objects.filter(is_active=True)
    suppliers = Party.objects.filter(is_active=True, type__in=[Party.Type.SUPPLIER, Party.Type.BOTH]).order_by("name")

    data = receipt.extracted_data or {}
    lines = []
    for line in data.get("items", []):
        matched = match_item_by_name(line.get("name", ""))
        lines.append({
            "raw_name": line.get("name", ""),
            "quantity": line.get("quantity", 1),
            "unit_price": line.get("unit_price", 0),
            "matched_item": matched,
        })

    context = {
        "receipt": receipt,
        "warehouses": warehouses,
        "suppliers": suppliers,
        "all_items": Item.objects.filter(is_active=True).order_by("name"),
        "extracted_supplier": data.get("supplier_name", ""),
        "extracted_date": data.get("date", ""),
        "lines": lines,
    }
    return render(request, "assistant/scan_review.html", context)


@login_required
@require_POST
def scan_confirm(request, pk):
    receipt = get_object_or_404(ScannedReceipt, pk=pk)
    warehouses = Warehouse.objects.filter(is_active=True)
    warehouse = resolve_warehouse(warehouses, request.POST.get("warehouse_id"))
    supplier = Party.objects.filter(pk=request.POST.get("supplier_id")).first() if request.POST.get("supplier_id") else None

    if not warehouse or not supplier:
        messages.error(request, "Select both a warehouse and a supplier.")
        return redirect("assistant:scan_review", pk=pk)

    item_ids = request.POST.getlist("item_id")
    quantities = request.POST.getlist("quantity")
    unit_prices = request.POST.getlist("unit_price")

    lines = []
    for item_id, qty, price in zip(item_ids, quantities, unit_prices):
        if not item_id:
            continue
        try:
            lines.append({
                "item": Item.objects.get(pk=item_id),
                "quantity": Decimal(qty),
                "unit_price": Decimal(price),
            })
        except (InvalidOperation, Item.DoesNotExist):
            continue

    if not lines:
        messages.error(request, "No valid item lines to save - match each row to a real item first.")
        return redirect("assistant:scan_review", pk=pk)

    class ReceiptCart:
        def __iter__(self_inner):
            for line in lines:
                yield {"item_id": line["item"].id, "quantity": line["quantity"], "unit_price": line["unit_price"]}

        def __len__(self_inner):
            return len(lines)

        @property
        def subtotal(self_inner):
            return sum((l["quantity"] * l["unit_price"] for l in lines), Decimal("0"))

        def clear(self_inner):
            pass

    try:
        paid_amount = Decimal(request.POST.get("paid_amount") or "0")
    except InvalidOperation:
        paid_amount = Decimal("0")

    invoice = complete_purchase(
        warehouse=warehouse, supplier=supplier, paid_amount=paid_amount,
        discount=Decimal("0"), cart=ReceiptCart(), user=request.user,
    )

    receipt.status = ScannedReceipt.Status.CONVERTED
    receipt.purchase_invoice = invoice
    receipt.save(update_fields=["status", "purchase_invoice"])

    messages.success(request, f"Purchase {invoice.invoice_no} created from scanned receipt.")
    return redirect("purchase:detail", pk=invoice.pk)


@login_required
@require_POST
def scan_discard(request, pk):
    receipt = get_object_or_404(ScannedReceipt, pk=pk)
    receipt.status = ScannedReceipt.Status.DISCARDED
    receipt.save(update_fields=["status"])
    return redirect("assistant:scan_list")
