"""
Creates a realistic e-commerce SQLite database for local demonstration and testing.
Includes customers, orders, order_items, and products with intentional quality anomalies.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3

SAMPLE_DB = Path(__file__).resolve().parent / "sample.db"


def init_sample_db():
    if SAMPLE_DB.exists():
        SAMPLE_DB.unlink()

    conn = sqlite3.connect(SAMPLE_DB)
    cur = conn.cursor()

    # 1. Customers
    cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT,
            status TEXT DEFAULT 'ACTIVE',
            credit_limit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.executemany("""
        INSERT INTO customers (customer_id, full_name, email, status, credit_limit, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (1, "Alice Morgan", "alice.m@enterprise.com", "ACTIVE", 5000.0, "2026-01-15 10:00:00"),
        (2, "Bob Vance", "bob@vancerefrig.com", "ACTIVE", 3500.0, "2026-02-10 14:30:00"),
        (3, "Charlie Day", "charlie_invalid_email", "ACTIVE", 1200.0, "2026-03-01 09:15:00"),  # invalid email
        (4, "Diana Prince", "diana@themyscira.gov", "INACTIVE", 10000.0, "2026-03-12 11:20:00"),
        (5, "Evan Wright", None, "SUSPENDED", 0.0, "2026-04-05 16:45:00")
    ])

    # 2. Orders
    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TIMESTAMP NOT NULL,
            status TEXT NOT NULL,
            total_amount REAL NOT NULL
        )
    """)
    cur.executemany("""
        INSERT INTO orders (order_id, customer_id, order_date, status, total_amount)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (101, 1, "2026-04-10 10:30:00", "COMPLETED", 250.50),
        (102, 2, "2026-04-12 11:00:00", "COMPLETED", 149.00),
        (103, 1, "2026-04-15 14:00:00", "PENDING", 45.00),
        (104, 3, "2026-04-18 16:20:00", "FAILED", -20.00),  # anomaly: negative amount
        (105, 4, "2026-04-20 09:10:00", "COMPLETED", 980.00)
    ])

    # 3. Products
    cur.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL
        )
    """)
    cur.executemany("""
        INSERT INTO products (product_id, sku, product_name, price, stock_quantity)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, "SKU-LAP-001", "Enterprise Laptop Pro", 1299.99, 45),
        (2, "SKU-MNT-002", "4K Ultra-Wide Monitor", 499.50, 80),
        (3, "SKU-KBD-003", "Mechanical Keyboard", 129.00, 150),
        (4, "SKU-MSE-004", "Ergonomic Mouse", 69.90, 200)
    ])

    conn.commit()
    conn.close()
    print(f"Sample DB created at {SAMPLE_DB}")


if __name__ == "__main__":
    init_sample_db()
