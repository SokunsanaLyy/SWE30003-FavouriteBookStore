"""
database.py
Singleton Database class implementing the Repository pattern.
All persistence operations are abstracted here; no SQL appears in business classes.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""

import sqlite3
import os
from typing import Any


class Database:
    """
    Singleton class providing a single shared database connection.
    Implements the Repository pattern: business classes call high-level
    methods and never write raw SQL.
    """

    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self, db_path: str = "favourite_books.db") -> None:
        """Open the database connection and enable foreign key enforcement."""
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Return the active connection."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Execute a parameterised SELECT query.
        Returns a list of row dicts.
        """
        cursor = self._connection.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """
        Execute a parameterised INSERT / UPDATE / DELETE.
        Returns the number of rows affected.
        """
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor.rowcount

    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        """Execute an INSERT and return the new row's lastrowid."""
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor.lastrowid

    def initialise_schema(self) -> None:
        """Create all tables if they do not already exist."""
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            sql = f.read()
        self._connection.executescript(sql)
        self._connection.commit()
