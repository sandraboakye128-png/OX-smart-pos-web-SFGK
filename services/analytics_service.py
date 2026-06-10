from database.db import get_connection


def get_summary_multi(period="daily"):
    conn = get_connection()
    cursor = conn.cursor()

    query_map = {
        "daily": "DATE(s.date)=DATE('now','localtime')",
        "weekly": "DATE(s.date) >= DATE('now','-6 days')",
        "monthly": "strftime('%m', s.date)=strftime('%m','now')",
        "yearly": "strftime('%Y', s.date)=strftime('%Y','now')"
    }
    where_clause = query_map.get(period, "1=1")

    # Fixed: sum s.total directly from sales, not multiplied by items
    cursor.execute(f"""
        SELECT 
            IFNULL(SUM(s.total),0),
            IFNULL(SUM(s.discount),0)
        FROM sales s
        WHERE {where_clause}
        AND s.reversed = 0
    """)
    total_sales, total_discount = cursor.fetchone()

    # Items sold and profit still need sales_items join, but profit per item is fine
    cursor.execute(f"""
        SELECT 
            IFNULL(SUM(si.quantity),0),
            IFNULL(SUM(si.profit),0)
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE {where_clause}
        AND s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = si.product_id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
    """)
    items_sold, profit = cursor.fetchone()

    conn.close()
    return (items_sold, total_sales, total_discount, total_sales, profit)  # subtotal = total for simplicity


def get_top_products_multi(period="daily", limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    query_map = {
        "daily": "DATE(s.date)=DATE('now','localtime')",
        "weekly": "DATE(s.date) >= DATE('now','-6 days')",
        "monthly": "strftime('%m', s.date)=strftime('%m','now')",
        "yearly": "strftime('%Y', s.date)=strftime('%Y','now')"
    }
    where_clause = query_map.get(period, "1=1")

    cursor.execute(f"""
        SELECT 
            p.name, p.brand, p.category, SUM(si.quantity) as qty
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        JOIN products p ON p.id = si.product_id
        WHERE {where_clause}
        AND s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
        GROUP BY si.product_id
        ORDER BY qty DESC
        LIMIT ?
    """, (limit,))

    data = cursor.fetchall()
    conn.close()
    return data


def get_sales_trend_multi(period="daily"):
    conn = get_connection()
    cursor = conn.cursor()

    # Simplified: group by date/hour based on period, sum sales.total directly
    if period == "daily":
        group = "strftime('%H', s.date)"
    elif period == "weekly":
        group = "strftime('%w', s.date)"
    elif period == "monthly":
        group = "strftime('%d', s.date)"
    else:
        group = "strftime('%m', s.date)"

    cursor.execute(f"""
        SELECT 
            {group} as label,
            IFNULL(SUM(s.total),0) as sales_total
        FROM sales s
        WHERE s.reversed = 0
        GROUP BY label
        ORDER BY label
    """)
    sales_data = cursor.fetchall()

    cursor.execute(f"""
        SELECT 
            {group} as label,
            IFNULL(SUM(si.profit),0) as profit_total
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE s.reversed = 0
        GROUP BY label
        ORDER BY label
    """)
    profit_data = cursor.fetchall()

    conn.close()

    profit_dict = {p[0]: p[1] for p in profit_data}
    final = [(s[0], s[1], profit_dict.get(s[0], 0)) for s in sales_data]
    return final