# Favourite Books Online Bookstore
## SWE30003 Assignment 3 — Group 3

### Tech Stack
- **Language:** Python 3.11
- **Framework:** Flask 3.0.3
- **Storage:** JSON files (persistent file-based storage)
- **Coding Standard:** PEP 8 — https://peps.python.org/pep-0008/

### Four Implemented Business Areas
1. Customer Account Creation and Login
2. Book Browsing and Shopping Cart Management
3. Checkout and Order Creation with Simulated Payment
4. Admin Book Catalogue Management + Sales Reports

### How to Run
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Open browser at
http://localhost:5000
```

### Default Admin Credentials
- Email: admin@favouritebooks.com
- Password: Admin@1234

### Project Structure
```
favouritebooks/
├── app.py                  # Flask routes (entry point)
├── requirements.txt
├── README.md
├── database/
│   ├── storage.py          # JSON Storage singleton
├── models/
│   ├── account.py          # Abstract Account + DTOs
│   ├── customer.py         # Customer class
│   ├── admin.py            # Admin class
│   ├── book.py             # Book + BookCatalogue
│   └── order.py            # Cart, Order, Invoice, Payment, etc.
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── book_detail.html
│   ├── register.html
│   ├── login.html
│   ├── cart.html
│   ├── checkout.html
│   ├── payment.html
│   ├── confirmation.html
│   ├── account.html
│   └── admin/
│       ├── dashboard.html
│       ├── book_form.html
│       ├── orders.html
│       └── reports.html
└── data/                   # JSON files (auto-created on first run)
    ├── accounts.json
    ├── books.json
    ├── orders.json
    └── ...
```
