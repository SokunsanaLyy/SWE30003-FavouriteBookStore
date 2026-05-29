"""
account.py
Abstract Account base class. Shared authentication for Customer and Admin.
Uses JSON file-based storage via Storage singleton.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import bcrypt
from database.storage import Storage


@dataclass
class BookDTO:
    book_id: str
    isbn: str
    title: str
    author: str
    price: float
    genre: str
    description: str
    stock_quantity: int
    is_available: bool


@dataclass
class OrderItemDTO:
    order_item_id: str
    book_title: str
    quantity: int
    unit_price: float
    line_total: float


@dataclass
class OrderDTO:
    order_id: str
    total_amount: float
    status: str
    created_at: str
    items: list


@dataclass
class InvoiceDTO:
    invoice_id: str
    order_id: str
    subtotal: float
    tax_amount: float
    total_amount: float
    is_paid: bool
    issued_at: str


@dataclass
class ReceiptDTO:
    receipt_id: str
    order_id: str
    transaction_reference: str
    amount_paid: float
    payment_method: str
    issued_at: str


class Account(ABC):
    """
    Abstract base class for all authenticated users.
    Handles password hashing and credential validation.
    Customer and Admin extend this class.
    """

    def __init__(self, account_id: str, email: str, password_hash: str):
        self._account_id = account_id
        self._email = email
        self._password_hash = password_hash
        self._storage = Storage()

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def email(self) -> str:
        return self._email

    @staticmethod
    def enforce_password_strength(password: str) -> bool:
        """Password must be 8+ chars with upper, lower, and digit."""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        return True

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def validate_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    @staticmethod
    def find_by_email(email: str) -> dict | None:
        return Storage().find_one("accounts", email=email.lower().strip())

    @abstractmethod
    def get_role(self) -> str:
        pass
