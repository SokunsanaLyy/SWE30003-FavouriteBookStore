"""
storage.py
JSON file-based persistent storage replacing the SQLite database.
All data is stored as JSON files in the /data directory.
Follows PEP 8 coding standard. Reference: https://peps.python.org/pep-0008/
"""

import json
import os
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# JSON file names — one per entity
FILES = {
    "accounts":       "accounts.json",
    "customers":      "customers.json",
    "admins":         "admins.json",
    "books":          "books.json",
    "shopping_carts": "shopping_carts.json",
    "cart_items":     "cart_items.json",
    "orders":         "orders.json",
    "order_items":    "order_items.json",
    "invoices":       "invoices.json",
    "payments":       "payments.json",
    "receipts":       "receipts.json",
    "shipments":      "shipments.json",
}


class Storage:
    """
    Singleton JSON file storage class.
    Provides simple read/write/delete operations on JSON files.
    Business classes call these methods — no JSON logic leaks into models.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Create the data directory and empty JSON files if they don't exist."""
        os.makedirs(DATA_DIR, exist_ok=True)
        for name, filename in FILES.items():
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path):
                self._write(name, [])
        self._seed_default_data()

    # ── Core read / write ─────────────────────────────────────────────────────

    def _read(self, store: str) -> list[dict]:
        """Read and return all records from a JSON file."""
        path = os.path.join(DATA_DIR, FILES[store])
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, store: str, records: list[dict]) -> None:
        """Overwrite a JSON file with the given list of records."""
        path = os.path.join(DATA_DIR, FILES[store])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all(self, store: str) -> list[dict]:
        """Return all records in the given store."""
        return self._read(store)

    def find(self, store: str, **filters) -> list[dict]:
        """
        Return all records matching ALL supplied keyword filters.
        Example: find("books", is_available=True)
        """
        records = self._read(store)
        for key, value in filters.items():
            records = [r for r in records if r.get(key) == value]
        return records

    def find_one(self, store: str, **filters) -> dict | None:
        """Return the first matching record, or None."""
        results = self.find(store, **filters)
        return results[0] if results else None

    def insert(self, store: str, record: dict) -> None:
        """Append a new record to the store."""
        records = self._read(store)
        records.append(record)
        self._write(store, records)

    def update(self, store: str, id_field: str,
               id_value: str, updates: dict) -> bool:
        """
        Update the first record matching id_field == id_value.
        Returns True if a record was found and updated.
        """
        records = self._read(store)
        for record in records:
            if record.get(id_field) == id_value:
                record.update(updates)
                self._write(store, records)
                return True
        return False

    def delete(self, store: str, id_field: str, id_value: str) -> int:
        """
        Remove all records where id_field == id_value.
        Returns count of deleted records.
        """
        records = self._read(store)
        original_len = len(records)
        records = [r for r in records if r.get(id_field) != id_value]
        self._write(store, records)
        return original_len - len(records)

    def delete_where(self, store: str, **filters) -> int:
        """
        Remove all records matching ALL filters.
        Returns count of deleted records.
        """
        records = self._read(store)
        original_len = len(records)
        for key, value in filters.items():
            records = [r for r in records if r.get(key) != value]
        self._write(store, records)
        return original_len - len(records)

    def exists(self, store: str, **filters) -> bool:
        """Return True if at least one record matches the filters."""
        return len(self.find(store, **filters)) > 0

    # ── Seed default data ─────────────────────────────────────────────────────

    def _seed_default_data(self) -> None:
        """Populate default admin account and sample books if not already present."""
        import bcrypt
        from datetime import datetime

        # Default admin — password: Admin@1234
        if not self.exists("accounts", account_id="admin-001"):
            pw_hash = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
            self.insert("accounts", {
                "account_id": "admin-001",
                "email": "admin@favouritebooks.com",
                "password_hash": pw_hash,
                "role": "ADMIN",
                "created_at": datetime.now().isoformat()
            })
            self.insert("admins", {
                "admin_id": "admin-001",
                "role_detail": "owner"
            })

        # Sample books
        sample_books = [
            {"book_id": "book-001", "isbn": "9780743273565",
             "title": "The Great Gatsby", "author": "F. Scott Fitzgerald",
             "price": 18.99, "genre": "Fiction",
             "description": "A story of wealth, love, and the American Dream set in the 1920s.",
             "stock_quantity": 12, "is_available": True},
            {"book_id": "book-002", "isbn": "9780061096525",
             "title": "To Kill a Mockingbird", "author": "Harper Lee",
             "price": 17.99, "genre": "Fiction",
             "description": "A profound novel about racial injustice and moral growth.",
             "stock_quantity": 8, "is_available": True},
            {"book_id": "book-003", "isbn": "9780451524935",
             "title": "1984", "author": "George Orwell",
             "price": 16.99, "genre": "Dystopian",
             "description": "A chilling vision of a totalitarian society under constant surveillance.",
             "stock_quantity": 15, "is_available": True},
            {"book_id": "book-004", "isbn": "9780316769174",
             "title": "The Catcher in the Rye", "author": "J.D. Salinger",
             "price": 15.99, "genre": "Fiction",
             "description": "The story of teenage alienation narrated by Holden Caulfield.",
             "stock_quantity": 5, "is_available": True},
            {"book_id": "book-005", "isbn": "9780060850524",
             "title": "Brave New World", "author": "Aldous Huxley",
             "price": 17.50, "genre": "Dystopian",
             "description": "A futuristic world where society is controlled through pleasure.",
             "stock_quantity": 9, "is_available": True},
            {"book_id": "book-006", "isbn": "9780143105428",
             "title": "Pride and Prejudice", "author": "Jane Austen",
             "price": 14.99, "genre": "Romance",
             "description": "A witty and romantic novel following Elizabeth Bennet and Mr. Darcy.",
             "stock_quantity": 20, "is_available": True},
            {"book_id": "book-007", "isbn": "9780385490818",
             "title": "The Handmaid's Tale", "author": "Margaret Atwood",
             "price": 19.99, "genre": "Dystopian",
             "description": "A dark tale of a theocratic dystopia from a handmaid's perspective.",
             "stock_quantity": 7, "is_available": True},
            {"book_id": "book-008", "isbn": "9780618640157",
             "title": "The Lord of the Rings", "author": "J.R.R. Tolkien",
             "price": 34.99, "genre": "Fantasy",
             "description": "The epic fantasy trilogy following Frodo's quest to destroy the One Ring.",
             "stock_quantity": 3, "is_available": True},
        ]
        for book in sample_books:
            if not self.exists("books", book_id=book["book_id"]):
                now = __import__("datetime").datetime.now().isoformat()
                book["created_at"] = now
                self.insert("books", book)
