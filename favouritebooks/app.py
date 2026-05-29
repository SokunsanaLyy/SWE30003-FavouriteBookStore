"""
app.py — Favourite Books Online Bookstore Flask application.
Uses JSON file-based persistent storage via Storage singleton.
Coding standard: PEP 8 — https://peps.python.org/pep-0008/
"""
import os, uuid
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from database.storage import Storage
from models.account import Account
from models.customer import Customer
from models.admin import Admin
from models.book import BookCatalogue
from models.order import ShoppingCart, Order, Invoice, OrderItem, Payment, CardPaymentStrategy, Shipment

app = Flask(__name__)
app.secret_key = "favourite-books-secret-2024"

#  Startup 
storage = Storage()
storage.initialise()
catalogue = BookCatalogue()

# ── Helpers ───────────────────────────────────────────────────────────────────
def is_logged_in(): return "account_id" in session
def is_admin(): return session.get("role") == "ADMIN"

def require_login():
    if not is_logged_in():
        flash("Please log in to continue.", "warning")
        return redirect(url_for("login"))

def require_admin():
    if not is_logged_in() or not is_admin():
        flash("Admin access required.", "danger")
        return redirect(url_for("login"))

def cart_count():
    if not is_logged_in() or is_admin(): return 0
    cart = ShoppingCart.load_or_create(session["account_id"])
    return sum(i.quantity for i in cart.items)

app.jinja_env.globals["cart_count"] = cart_count

# ── Public ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    books = catalogue.get_all_books()
    genres = catalogue.get_genres()
    return render_template("index.html", books=books, genres=genres, search="", selected_genre="")

@app.route("/search")
def search():
    q = request.args.get("q","").strip()
    genre = request.args.get("genre","").strip()
    genres = catalogue.get_genres()
    if genre: books = catalogue.filter_by_genre(genre)
    elif q:   books = catalogue.search_books(q)
    else:     books = catalogue.get_all_books()
    return render_template("index.html", books=books, genres=genres, search=q, selected_genre=genre)

@app.route("/book/<book_id>")
def book_detail(book_id):
    book = catalogue.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("index"))
    return render_template("book_detail.html", book=book)

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["GET","POST"])
def register():
    if is_logged_in(): return redirect(url_for("index"))
    if request.method == "POST":
        f = request.form
        if f.get("password") != f.get("confirm_password"):
            flash("Passwords do not match.", "danger")
            return render_template("register.html", form=f)
        ok, msg = Customer.register(f.get("first_name",""), f.get("last_name",""),
                                    f.get("email",""), f.get("password",""),
                                    f.get("phone",""), f.get("address",""))
        if ok:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        flash(msg, "danger")
        return render_template("register.html", form=f)
    return render_template("register.html", form={})

@app.route("/login", methods=["GET","POST"])
def login():
    if is_logged_in(): return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")
        acc = Account.find_by_email(email)
        if not acc or not Account.validate_password(password, acc["password_hash"]):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
        session["account_id"] = acc["account_id"]
        session["email"] = acc["email"]
        session["role"] = acc["role"]
        if acc["role"] == "ADMIN":
            flash("Welcome, Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        cust = Customer.load(acc["account_id"])
        session["full_name"] = cust.full_name if cust else email
        flash(f"Welcome back, {session['full_name']}!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# ── Cart ──────────────────────────────────────────────────────────────────────
@app.route("/cart")
def cart():
    g = require_login()
    if g: return g
    if is_admin(): return redirect(url_for("admin_dashboard"))
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    return render_template("cart.html", cart=cart_obj)

@app.route("/cart/add", methods=["POST"])
def cart_add():
    g = require_login()
    if g: return g
    book_id = request.form.get("book_id","")
    try: qty = int(request.form.get("quantity",1))
    except ValueError: qty = 1
    book = catalogue.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("index"))
    if not book.is_in_stock():
        flash("This book is currently out of stock.", "danger")
        return redirect(url_for("book_detail", book_id=book_id))
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    ok, msg = cart_obj.add_book(book.book_id, book.title, book.price, qty, book.stock_quantity)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("cart"))

@app.route("/cart/remove/<cart_item_id>", methods=["POST"])
def cart_remove(cart_item_id):
    g = require_login()
    if g: return g
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    cart_obj.remove_item(cart_item_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))

@app.route("/cart/update", methods=["POST"])
def cart_update():
    g = require_login()
    if g: return g
    cid = request.form.get("cart_item_id","")
    try: qty = int(request.form.get("quantity",1))
    except ValueError: qty = 1
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    item = next((i for i in cart_obj.items if i.cart_item_id == cid), None)
    if item:
        book = catalogue.get_book_by_id(item.book_id)
        stock = book.stock_quantity if book else 999
        ok, msg = cart_obj.update_quantity(cid, qty, stock)
        flash(msg, "success" if ok else "danger")
    return redirect(url_for("cart"))

# ── Checkout ──────────────────────────────────────────────────────────────────
@app.route("/checkout", methods=["GET","POST"])
def checkout():
    g = require_login()
    if g: return g
    if is_admin(): return redirect(url_for("admin_dashboard"))
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    if cart_obj.is_empty():
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))
    customer = Customer.load(session["account_id"])
    if request.method == "POST":
        address = request.form.get("delivery_address","").strip()
        if not address:
            flash("Delivery address is required.", "danger")
            return render_template("checkout.html", cart=cart_obj, customer=customer, address="")
        subtotal = cart_obj.get_total_amount()
        tax = round(subtotal * 0.10, 2)
        total = round(subtotal + tax, 2)
        session["pending_address"] = address
        return render_template("payment.html", cart=cart_obj,
                               subtotal=subtotal, tax=tax, total=total, address=address)
    return render_template("checkout.html", cart=cart_obj, customer=customer,
                           address=customer.shipping_address if customer else "")

@app.route("/payment", methods=["POST"])
def payment():
    g = require_login()
    if g: return g
    # Validate card fields
    card_num = request.form.get("card_number","").replace(" ","")
    card_name = request.form.get("card_name","").strip()
    expiry = request.form.get("expiry","").strip()
    cvv = request.form.get("cvv","").strip()
    errors = []
    if len(card_num) != 16 or not card_num.isdigit():
        errors.append("Card number must be 16 digits.")
    if not card_name:
        errors.append("Cardholder name is required.")
    if not expiry or len(expiry) != 5 or "/" not in expiry:
        errors.append("Expiry must be in MM/YY format.")
    if not cvv or not cvv.isdigit() or len(cvv) not in (3,4):
        errors.append("CVV must be 3 or 4 digits.")
    if errors:
        cart_obj = ShoppingCart.load_or_create(session["account_id"])
        subtotal = cart_obj.get_total_amount()
        tax = round(subtotal*0.10,2)
        total = round(subtotal+tax,2)
        for e in errors: flash(e,"danger")
        return render_template("payment.html", cart=cart_obj, subtotal=subtotal,
                               tax=tax, total=total, address=session.get("pending_address",""))
    # Create order
    cart_obj = ShoppingCart.load_or_create(session["account_id"])
    address = session.get("pending_address","")
    ok, msg, order_id = cart_obj.checkout(session["account_id"], address)
    if not ok:
        flash(msg,"danger")
        return redirect(url_for("cart"))
    # Process payment via Order facade
    order = Order.load_and_pay(order_id, address)
    session.pop("pending_address", None)
    return render_template("confirmation.html",
                           success=order["success"],
                           message=order["message"],
                           order_id=order_id,
                           invoice=order.get("invoice"),
                           receipt=order.get("receipt"),
                           tracking=order.get("tracking"))

# ── Account ───────────────────────────────────────────────────────────────────
@app.route("/account")
def account():
    g = require_login()
    if g: return g
    if is_admin(): return redirect(url_for("admin_dashboard"))
    customer = Customer.load(session["account_id"])
    orders = customer.get_order_history() if customer else []
    return render_template("account.html", customer=customer, orders=orders)

@app.route("/account/update", methods=["POST"])
def account_update():
    g = require_login()
    if g: return g
    customer = Customer.load(session["account_id"])
    if not customer: return redirect(url_for("logout"))
    f = request.form
    ok, msg = customer.update_profile(f.get("first_name",""), f.get("last_name",""),
                                      f.get("phone",""), f.get("address",""))
    if ok: session["full_name"] = f"{f.get('first_name','')} {f.get('last_name','')}".strip()
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("account"))

# ── Admin ─────────────────────────────────────────────────────────────────────
@app.route("/admin")
def admin_dashboard():
    g = require_admin()
    if g: return g
    books = catalogue.get_all_books_admin()
    return render_template("admin/dashboard.html", books=books)

@app.route("/admin/books/add", methods=["GET","POST"])
def admin_add_book():
    g = require_admin()
    if g: return g
    if request.method == "POST":
        f = request.form
        ok, msg = catalogue.add_book(f.get("isbn",""), f.get("title",""),
                                     f.get("author",""), f.get("price",0),
                                     f.get("genre",""), f.get("description",""),
                                     f.get("stock_quantity",0))
        flash(msg, "success" if ok else "danger")
        if ok: return redirect(url_for("admin_dashboard"))
        return render_template("admin/book_form.html", book=None, form=f)
    return render_template("admin/book_form.html", book=None, form={})

@app.route("/admin/books/edit/<book_id>", methods=["GET","POST"])
def admin_edit_book(book_id):
    g = require_admin()
    if g: return g
    book = catalogue.get_book_by_id(book_id)
    if not book:
        flash("Book not found.","danger")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        f = request.form
        ok, msg = catalogue.update_book(book_id, f.get("isbn",""), f.get("title",""),
                                        f.get("author",""), f.get("price",0),
                                        f.get("genre",""), f.get("description",""),
                                        f.get("stock_quantity",0))
        flash(msg, "success" if ok else "danger")
        if ok: return redirect(url_for("admin_dashboard"))
        return render_template("admin/book_form.html", book=book, form=f)
    return render_template("admin/book_form.html", book=book, form={})

@app.route("/admin/books/remove/<book_id>", methods=["POST"])
def admin_remove_book(book_id):
    g = require_admin()
    if g: return g
    ok, msg = catalogue.remove_book(book_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/books/restore/<book_id>", methods=["POST"])
def admin_restore_book(book_id):
    g = require_admin()
    if g: return g
    ok, msg = catalogue.restore_book(book_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/orders")
def admin_orders():
    g = require_admin()
    if g: return g
    admin = Admin.load(session["account_id"])
    orders = admin.get_all_orders() if admin else []
    return render_template("admin/orders.html", orders=orders)

@app.route("/admin/reports", methods=["GET","POST"])
def admin_reports():
    g = require_admin()
    if g: return g
    report, period = None, "MONTHLY"
    if request.method == "POST":
        period = request.form.get("period","MONTHLY")
        admin = Admin.load(session["account_id"])
        if admin: report = admin.generate_sales_report(period)
    return render_template("admin/reports.html", report=report, period=period)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
