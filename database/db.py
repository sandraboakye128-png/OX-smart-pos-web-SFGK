import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------- Ensure folders exist ----------
DB_DIR = "database"
RECEIPTS_DIR = "receipts"
REPORTS_DIR = "reports"

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ---------- DATABASE PATHS ----------
DB_PATH = os.path.join(DB_DIR, "retail.db")
AUTH_DB_PATH = os.path.join(DB_DIR, "auth.db")

# ---------- RETAIL SCHEMA ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    cost_price REAL,
    selling_price REAL,
    stock INTEGER,
    category TEXT,
    discount REAL DEFAULT 0,
    base_unit TEXT DEFAULT 'piece'
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtotal REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    total REAL,
    profit REAL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deleted_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    brand TEXT,
    cost_price REAL,
    selling_price REAL,
    stock INTEGER,
    category TEXT,
    discount REAL DEFAULT 0,
    action TEXT DEFAULT 'deleted',
    source TEXT DEFAULT 'product',
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id INTEGER,
    batch_quantity INTEGER,
    batch_remaining INTEGER,
    product_id INTEGER
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    quantity INTEGER,
    cost_price REAL,
    discount REAL DEFAULT 0,
    total REAL,
    selling_price REAL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remaining_stock INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS purchase_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    quantity INTEGER,
    remaining_quantity INTEGER,
    cost_price REAL,
    discount REAL,
    selling_price REAL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT DEFAULT 'created'
);

CREATE TABLE IF NOT EXISTS sales_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    product_id INTEGER,
    batch_id INTEGER,
    quantity INTEGER,
    cost_price REAL,
    selling_price REAL,
    profit REAL,
    unit_id INTEGER,
    unit_quantity REAL
);

CREATE TABLE IF NOT EXISTS product_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    unit_name TEXT,
    conversion_factor REAL,
    selling_price REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

# ---------- USERS SCHEMA ----------
AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)

    # ---------- SAFE MIGRATIONS ----------

    # PRODUCTS
    try: cursor.execute("ALTER TABLE products ADD COLUMN category TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE products ADD COLUMN discount REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE products ADD COLUMN base_unit TEXT DEFAULT 'piece'")
    except: pass

    # SALES
    try: cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE sales ADD COLUMN subtotal REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE sales ADD COLUMN product_id INTEGER")
    except: pass
    # NEW: reversed column for sale reversal (0 = not reversed, 1 = reversed)
    try: cursor.execute("ALTER TABLE sales ADD COLUMN reversed INTEGER DEFAULT 0")
    except: pass

    # PURCHASES
    try: cursor.execute("ALTER TABLE purchases ADD COLUMN selling_price REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE purchases ADD COLUMN remaining_stock INTEGER DEFAULT 0")
    except: pass

    # PURCHASE BATCHES
    try: cursor.execute("ALTER TABLE purchase_batches ADD COLUMN selling_price REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE purchase_batches ADD COLUMN action TEXT DEFAULT 'created'")
    except: pass

    # DELETED PRODUCTS - original columns
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN category TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN discount REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN action TEXT DEFAULT 'deleted'")
    except: pass
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN source TEXT DEFAULT 'product'")
    except: pass

    # DELETED PRODUCTS - batch restore columns
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_id INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_quantity INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_remaining INTEGER")
    except: pass

    # DELETED PRODUCTS - product_id column (CRITICAL for batch tracking)
    try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN product_id INTEGER")
    except: pass

    # SALES_ITEMS - unit support columns
    try: cursor.execute("ALTER TABLE sales_items ADD COLUMN unit_id INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE sales_items ADD COLUMN unit_quantity REAL")
    except: pass

    # PRODUCT_UNITS table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                unit_name TEXT,
                conversion_factor REAL,
                selling_price REAL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
    except: pass

    conn.commit()

    # ---------- AUTH DB ----------
    auth_conn = sqlite3.connect(AUTH_DB_PATH)
    auth_cursor = auth_conn.cursor()
    auth_cursor.executescript(AUTH_SCHEMA)
    auth_conn.commit()
    auth_conn.close()

    return conn