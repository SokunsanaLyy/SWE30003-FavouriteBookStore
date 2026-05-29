-- schema.sql
-- Favourite Books Online Bookstore — SQLite schema
-- All tables created only if they do not already exist.
-- Foreign key enforcement is enabled via PRAGMA in Database.connect().

CREATE TABLE IF NOT EXISTS accounts (
    account_id   TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role         TEXT NOT NULL CHECK(role IN ('CUSTOMER','ADMIN')),
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id      TEXT PRIMARY KEY REFERENCES accounts(account_id),
    first_name       TEXT NOT NULL,
    last_name        TEXT NOT NULL,
    phone            TEXT,
    shipping_address TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    admin_id    TEXT PRIMARY KEY REFERENCES accounts(account_id),
    role_detail TEXT
);

CREATE TABLE IF NOT EXISTS books (
    book_id        TEXT PRIMARY KEY,
    isbn           TEXT UNIQUE NOT NULL,
    title          TEXT NOT NULL,
    author         TEXT NOT NULL,
    price          REAL NOT NULL,
    genre          TEXT,
    description    TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_available   INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shopping_carts (
    cart_id     TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id TEXT PRIMARY KEY,
    cart_id      TEXT NOT NULL REFERENCES shopping_carts(cart_id) ON DELETE CASCADE,
    book_id      TEXT NOT NULL REFERENCES books(book_id),
    quantity     INTEGER NOT NULL,
    unit_price   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL REFERENCES customers(customer_id),
    total_amount REAL NOT NULL,
    status       TEXT NOT NULL DEFAULT 'PENDING',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id      TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    book_id       TEXT NOT NULL REFERENCES books(book_id),
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id   TEXT PRIMARY KEY,
    order_id     TEXT UNIQUE NOT NULL REFERENCES orders(order_id),
    subtotal     REAL NOT NULL,
    tax_amount   REAL NOT NULL,
    total_amount REAL NOT NULL,
    is_paid      INTEGER NOT NULL DEFAULT 0,
    issued_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id     TEXT PRIMARY KEY,
    order_id       TEXT UNIQUE NOT NULL REFERENCES orders(order_id),
    amount         REAL NOT NULL,
    method         TEXT NOT NULL DEFAULT 'CARD',
    status         TEXT NOT NULL DEFAULT 'PENDING',
    transaction_ref TEXT,
    processed_at   TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id           TEXT PRIMARY KEY,
    order_id             TEXT UNIQUE NOT NULL REFERENCES orders(order_id),
    transaction_reference TEXT NOT NULL,
    amount_paid          REAL NOT NULL,
    payment_method       TEXT NOT NULL,
    issued_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id      TEXT PRIMARY KEY,
    order_id         TEXT UNIQUE NOT NULL REFERENCES orders(order_id),
    delivery_address TEXT NOT NULL,
    shipping_method  TEXT NOT NULL DEFAULT 'STANDARD',
    status           TEXT NOT NULL DEFAULT 'PACKED',
    tracking_number  TEXT,
    estimated_delivery TEXT
);

-- Seed one default admin account (password: Admin@1234)
-- bcrypt hash generated offline for 'Admin@1234'
INSERT OR IGNORE INTO accounts (account_id, email, password_hash, role, created_at)
VALUES (
    'admin-001',
    'admin@favouritebooks.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8Ji6HHrJEoC5G6HoICi',
    'ADMIN',
    datetime('now')
);

INSERT OR IGNORE INTO admins (admin_id, role_detail)
VALUES ('admin-001', 'owner');

-- Seed sample books
INSERT OR IGNORE INTO books (book_id, isbn, title, author, price, genre, description, stock_quantity, is_available, created_at)
VALUES
('book-001','9780743273565','The Great Gatsby','F. Scott Fitzgerald',18.99,'Fiction','A story of wealth, love, and the American Dream set in the 1920s.',12,'1',datetime('now')),
('book-002','9780061096525','To Kill a Mockingbird','Harper Lee',17.99,'Fiction','A profound novel about racial injustice and moral growth in the American South.',8,'1',datetime('now')),
('book-003','9780451524935','1984','George Orwell',16.99,'Dystopian','A chilling vision of a totalitarian society under constant surveillance.',15,'1',datetime('now')),
('book-004','9780316769174','The Catcher in the Rye','J.D. Salinger',15.99,'Fiction','The story of teenage alienation and angst narrated by Holden Caulfield.',5,'1',datetime('now')),
('book-005','9780060850524','Brave New World','Aldous Huxley',17.50,'Dystopian','A futuristic world where society is controlled through pleasure and conditioning.',9,'1',datetime('now')),
('book-006','9780143105428','Pride and Prejudice','Jane Austen',14.99,'Romance','A witty and romantic novel following Elizabeth Bennet and Mr. Darcy.',20,'1',datetime('now')),
('book-007','9780385490818','The Handmaid''s Tale','Margaret Atwood',19.99,'Dystopian','A dark tale of a theocratic dystopia from a handmaid''s perspective.',7,'1',datetime('now')),
('book-008','9780618640157','The Lord of the Rings','J.R.R. Tolkien',34.99,'Fantasy','The epic fantasy trilogy following Frodo''s quest to destroy the One Ring.',3,'1',datetime('now'));
