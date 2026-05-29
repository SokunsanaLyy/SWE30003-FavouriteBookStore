"""
order.py — ShoppingCart, Order (Facade), Invoice, Payment, Receipt, Shipment.
All using JSON file storage. Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""
import uuid
from datetime import datetime, timedelta
from models.account import InvoiceDTO, ReceiptDTO
from database.storage import Storage

GST_RATE = 0.10


class CartItem:
    """Single book line in the shopping cart. Owns its own subtotal (Information Expert)."""
    def __init__(self, cart_item_id, book_id, book_title, quantity, unit_price):
        self._cart_item_id = cart_item_id
        self._book_id = book_id
        self._book_title = book_title
        self._quantity = quantity
        self._unit_price = unit_price

    @property
    def cart_item_id(self): return self._cart_item_id
    @property
    def book_id(self): return self._book_id
    @property
    def book_title(self): return self._book_title
    @property
    def quantity(self): return self._quantity
    @property
    def unit_price(self): return self._unit_price

    def get_subtotal(self):
        return round(self._unit_price * self._quantity, 2)

    def set_quantity(self, qty):
        self._quantity = qty


class ShoppingCart:
    """Manages temporary book selections before checkout."""

    def __init__(self, cart_id, customer_id):
        self._cart_id = cart_id
        self._customer_id = customer_id
        self._items = []
        self._storage = Storage()

    @property
    def cart_id(self): return self._cart_id
    @property
    def items(self): return self._items

    def is_empty(self): return len(self._items) == 0

    def get_total_amount(self):
        return round(sum(i.get_subtotal() for i in self._items), 2)

    @staticmethod
    def load_or_create(customer_id):
        s = Storage()
        cart_rec = s.find_one("shopping_carts", customer_id=customer_id)
        if cart_rec:
            cart = ShoppingCart(cart_rec["cart_id"], customer_id)
        else:
            cart_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            s.insert("shopping_carts", {
                "cart_id": cart_id, "customer_id": customer_id,
                "created_at": now, "updated_at": now
            })
            cart = ShoppingCart(cart_id, customer_id)

        # Load items
        items = s.find("cart_items", cart_id=cart._cart_id)
        for item in items:
            book = s.find_one("books", book_id=item["book_id"])
            title = book["title"] if book else "Unknown"
            cart._items.append(CartItem(
                item["cart_item_id"], item["book_id"], title,
                item["quantity"], item["unit_price"]
            ))
        return cart

    def add_book(self, book_id, book_title, unit_price, qty, stock):
        if qty < 1:
            return False, "Quantity must be at least 1."
        if qty > stock:
            return False, f"Only {stock} copies available."

        for item in self._items:
            if item.book_id == book_id:
                new_qty = item.quantity + qty
                if new_qty > stock:
                    return False, f"Total quantity cannot exceed stock ({stock})."
                item.set_quantity(new_qty)
                self._storage.update("cart_items", "cart_item_id",
                                     item.cart_item_id, {"quantity": new_qty})
                self._touch()
                return True, "Cart updated."

        cart_item_id = str(uuid.uuid4())
        self._storage.insert("cart_items", {
            "cart_item_id": cart_item_id, "cart_id": self._cart_id,
            "book_id": book_id, "quantity": qty, "unit_price": unit_price
        })
        self._items.append(CartItem(cart_item_id, book_id, book_title, qty, unit_price))
        self._touch()
        return True, "Book added to cart."

    def remove_item(self, cart_item_id):
        self._storage.delete("cart_items", "cart_item_id", cart_item_id)
        self._items = [i for i in self._items if i.cart_item_id != cart_item_id]
        self._touch()
        return True, "Item removed."

    def update_quantity(self, cart_item_id, qty, stock):
        if qty < 1:
            return self.remove_item(cart_item_id)
        if qty > stock:
            return False, f"Only {stock} copies available."
        self._storage.update("cart_items", "cart_item_id",
                             cart_item_id, {"quantity": qty})
        for item in self._items:
            if item.cart_item_id == cart_item_id:
                item.set_quantity(qty)
        self._touch()
        return True, "Quantity updated."

    def clear(self):
        self._storage.delete_where("cart_items", cart_id=self._cart_id)
        self._items = []

    def checkout(self, customer_id, delivery_address):
        if self.is_empty():
            return False, "Your cart is empty.", ""
        order = Order.create_from_cart(self, customer_id, delivery_address)
        if not order:
            return False, "Could not create order.", ""
        self.clear()
        return True, "Order placed.", order.order_id

    def _touch(self):
        self._storage.update("shopping_carts", "cart_id", self._cart_id,
                             {"updated_at": datetime.now().isoformat()})


class OrderItem:
    """Captures unit price at time of purchase — immutable snapshot."""
    def __init__(self, order_item_id, order_id, book_id, book_title, quantity, unit_price):
        self._order_item_id = order_item_id
        self._order_id = order_id
        self._book_id = book_id
        self._book_title = book_title
        self._quantity = quantity
        self._unit_price = unit_price

    @property
    def book_title(self): return self._book_title
    @property
    def quantity(self): return self._quantity
    @property
    def unit_price(self): return self._unit_price

    def get_line_total(self):
        return round(self._unit_price * self._quantity, 2)


class Invoice:
    """Billing document. Calculates subtotal, GST, total from OrderItems."""

    def __init__(self, invoice_id, order_id, order_items):
        self._invoice_id = invoice_id
        self._order_id = order_id
        self._order_items = order_items
        self._subtotal = 0.0
        self._tax_amount = 0.0
        self._total_amount = 0.0
        self._is_paid = False
        self._issued_at = datetime.now().isoformat()
        self._storage = Storage()

    def generate(self):
        self._subtotal = round(sum(i.get_line_total() for i in self._order_items), 2)
        self._tax_amount = round(self._subtotal * GST_RATE, 2)
        self._total_amount = round(self._subtotal + self._tax_amount, 2)
        self._storage.insert("invoices", {
            "invoice_id": self._invoice_id, "order_id": self._order_id,
            "subtotal": self._subtotal, "tax_amount": self._tax_amount,
            "total_amount": self._total_amount, "is_paid": False,
            "issued_at": self._issued_at
        })

    def mark_paid(self):
        self._is_paid = True
        self._storage.update("invoices", "invoice_id",
                             self._invoice_id, {"is_paid": True})

    def generate_receipt(self, transaction_ref, amount, method):
        if not self._is_paid:
            raise RuntimeError("Cannot generate receipt before payment confirmed.")
        receipt = Receipt(str(uuid.uuid4()), self._order_id,
                          transaction_ref, amount, method)
        receipt.save()
        return receipt

    def to_dto(self):
        return InvoiceDTO(self._invoice_id, self._order_id, self._subtotal,
                          self._tax_amount, self._total_amount,
                          self._is_paid, self._issued_at)


class Receipt:
    """Proof of completed payment."""

    def __init__(self, receipt_id, order_id, transaction_reference, amount_paid, payment_method):
        self._receipt_id = receipt_id
        self._order_id = order_id
        self._transaction_reference = transaction_reference
        self._amount_paid = amount_paid
        self._payment_method = payment_method
        self._issued_at = datetime.now().isoformat()
        self._storage = Storage()

    @property
    def transaction_reference(self): return self._transaction_reference

    def save(self):
        self._storage.insert("receipts", {
            "receipt_id": self._receipt_id, "order_id": self._order_id,
            "transaction_reference": self._transaction_reference,
            "amount_paid": self._amount_paid, "payment_method": self._payment_method,
            "issued_at": self._issued_at
        })

    def to_dto(self):
        return ReceiptDTO(self._receipt_id, self._order_id,
                          self._transaction_reference, self._amount_paid,
                          self._payment_method, self._issued_at)


class IPaymentStrategy:
    def process_payment(self, amount, reference): raise NotImplementedError
    def is_available(self): raise NotImplementedError


class CardPaymentStrategy(IPaymentStrategy):
    """Simulated card payment — always succeeds per assignment requirements."""
    def is_available(self): return True
    def process_payment(self, amount, reference):
        return f"TXN-{uuid.uuid4().hex[:10].upper()}"


class Payment:
    """Handles payment via injected strategy. Isolates payment from Order."""

    def __init__(self, payment_id, order_id, amount):
        self._payment_id = payment_id
        self._order_id = order_id
        self._amount = amount
        self._method = "CARD"
        self._status = "PENDING"
        self._transaction_ref = None
        self._strategy = CardPaymentStrategy()
        self._storage = Storage()

    @property
    def transaction_ref(self): return self._transaction_ref
    @property
    def amount(self): return self._amount

    def submit(self):
        if not self._strategy.is_available():
            return False, "Payment gateway is currently unavailable."
        ref = self._strategy.process_payment(self._amount, self._order_id)
        if ref:
            self._transaction_ref = ref
            self._status = "SUCCESS"
            self._storage.insert("payments", {
                "payment_id": self._payment_id, "order_id": self._order_id,
                "amount": self._amount, "method": self._method,
                "status": self._status, "transaction_ref": self._transaction_ref,
                "processed_at": datetime.now().isoformat()
            })
            return True, "Payment processed successfully."
        return False, "Payment could not be processed."


class Shipment:
    """Tracks delivery from PACKED to DELIVERED."""

    def __init__(self, shipment_id, order_id, delivery_address):
        self._shipment_id = shipment_id
        self._order_id = order_id
        self._delivery_address = delivery_address
        self._status = "PACKED"
        self._tracking_number = None
        self._storage = Storage()

    @property
    def tracking_number(self): return self._tracking_number

    def create(self):
        self._tracking_number = f"FB-{uuid.uuid4().hex[:8].upper()}"
        estimated = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        self._storage.insert("shipments", {
            "shipment_id": self._shipment_id, "order_id": self._order_id,
            "delivery_address": self._delivery_address,
            "shipping_method": "STANDARD", "status": self._status,
            "tracking_number": self._tracking_number,
            "estimated_delivery": estimated
        })


class Order:
    """
    Facade over the checkout subsystem.
    Orchestrates OrderItems, Invoice, Payment, Receipt, Shipment.
    """

    def __init__(self, order_id, customer_id, order_items, total_amount, delivery_address):
        self._order_id = order_id
        self._customer_id = customer_id
        self._order_items = order_items
        self._total_amount = total_amount
        self._delivery_address = delivery_address
        self._status = "PENDING"
        self._invoice = None
        self._payment = None
        self._shipment = None
        self._receipt = None
        self._storage = Storage()

    @property
    def order_id(self): return self._order_id
    @property
    def total_amount(self): return self._total_amount
    @property
    def status(self): return self._status
    @property
    def order_items(self): return self._order_items
    @property
    def invoice(self): return self._invoice
    @property
    def receipt(self): return self._receipt
    @property
    def shipment(self): return self._shipment

    @staticmethod
    def create_from_cart(cart, customer_id, delivery_address):
        """
        Static factory converting CartItems to OrderItems.
        Called by Customer.place_order(), not by ShoppingCart (corrected from A2).
        """
        if cart.is_empty():
            return None
        s = Storage()
        order_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        order_items = []
        total = 0.0

        for ci in cart.items:
            oi_id = str(uuid.uuid4())
            line = ci.get_subtotal()
            total += line
            s.insert("order_items", {
                "order_item_id": oi_id, "order_id": order_id,
                "book_id": ci.book_id, "quantity": ci.quantity,
                "unit_price": ci.unit_price
            })
            # Decrement stock in JSON
            book_rec = s.find_one("books", book_id=ci.book_id)
            if book_rec:
                new_stock = book_rec["stock_quantity"] - ci.quantity
                s.update("books", "book_id", ci.book_id,
                         {"stock_quantity": max(0, new_stock)})
            order_items.append(OrderItem(
                oi_id, order_id, ci.book_id, ci.book_title,
                ci.quantity, ci.unit_price
            ))

        total = round(total, 2)
        s.insert("orders", {
            "order_id": order_id, "customer_id": customer_id,
            "total_amount": total, "status": "PENDING", "created_at": now,
            "delivery_address": delivery_address
        })

        order = Order(order_id, customer_id, order_items, total, delivery_address)
        order._generate_invoice()
        return order

    def _generate_invoice(self):
        inv_id = str(uuid.uuid4())
        self._invoice = Invoice(inv_id, self._order_id, self._order_items)
        self._invoice.generate()

    def process_payment(self):
        if not self._invoice:
            return False, "No invoice for this order."
        pmt_id = str(uuid.uuid4())
        self._payment = Payment(pmt_id, self._order_id,
                                self._invoice.to_dto().total_amount)
        success, message = self._payment.submit()
        if success:
            self._invoice.mark_paid()
            self._receipt = self._invoice.generate_receipt(
                self._payment.transaction_ref, self._payment.amount, "CARD")
            self._status = "PAID"
            self._storage.update("orders", "order_id",
                                 self._order_id, {"status": "PAID"})
            ship_id = str(uuid.uuid4())
            self._shipment = Shipment(ship_id, self._order_id, self._delivery_address)
            self._shipment.create()
        return success, message

# Patch Order with load_and_pay
@staticmethod
def _load_and_pay(order_id, delivery_address):
    s = Storage()
    order_rec = s.find_one("orders", order_id=order_id)
    if not order_rec:
        return {"success": False, "message": "Order not found."}

    items_raw = s.find("order_items", order_id=order_id)
    order_items = []
    for i in items_raw:
        book = s.find_one("books", book_id=i["book_id"])
        title = book["title"] if book else "Unknown"
        order_items.append(OrderItem(
            i["order_item_id"], order_id, i["book_id"],
            title, i["quantity"], i["unit_price"]
        ))

    order = Order(order_id, order_rec["customer_id"], order_items,
                  order_rec["total_amount"],
                  order_rec.get("delivery_address", delivery_address))
    order._status = order_rec["status"]

    # Generate invoice + process payment
    order._generate_invoice()
    success, message = order.process_payment()

    return {
        "success": success,
        "message": message,
        "invoice": order.invoice.to_dto() if order.invoice else None,
        "receipt": order.receipt.to_dto() if order.receipt else None,
        "tracking": order.shipment.tracking_number if order.shipment else None,
    }

Order.load_and_pay = staticmethod(_load_and_pay)
