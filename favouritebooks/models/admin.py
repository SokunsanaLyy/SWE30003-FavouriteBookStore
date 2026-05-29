"""
admin.py — Admin class using JSON storage.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""
from models.account import Account
from database.storage import Storage


class Admin(Account):

    def __init__(self, account_id, email, password_hash, role_detail="owner"):
        super().__init__(account_id, email, password_hash)
        self._role_detail = role_detail

    def get_role(self): return "ADMIN"

    @staticmethod
    def load(account_id):
        s = Storage()
        acc = s.find_one("accounts", account_id=account_id)
        adm = s.find_one("admins", admin_id=account_id)
        if not acc or not adm:
            return None
        return Admin(acc["account_id"], acc["email"],
                     acc["password_hash"], adm.get("role_detail", "owner"))

    def get_all_orders(self):
        s = Storage()
        orders = s.get_all("orders")
        orders.sort(key=lambda o: o["created_at"], reverse=True)
        result = []
        for o in orders:
            cust = s.find_one("customers", customer_id=o["customer_id"])
            o["first_name"] = cust["first_name"] if cust else ""
            o["last_name"] = cust["last_name"] if cust else ""
            result.append(o)
        return result

    def generate_sales_report(self, period):
        from datetime import datetime, timedelta
        s = Storage()
        now = datetime.now()
        period_deltas = {
            "DAILY":   timedelta(days=1),
            "WEEKLY":  timedelta(weeks=1),
            "MONTHLY": timedelta(days=30),
            "ANNUAL":  timedelta(days=365),
            "YTD":     now - datetime(now.year, 1, 1),
        }
        delta = period_deltas.get(period, timedelta(days=30))
        since = (now - delta).isoformat()

        orders = [o for o in s.get_all("orders")
                  if o["status"] == "PAID" and o["created_at"] >= since]

        total_revenue = round(sum(o["total_amount"] for o in orders), 2)
        order_count = len(orders)

        # Aggregate top books
        book_sales = {}
        for o in orders:
            items = s.find("order_items", order_id=o["order_id"])
            for item in items:
                bid = item["book_id"]
                if bid not in book_sales:
                    book = s.find_one("books", book_id=bid)
                    book_sales[bid] = {
                        "title": book["title"] if book else "Unknown",
                        "units_sold": 0,
                        "revenue": 0.0
                    }
                book_sales[bid]["units_sold"] += item["quantity"]
                book_sales[bid]["revenue"] += round(
                    item["quantity"] * item["unit_price"], 2)

        top_books = sorted(book_sales.values(),
                           key=lambda x: x["units_sold"], reverse=True)[:5]

        return {
            "period": period,
            "total_revenue": total_revenue,
            "order_count": order_count,
            "top_books": top_books,
        }
