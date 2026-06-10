from database.db import get_connection
from datetime import date


# ----------------- TODAY'S TOTAL SALES -----------------
def get_today_sales(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    dt = selected_date or date.today()
    dt = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    cursor.execute("""
        SELECT IFNULL(SUM(s.total), 0)
        FROM sales s
        WHERE DATE(s.date)=?
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


# ----------------- TODAY'S PROFIT -----------------
def get_today_profit(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    dt = selected_date or date.today()
    dt = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    cursor.execute("""
        SELECT IFNULL(SUM(si.profit), 0)
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE DATE(s.date)=?
        AND s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = si.product_id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
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
        WHERE p.stock <= ?
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


# ----------------- WEEKLY SALES -----------------
def get_weekly_sales():
    conn = get_connection()
    cursor = conn.cursor()

    # Use subquery to get unique sale totals per day
    cursor.execute("""
        SELECT DATE(s.date), IFNULL(SUM(s.total), 0)
        FROM sales s
        WHERE DATE(s.date) >= DATE('now','-6 day')
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
        GROUP BY DATE(s.date)
        ORDER BY DATE(s.date)
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
        dt = selected_date.isoformat() if hasattr(selected_date, "isoformat") else str(selected_date)
        query += " AND DATE(s.date)=?"
        params.append(dt)

    query += " GROUP BY si.product_id ORDER BY qty DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products


# ----------------- SALES HISTORY (FIXED) -----------------
def get_sales_history(selected_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    # First, get per‑day totals and discounts from the sales table (no join)
    if selected_date:
        dt = selected_date.isoformat() if hasattr(selected_date, "isoformat") else str(selected_date)
        cursor.execute("""
            SELECT DATE(s.date),
                   IFNULL(SUM(s.total), 0) AS total_sales,
                   IFNULL(SUM(s.discount), 0) AS total_discount
            FROM sales s
            WHERE DATE(s.date) = ?
            AND s.reversed = 0
            GROUP BY DATE(s.date)
        """, (dt,))
        sales_rows = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT DATE(s.date),
                   IFNULL(SUM(s.total), 0) AS total_sales,
                   IFNULL(SUM(s.discount), 0) AS total_discount
            FROM sales s
            WHERE s.reversed = 0
            GROUP BY DATE(s.date)
            ORDER BY DATE(s.date) DESC
        """)
        sales_rows = cursor.fetchall()

    # Create a dict with date as key, storing total_sales and total_discount
    sales_dict = {}
    for row in sales_rows:
        date_str = row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0])
        sales_dict[date_str] = {
            'total_sales': row[1],
            'total_discount': row[2],
            'total_profit': 0.0  # placeholder
        }

    # Now get per‑day profit from sales_items (needs join but profit is per item, so safe)
    if selected_date:
        cursor.execute("""
            SELECT DATE(s.date),
                   IFNULL(SUM(si.profit), 0) AS total_profit
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE DATE(s.date) = ?
            AND s.reversed = 0
            GROUP BY DATE(s.date)
        """, (dt,))
    else:
        cursor.execute("""
            SELECT DATE(s.date),
                   IFNULL(SUM(si.profit), 0) AS total_profit
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE s.reversed = 0
            GROUP BY DATE(s.date)
            ORDER BY DATE(s.date) DESC
        """)
    profit_rows = cursor.fetchall()
    conn.close()

    # Merge profit into the dict
    for row in profit_rows:
        date_str = row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0])
        if date_str in sales_dict:
            sales_dict[date_str]['total_profit'] = row[1]
        else:
            # Should not happen, but just in case
            sales_dict[date_str] = {
                'total_sales': 0,
                'total_discount': 0,
                'total_profit': row[1]
            }

    # Convert dict to list of tuples (date, total_sales, total_profit, total_discount) sorted by date
    result = []
    for date_str, vals in sorted(sales_dict.items(), key=lambda x: x[0], reverse=True):
        result.append((date_str, vals['total_sales'], vals['total_profit'], vals['total_discount']))

    return result