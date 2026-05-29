"""
customer.py
Customer class extending Account. JSON file storage.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""

import uuid
from datetime import datetime
from models.account import Account, OrderDTO, OrderItemDTO
from database.storage import Storage


class Customer(Account):

    def __init__(self, account_id, email, password_hash,
                 first_name="", last_name="", phone="", shipping_address=""):
        super().__init__(account_id, email, password_hash)
        self._first_name = first_name
        self._last_name = last_name
        self._phone = phone
        self._shipping_address = shipping_address

    @property
    def first_name(self): return self._first_name
    @property
    def last_name(self): return self._last_name
    @property
    def full_name(self): return f"{self._first_name} {self._last_name}"
    @property
    def phone(self): return self._phone
    @property
    def shipping_address(self): return self._shipping_address

    def get_role(self): return "CUSTOMER"

    @staticmethod
    def register(first_name, last_name, email, password, phone="", address=""):
        if not first_name.strip():
            return False, "First name is required."
        if not last_name.strip():
            return False, "Last name is required."
        if not email.strip() or "@" not in email:
            return False, "A valid email address is required."
        if not Account.enforce_password_strength(password):
            return False, ("Password must be at least 8 characters and include "
                           "an uppercase letter, a lowercase letter, and a digit.")
        s = Storage()
        if s.exists("accounts", email=email.lower().strip()):
            return False, "An account with this email already exists."

        account_id = str(uuid.uuid4())
        s.insert("accounts", {
            "account_id": account_id,
            "email": email.lower().strip(),
            "password_hash": Account.hash_password(password),
            "role": "CUSTOMER",
            "created_at": datetime.now().isoformat()
        })
        s.insert("customers", {
            "customer_id": account_id,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "phone": phone.strip(),
            "shipping_address": address.strip()
        })
        return True, "Registration successful."

    @staticmethod
    def load(account_id):
        s = Storage()
        acc = s.find_one("accounts", account_id=account_id)
        cust = s.find_one("customers", customer_id=account_id)
        if not acc or not cust:
            return None
        return Customer(
            acc["account_id"], acc["email"], acc["password_hash"],
            cust["first_name"], cust["last_name"],
            cust.get("phone", ""), cust.get("shipping_address", "")
        )

    def update_profile(self, first_name, last_name, phone, address):
        if not first_name.strip():
            return False, "First name cannot be blank."
        if not last_name.strip():
            return False, "Last name cannot be blank."
        self._storage.update("customers", "customer_id", self._account_id, {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "phone": phone.strip(),
            "shipping_address": address.strip()
        })
        self._first_name = first_name.strip()
        self._last_name = last_name.strip()
        self._phone = phone.strip()
        self._shipping_address = address.strip()
        return True, "Profile updated successfully."

    def get_order_history(self):
        orders = self._storage.find("orders", customer_id=self._account_id)
        orders.sort(key=lambda o: o["created_at"], reverse=True)
        result = []
        for o in orders:
            items_raw = self._storage.find("order_items", order_id=o["order_id"])
            items = []
            for i in items_raw:
                book = self._storage.find_one("books", book_id=i["book_id"])
                title = book["title"] if book else "Unknown"
                items.append(OrderItemDTO(
                    i["order_item_id"], title,
                    i["quantity"], i["unit_price"],
                    round(i["quantity"] * i["unit_price"], 2)
                ))
            result.append(OrderDTO(
                o["order_id"], o["total_amount"],
                o["status"], o["created_at"], items
            ))
        return result
