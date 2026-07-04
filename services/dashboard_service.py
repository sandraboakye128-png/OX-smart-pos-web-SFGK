from database.db import get_connection
from datetime import date, datetime

# ----------------- TOTAL SALES (with optional date or datetime range) -----------------
def get_today_sales(selected_date=None, start_datetime=None, end_datetime=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_datetime and end_datetime:
        cursor.execute("""
            SELECT COALESCE(SUM(s.total), 0)
            FROM sales s
            WHERE s.date BETWEEN %s AND %s
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """, (start_datetime, end_datetime))
    elif selected_date:
        dt = selected_date.isoformat() if hasattr(selected_date, 'isoformat') else selected_date
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
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """, (dt,))
    else:
        cursor.execute("""
            SELECT COALESCE(SUM(s.total), 0)
            FROM sales s
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """)
    
    total = cursor.fetchone()[0]
    conn.close()
    return total


# ----------------- TOTAL PROFIT (NET) (with optional date or datetime range) -----------------
def get_today_profit(selected_date=None, start_datetime=None, end_datetime=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_datetime and end_datetime:
        cursor.execute("""
            SELECT COALESCE(SUM(s.profit), 0)
            FROM sales s
            WHERE s.date BETWEEN %s AND %s
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """, (start_datetime, end_datetime))
    elif selected_date:
        dt = selected_date.isoformat() if hasattr(selected_date, 'isoformat') else selected_date
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
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """, (dt,))
    else:
        cursor.execute("""
            SELECT COALESCE(SUM(s.profit), 0)
            FROM sales s
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """)
    
    profit = cursor.fetchone()[0]
    conn.close()
    return profit


# ----------------- TOTAL PRODUCTS (ALL unique products, including stock 0 and without batches) -----------------
def get_total_products():
    """
    Count ALL unique products (grouped by name + brand) 
    including those with stock = 0 and those without any batches.
    Excludes permanently deleted products.
    FIXED: Previously excluded products without batches, causing incorrect count.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT CONCAT(p.name, '|', p.brand)) as unique_products
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
    """)
    total = cursor.fetchone()[0]
    conn.close()
    return total


# ----------------- TOTAL BATCHES (all active batches, regardless of stock) -----------------
def get_total_batches():
    """
    Count all purchase batches that belong to non‑deleted products.
    This includes both Accessories and Screens.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM purchase_batches pb
        JOIN products p ON p.id = pb.product_id
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ----------------- LOW STOCK PRODUCTS (including zero stock and products without batches) -----------------
def get_low_stock_products(threshold=10):
    """
    Return products with stock <= threshold (including 0).
    FIXED: Now includes ALL products with low stock, even those without batches.
    Previously required products to have at least one batch, which excluded some products.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name, p.brand, p.category, p.stock
        FROM products p
        WHERE p.stock <= %s
        AND p.stock >= 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
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
                AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                AND dp.source = 'product'
            )
        )
        GROUP BY s.date::date
        ORDER BY s.date::date
    """)
    data = cursor.fetchall()
    conn.close()
    return data


# ----------------- TOP PRODUCTS (with optional date or datetime range) -----------------
def get_top_products(selected_date=None, limit=5, start_datetime=None, end_datetime=None):
    conn = get_connection()
    cursor = conn.cursor()
    params = []
    query = """
        SELECT p.name, p.brand, p.category, COALESCE(SUM(si.quantity), 0) as qty
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        JOIN products p ON si.product_id = p.id
        WHERE s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
    """
    
    if start_datetime and end_datetime:
        query += " AND s.date BETWEEN %s AND %s"
        params.extend([start_datetime, end_datetime])
    elif selected_date:
        dt = selected_date.isoformat() if hasattr(selected_date, 'isoformat') else selected_date
        query += " AND s.date::date = %s"
        params.append(dt)
    
    query += " GROUP BY si.product_id, p.name, p.brand, p.category ORDER BY qty DESC LIMIT %s"
    params.append(limit)
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products


# ----------------- SALES HISTORY (NET) (with optional date or datetime range) -----------------
def get_sales_history(selected_date=None, start_datetime=None, end_datetime=None):
    conn = get_connection()
    cursor = conn.cursor()
    params = []
    
    query = """
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
                AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                AND dp.source = 'product'
            )
        )
    """
    
    if start_datetime and end_datetime:
        query += " AND s.date BETWEEN %s AND %s"
        params.extend([start_datetime, end_datetime])
    elif selected_date:
        dt = selected_date.isoformat() if hasattr(selected_date, 'isoformat') else selected_date
        query += " AND s.date::date = %s"
        params.append(dt)
    
    query += " GROUP BY s.date::date ORDER BY s.date::date DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


# ----------------- DASHBOARD SUMMARY (Combines all data for the dashboard) -----------------
def get_dashboard_summary(start_datetime=None, end_datetime=None):
    """
    Get all dashboard summary data in one call.
    Returns sales, profit, total_products, total_batches, low_stock_count, and low_stock_products.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get sales and profit
    if start_datetime and end_datetime:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0) as total_sales,
                COALESCE(SUM(s.profit), 0) as total_profit
            FROM sales s
            WHERE s.date BETWEEN %s AND %s
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """, (start_datetime, end_datetime))
    else:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0) as total_sales,
                COALESCE(SUM(s.profit), 0) as total_profit
            FROM sales s
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
            AND EXISTS (
                SELECT 1 FROM sales_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = s.id
                AND NOT EXISTS (
                    SELECT 1 FROM deleted_products dp 
                    WHERE dp.product_id = p.id 
                    AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                    AND dp.source = 'product'
                )
            )
        """)
    
    sales_data = cursor.fetchone()
    total_sales = sales_data[0] or 0
    total_profit = sales_data[1] or 0
    
    # Get total products (ALL products, including those without batches)
    cursor.execute("""
        SELECT COUNT(DISTINCT CONCAT(p.name, '|', p.brand)) as unique_products
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
    """)
    total_products = cursor.fetchone()[0] or 0
    
    # Get total batches
    cursor.execute("""
        SELECT COUNT(*)
        FROM purchase_batches pb
        JOIN products p ON p.id = pb.product_id
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
    """)
    total_batches = cursor.fetchone()[0] or 0
    
    # Get low stock products (ALL products with stock <= 10, including those without batches)
    cursor.execute("""
        SELECT p.name, p.brand, p.category, p.stock
        FROM products p
        WHERE p.stock <= 10
        AND p.stock >= 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
        ORDER BY p.stock ASC
    """)
    low_stock_products = cursor.fetchall()
    
    conn.close()
    
    return {
        'sales': total_sales,
        'profit': total_profit,
        'total_products': total_products,
        'total_batches': total_batches,
        'low_stock_count': len(low_stock_products),
        'low_stock_products': low_stock_products
    }