import os
import sqlite3

# ---------- Ensure folders exist ----------
DB_DIR = "database"
RECEIPTS_DIR = "receipts"
REPORTS_DIR = "reports"

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ---------- DATABASE PATHS (for SQLite) ----------
DB_PATH = os.path.join(DB_DIR, "retail.db")
AUTH_DB_PATH = os.path.join(DB_DIR, "auth.db")

# ---------- Check if we are on Render (PostgreSQL) ----------
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    # Use the default cursor (returns tuples, not dictionaries)
    print("Using PostgreSQL (Supabase) - default cursor")

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        subtotal REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        total REAL,
        profit REAL,
        date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS deleted_products (
        id SERIAL PRIMARY KEY,
        name TEXT,
        brand TEXT,
        cost_price REAL,
        selling_price REAL,
        stock INTEGER,
        category TEXT,
        discount REAL DEFAULT 0,
        action TEXT DEFAULT 'deleted',
        source TEXT DEFAULT 'product',
        deleted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        batch_id INTEGER,
        batch_quantity INTEGER,
        batch_remaining INTEGER,
        product_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS purchases (
        id SERIAL PRIMARY KEY,
        product_name TEXT NOT NULL,
        brand TEXT,
        category TEXT,
        quantity INTEGER,
        cost_price REAL,
        discount REAL DEFAULT 0,
        total REAL,
        selling_price REAL,
        date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        remaining_stock INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS purchase_batches (
        id SERIAL PRIMARY KEY,
        product_id INTEGER,
        quantity INTEGER,
        remaining_quantity INTEGER,
        cost_price REAL,
        discount REAL,
        selling_price REAL,
        date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        action TEXT DEFAULT 'created'
    );

    CREATE TABLE IF NOT EXISTS sales_items (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        product_id INTEGER,
        unit_name TEXT,
        conversion_factor REAL,
        selling_price REAL
    );

    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """

    POSTGRES_MIGRATIONS = [
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS category TEXT",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS discount REAL DEFAULT 0",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS base_unit TEXT DEFAULT 'piece'",
        "ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount REAL DEFAULT 0",
        "ALTER TABLE sales ADD COLUMN IF NOT EXISTS subtotal REAL DEFAULT 0",
        "ALTER TABLE sales ADD COLUMN IF NOT EXISTS product_id INTEGER",
        "ALTER TABLE sales ADD COLUMN IF NOT EXISTS reversed INTEGER DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS selling_price REAL DEFAULT 0",
        "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS remaining_stock INTEGER DEFAULT 0",
        "ALTER TABLE purchase_batches ADD COLUMN IF NOT EXISTS selling_price REAL DEFAULT 0",
        "ALTER TABLE purchase_batches ADD COLUMN IF NOT EXISTS action TEXT DEFAULT 'created'",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS category TEXT",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS discount REAL DEFAULT 0",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS action TEXT DEFAULT 'deleted'",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'product'",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS batch_id INTEGER",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS batch_quantity INTEGER",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS batch_remaining INTEGER",
        "ALTER TABLE deleted_products ADD COLUMN IF NOT EXISTS product_id INTEGER",
        "ALTER TABLE sales_items ADD COLUMN IF NOT EXISTS unit_id INTEGER",
        "ALTER TABLE sales_items ADD COLUMN IF NOT EXISTS unit_quantity REAL",
        "CREATE TABLE IF NOT EXISTS product_units (id SERIAL PRIMARY KEY, product_id INTEGER, unit_name TEXT, conversion_factor REAL, selling_price REAL)"
    ]

    def get_connection():
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # Create tables if not exist
        cursor.execute(SCHEMA)
        # Apply migrations (ALTER TABLE … IF NOT EXISTS)
        for migration in POSTGRES_MIGRATIONS:
            try:
                cursor.execute(migration)
            except Exception:
                pass  # column already exists or other benign error
        conn.commit()
        return conn

else:
    # ---------- SQLite (local development) ----------
    import sqlite3
    print("Using SQLite (local)")

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
        try: cursor.execute("ALTER TABLE products ADD COLUMN category TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE products ADD COLUMN discount REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE products ADD COLUMN base_unit TEXT DEFAULT 'piece'")
        except: pass

        try: cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE sales ADD COLUMN subtotal REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE sales ADD COLUMN product_id INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE sales ADD COLUMN reversed INTEGER DEFAULT 0")
        except: pass

        try: cursor.execute("ALTER TABLE purchases ADD COLUMN selling_price REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE purchases ADD COLUMN remaining_stock INTEGER DEFAULT 0")
        except: pass

        try: cursor.execute("ALTER TABLE purchase_batches ADD COLUMN selling_price REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE purchase_batches ADD COLUMN action TEXT DEFAULT 'created'")
        except: pass

        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN category TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN discount REAL DEFAULT 0")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN action TEXT DEFAULT 'deleted'")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN source TEXT DEFAULT 'product'")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_id INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_quantity INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN batch_remaining INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE deleted_products ADD COLUMN product_id INTEGER")
        except: pass

        try: cursor.execute("ALTER TABLE sales_items ADD COLUMN unit_id INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE sales_items ADD COLUMN unit_quantity REAL")
        except: pass

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