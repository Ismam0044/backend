from decimal import Decimal


class SessionCart:
    """A simple session-backed cart: {item_id: {name, unit, quantity, unit_price}}."""

    def __init__(self, request, session_key):
        self.session = request.session
        self.session_key = session_key
        self.cart = self.session.setdefault(session_key, {})

    def add(self, item, quantity, unit_price):
        item_id = str(item.id)
        if item_id in self.cart:
            self.cart[item_id]["quantity"] = str(Decimal(self.cart[item_id]["quantity"]) + Decimal(quantity))
        else:
            self.cart[item_id] = {
                "name": item.name,
                "unit": item.unit.short_name,
                "quantity": str(quantity),
                "unit_price": str(unit_price),
            }
        self._save()

    def set_quantity(self, item_id, quantity):
        item_id = str(item_id)
        if item_id not in self.cart:
            return
        if Decimal(quantity) <= 0:
            del self.cart[item_id]
        else:
            self.cart[item_id]["quantity"] = str(quantity)
        self._save()

    def set_unit_price(self, item_id, unit_price):
        item_id = str(item_id)
        if item_id in self.cart:
            self.cart[item_id]["unit_price"] = str(unit_price)
            self._save()

    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self._save()

    def clear(self):
        self.session[self.session_key] = {}
        self.cart = self.session[self.session_key]
        self._save()

    def _save(self):
        self.session[self.session_key] = self.cart
        self.session.modified = True

    def __iter__(self):
        for item_id, data in self.cart.items():
            quantity = Decimal(data["quantity"])
            unit_price = Decimal(data["unit_price"])
            yield {
                "item_id": item_id,
                "name": data["name"],
                "unit": data.get("unit", ""),
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": quantity * unit_price,
            }

    def __len__(self):
        return len(self.cart)

    @property
    def subtotal(self):
        return sum((Decimal(d["quantity"]) * Decimal(d["unit_price"]) for d in self.cart.values()), Decimal("0"))
