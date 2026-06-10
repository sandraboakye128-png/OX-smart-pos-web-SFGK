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

    # Total sales, discount, and net profit from sales table
    cursor.execute(f"""
        SELECT 
            IFNULL(SUM(s.total),0),
            IFNULL(SUM(s.discount),0),
            IFNULL(SUM(s.profit),0)
        FROM sales s
        WHERE {where_clause}
        AND s.reversed = 0
    """)
    total_sales, total_discount, total_profit = cursor.fetchone()

    # Items sold from sales_items
    cursor.execute(f"""
        SELECT IFNULL(SUM(si.quantity),0)
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
    items_sold = cursor.fetchone()[0]

    conn.close()
    return (items_sold, total_sales, total_discount, total_sales, total_profit)


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

    if period == "daily":
        group = "strftime('%H', s.date)"
    elif period == "weekly":
        group = "strftime('%w', s.date)"
    elif period == "monthly":
        group = "strftime('%d', s.date)"
    else:
        group = "strftime('%m', s.date)"

    # Sales total and net profit both from sales table
    cursor.execute(f"""
        SELECT 
            {group} as label,
            IFNULL(SUM(s.total),0) as sales_total,
            IFNULL(SUM(s.profit),0) as profit_total
        FROM sales s
        WHERE s.reversed = 0
        GROUP BY label
        ORDER BY label
    """)
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1], r[2]) for r in rows]