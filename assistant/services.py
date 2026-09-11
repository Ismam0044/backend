import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import F, Q, Sum
from django.utils import timezone
from google import genai
from google.genai import types

from accounts.models import CashBookEntry
from inventory.models import Item, Stock
from parties.models import Party
from purchase.models import PurchaseInvoice
from sales.models import SalesInvoice, SalesInvoiceItem

from .models import ChatQuery

MODEL_NAME = "gemini-3.6-flash"


def _client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


# --------------------------------------------------------------------------
# Chat tools - plain read-only Python functions. google-genai builds the
# function-calling schema from each one's type hints and docstring, and
# calls them automatically when the model decides it needs that data.
# --------------------------------------------------------------------------

def get_todays_sales() -> dict:
    """Get today's total sales amount (in Bangladeshi Taka) and invoice count."""
    today = timezone.localdate()
    total = SalesInvoice.objects.filter(date=today).aggregate(t=Sum("total"))["t"] or 0
    count = SalesInvoice.objects.filter(date=today).count()
    return {"date": str(today), "total_sales_bdt": float(total), "invoice_count": count}


def get_low_stock_items() -> list:
    """Get items that are at or below their reorder level, across all warehouses."""
    stocks = Stock.objects.select_related("item", "warehouse").filter(
        quantity__lte=F("item__reorder_level")
    )[:20]
    return [
        {
            "item": s.item.name,
            "warehouse": s.warehouse.name,
            "quantity": float(s.quantity),
            "reorder_level": float(s.item.reorder_level),
        }
        for s in stocks
    ]


def get_top_selling_items(days: int = 30, limit: int = 5) -> list:
    """Get the top-selling items by quantity sold over the last N days (default 30)."""
    since = timezone.localdate() - timedelta(days=days)
    rows = (
        SalesInvoiceItem.objects.filter(invoice__date__gte=since)
        .values("item__name")
        .annotate(total_qty=Sum("quantity"), total_revenue=Sum(F("quantity") * F("unit_price")))
        .order_by("-total_qty")[:limit]
    )
    return [
        {"item": r["item__name"], "quantity_sold": float(r["total_qty"]), "revenue_bdt": float(r["total_revenue"])}
        for r in rows
    ]


def get_party_balance(party_name: str) -> list:
    """Look up a customer or supplier's current balance by (partial) name.
    Positive balance means they owe the shop money; negative means the shop owes them."""
    parties = Party.objects.filter(name__icontains=party_name).with_balance()[:5]
    if not parties:
        return [{"error": f"No party found matching '{party_name}'"}]
    return [
        {"name": p.name, "type": p.get_type_display(), "balance_bdt": float(p.balance)}
        for p in parties
    ]


def get_dues_summary() -> dict:
    """Get the total amount customers owe the shop (receivable) and the total the shop owes suppliers (payable)."""
    parties = Party.objects.with_balance()
    receivable = sum((p.balance for p in parties if p.balance > 0), Decimal("0"))
    payable = sum((-p.balance for p in parties if p.balance < 0), Decimal("0"))
    return {"total_receivable_bdt": float(receivable), "total_payable_bdt": float(payable)}


def get_cash_summary(days: int = 30) -> dict:
    """Get total cash in vs cash out over the last N days (default 30) across all warehouses."""
    since = timezone.localdate() - timedelta(days=days)
    totals = CashBookEntry.objects.filter(date__gte=since).aggregate(
        cash_in=Sum("amount", filter=Q(entry_type="IN")),
        cash_out=Sum("amount", filter=Q(entry_type="OUT")),
    )
    cash_in = totals["cash_in"] or 0
    cash_out = totals["cash_out"] or 0
    return {"period_days": days, "cash_in_bdt": float(cash_in), "cash_out_bdt": float(cash_out), "net_bdt": float(cash_in - cash_out)}


def get_recent_purchases(limit: int = 5) -> list:
    """Get the most recent purchase invoices from suppliers."""
    invoices = PurchaseInvoice.objects.select_related("supplier", "warehouse").order_by("-id")[:limit]
    return [
        {
            "invoice_no": inv.invoice_no,
            "supplier": inv.supplier.name,
            "warehouse": inv.warehouse.name,
            "date": str(inv.date),
            "total_bdt": float(inv.total),
            "due_bdt": float(inv.due_amount),
        }
        for inv in invoices
    ]


CHAT_TOOLS = [
    get_todays_sales,
    get_low_stock_items,
    get_top_selling_items,
    get_party_balance,
    get_dues_summary,
    get_cash_summary,
    get_recent_purchases,
]

CHAT_SYSTEM_INSTRUCTION = (
    "You are a business assistant built into the ERP system for a Bangladeshi supershop "
    "with multiple warehouses. Answer questions about sales, inventory, dues, and cash using "
    "the tools provided - always call a tool to get real data before answering; never guess or "
    "make up numbers. All amounts are in Bangladeshi Taka (৳). Be concise and direct, formatted "
    "for quick reading (short sentences or a brief list), not long paragraphs."
)


def ask_business_question(question: str, user) -> ChatQuery:
    record = ChatQuery(user=user, question=question)
    try:
        client = _client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_INSTRUCTION,
                tools=CHAT_TOOLS,
            ),
        )
        record.answer = response.text or "(no answer returned)"
    except Exception as exc:  # noqa: BLE001 - surface any API/config error to the UI
        record.error = str(exc)
    record.save()
    return record


# --------------------------------------------------------------------------
# Smart reorder suggestions - the math is plain arithmetic (deliberately not
# AI, since an LLM has no business doing numeric forecasting); Gemini only
# adds an optional natural-language summary on top of real computed numbers.
# --------------------------------------------------------------------------

def compute_reorder_suggestions(warehouse=None, lookback_days=30, cover_days=14):
    since = timezone.localdate() - timedelta(days=lookback_days)
    stocks = Stock.objects.select_related("item", "warehouse")
    if warehouse:
        stocks = stocks.filter(warehouse=warehouse)

    suggestions = []
    for s in stocks:
        sold = SalesInvoiceItem.objects.filter(
            item=s.item, invoice__warehouse=s.warehouse, invoice__date__gte=since
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        daily_velocity = sold / lookback_days
        if daily_velocity <= 0:
            continue
        target_stock = daily_velocity * cover_days + s.item.reorder_level
        suggested_qty = (target_stock - s.quantity).quantize(Decimal("1"))
        if suggested_qty > 0:
            suggestions.append({
                "item": s.item,
                "warehouse": s.warehouse,
                "current_stock": s.quantity,
                "daily_velocity": daily_velocity.quantize(Decimal("0.1")),
                "suggested_qty": suggested_qty,
            })
    suggestions.sort(key=lambda x: -x["daily_velocity"])
    return suggestions


def summarize_reorder_suggestions(suggestions) -> str:
    if not suggestions:
        return "No reorder suggestions right now — stock levels look healthy relative to recent sales."
    lines = [
        f"{s['item'].name} at {s['warehouse'].name}: {s['current_stock']} in stock, "
        f"selling ~{s['daily_velocity']}/day, suggest ordering {s['suggested_qty']}"
        for s in suggestions[:15]
    ]
    prompt = (
        "Here are computed reorder suggestions for a Bangladeshi supershop. Write a short "
        "(3-5 sentence) plain-language summary highlighting the most urgent ones. Use the "
        "exact numbers given - do not invent or estimate anything not listed here.\n\n"
        + "\n".join(lines)
    )
    client = _client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text or ""


# --------------------------------------------------------------------------
# Receipt / purchase invoice scanning
# --------------------------------------------------------------------------

RECEIPT_EXTRACTION_PROMPT = """Extract structured purchase data from this receipt/invoice image.
Return ONLY valid JSON, no markdown code fences, matching exactly this shape:
{"supplier_name": string or null, "date": "YYYY-MM-DD" or null, "items": [{"name": string, "quantity": number, "unit_price": number}], "total": number or null}
If a field is unreadable or absent, use null (or omit items you truly cannot make out).
Quantities and prices must be plain numbers, not strings, and not including currency symbols."""


def extract_receipt_data(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    client = _client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            RECEIPT_EXTRACTION_PROMPT,
        ],
    )
    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


def match_item_by_name(name: str):
    """Best-effort match of an AI-extracted item name against real inventory items."""
    if not name:
        return None
    exact = Item.objects.filter(name__iexact=name).first()
    if exact:
        return exact
    return Item.objects.filter(name__icontains=name.split()[0]).first() if name.split() else None
