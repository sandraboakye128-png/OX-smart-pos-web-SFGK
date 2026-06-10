from database.db import get_connection
from datetime import date

# ----------------- TODAY'S TOTAL SALES -----------------
def get_today_sales(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    dt = selected_date or date.today()
    dt = dt.isoformat()

    cursor.execute("""
        SELECT COALESCE(SUM(s.total), 0)
        FROM sales s
        WHERE s.date::date = %s
        AND s.reversed = 0
        AND EXISTS (
            SELECT 1 FROM sales_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = s.id
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
        )
    """, (dt,))
    total = cursor.fetchone()[0]
    conn.close()
    return total


# ----------------- TODAY'S PROFIT (NET) -----------------
def get_today_profit(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    dt = selected_date or date.today()
    dt = dt.isoformat()

    cursor.execute("""
        SELECT COALESCE(SUM(s.profit), 0)
        FROM sales s
        WHERE s.date::date = %s
        AND s.reversed = 0
        AND EXISTS (
            SELECT 1 FROM sales_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = s.id
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
        )
    """, (dt,))
    profit = cursor.fetchone()[0]
    conn.close()
    return profit


# ----------------- TOTAL PRODUCTS -----------------
def get_total_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
    """)
    total = cursor.fetchone()[0]
    conn.close()
    return total


# ----------------- LOW STOCK PRODUCTS -----------------
def get_low_stock_products(threshold=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name, p.brand, p.category, p.stock
        FROM products p
        WHERE p.stock <= %s
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
        ORDER BY p.stock ASC
    """, (threshold,))
    products = cursor.fetchall()
    conn.close()
    return products


# ----------------- WEEKLY SALES (NET) -----------------
def get_weekly_sales():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.date::date, COALESCE(SUM(s.total), 0)
        FROM sales s
        WHERE s.date >= CURRENT_DATE - INTERVAL '6 days'
        AND s.reversed = 0
        AND EXISTS (
            SELECT 1 FROM sales_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = s.id
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
        )
        GROUP BY s.date::date
        ORDER BY s.date::date
    """)
    data = cursor.fetchall()
    conn.close()
    return data


# ----------------- TOP PRODUCTS -----------------
def get_top_products(selected_date=None, limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    params = []
    query = """
        SELECT p.name, p.brand, p.category, SUM(si.quantity) as qty
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        JOIN products p ON si.product_id = p.id
        WHERE s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
    """
    if selected_date:
        dt = selected_date.isoformat()
        query += " AND s.date::date = %s"
        params.append(dt)
    query += " GROUP BY si.product_id, p.name, p.brand, p.category ORDER BY qty DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products


# ----------------- SALES HISTORY (NET) -----------------
def get_sales_history(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    if selected_date:
        dt = selected_date.isoformat()
        cursor.execute("""
            SELECT s.date::date,
                   COALESCE(SUM(s.total), 0) AS total_sales,
                   COALESCE(SUM(s.profit), 0) AS total_profit,
                   COALESCE(SUM(s.discount), 0) AS total_discount
            FROM sales s
            WHERE s.date::date = %s
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action = 'PERMANENTLY DELETED' 
                    AND dp.source = 'product'
                )
            )
            GROUP BY s.date::date
        """, (dt,))
    else:
        cursor.execute("""
            SELECT s.date::date,
                   COALESCE(SUM(s.total), 0) AS total_sales,
                   COALESCE(SUM(s.profit), 0) AS total_profit,
                   COALESCE(SUM(s.discount), 0) AS total_discount
            FROM sales s
            WHERE s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action = 'PERMANENTLY DELETED' 
                    AND dp.source = 'product'
                )
            )
            GROUP BY s.date::date
            ORDER BY s.date::date DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1], r[2], r[3]) for r in rows]