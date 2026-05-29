"""
book.py — Book and BookCatalogue using JSON storage.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""
import uuid
from datetime import datetime
from models.account import BookDTO
from database.storage import Storage


class Book:
    def __init__(self, book_id, isbn, title, author, price,
                 genre, description, stock_quantity, is_available):
        self._book_id = book_id
        self._isbn = isbn
        self._title = title
        self._author = author
        self._price = price
        self._genre = genre
        self._description = description
        self._stock_quantity = stock_quantity
        self._is_available = is_available

    @property
    def book_id(self): return self._book_id
    @property
    def isbn(self): return self._isbn
    @property
    def title(self): return self._title
    @property
    def author(self): return self._author
    @property
    def price(self): return self._price
    @property
    def genre(self): return self._genre
    @property
    def description(self): return self._description
    @property
    def stock_quantity(self): return self._stock_quantity
    @property
    def is_available(self): return bool(self._is_available)

    def is_in_stock(self):
        return self._is_available and self._stock_quantity > 0

    def decrement_stock(self, qty):
        Storage().update("books", "book_id", self._book_id,
                         {"stock_quantity": self._stock_quantity - qty})
        self._stock_quantity -= qty

    def to_dto(self):
        return BookDTO(self._book_id, self._isbn, self._title, self._author,
                       self._price, self._genre, self._description,
                       self._stock_quantity, self._is_available)

    @staticmethod
    def from_dict(d):
        return Book(d["book_id"], d["isbn"], d["title"], d["author"],
                    d["price"], d.get("genre", ""), d.get("description", ""),
                    d["stock_quantity"], d.get("is_available", True))


class BookCatalogue:
    def __init__(self):
        self._storage = Storage()

    def get_all_books(self):
        rows = self._storage.find("books", is_available=True)
        return sorted([Book.from_dict(r).to_dto() for r in rows],
                      key=lambda b: b.title)

    def get_all_books_admin(self):
        rows = self._storage.get_all("books")
        return sorted([Book.from_dict(r).to_dto() for r in rows],
                      key=lambda b: b.title)

    def get_book_by_id(self, book_id):
        row = self._storage.find_one("books", book_id=book_id)
        return Book.from_dict(row) if row else None

    def search_books(self, query):
        q = query.lower()
        rows = [r for r in self._storage.find("books", is_available=True)
                if q in r["title"].lower()
                or q in r["author"].lower()
                or q in r["isbn"]]
        return sorted([Book.from_dict(r).to_dto() for r in rows],
                      key=lambda b: b.title)

    def filter_by_genre(self, genre):
        rows = self._storage.find("books", is_available=True, genre=genre)
        return sorted([Book.from_dict(r).to_dto() for r in rows],
                      key=lambda b: b.title)

    def get_genres(self):
        rows = self._storage.find("books", is_available=True)
        genres = sorted({r["genre"] for r in rows if r.get("genre")})
        return genres

    def check_duplicate_isbn(self, isbn, exclude_id=""):
        rows = self._storage.find("books", isbn=isbn.strip())
        if exclude_id:
            rows = [r for r in rows if r["book_id"] != exclude_id]
        return len(rows) > 0

    def add_book(self, isbn, title, author, price, genre, description, stock):
        if not isbn.strip(): return False, "ISBN is required."
        if not title.strip(): return False, "Title is required."
        if not author.strip(): return False, "Author is required."
        try:
            price = float(price)
            stock = int(stock)
        except (ValueError, TypeError):
            return False, "Price and stock must be valid numbers."
        if price <= 0: return False, "Price must be greater than zero."
        if stock < 0: return False, "Stock quantity cannot be negative."
        if self.check_duplicate_isbn(isbn):
            return False, "A book with this ISBN already exists."
        self._storage.insert("books", {
            "book_id": str(uuid.uuid4()),
            "isbn": isbn.strip(), "title": title.strip(),
            "author": author.strip(), "price": price,
            "genre": genre.strip(), "description": description.strip(),
            "stock_quantity": stock, "is_available": True,
            "created_at": datetime.now().isoformat()
        })
        return True, "Book added successfully."

    def update_book(self, book_id, isbn, title, author, price, genre, description, stock):
        if not title.strip(): return False, "Title is required."
        try:
            price = float(price)
            stock = int(stock)
        except (ValueError, TypeError):
            return False, "Price and stock must be valid numbers."
        if price <= 0: return False, "Price must be greater than zero."
        if stock < 0: return False, "Stock quantity cannot be negative."
        if self.check_duplicate_isbn(isbn.strip(), exclude_id=book_id):
            return False, "A book with this ISBN already exists."
        self._storage.update("books", "book_id", book_id, {
            "isbn": isbn.strip(), "title": title.strip(),
            "author": author.strip(), "price": price,
            "genre": genre.strip(), "description": description.strip(),
            "stock_quantity": stock
        })
        return True, "Book updated successfully."

    def remove_book(self, book_id):
        self._storage.update("books", "book_id", book_id, {"is_available": False})
        return True, "Book removed from catalogue."

    def restore_book(self, book_id):
        self._storage.update("books", "book_id", book_id, {"is_available": True})
        return True, "Book restored to catalogue."
