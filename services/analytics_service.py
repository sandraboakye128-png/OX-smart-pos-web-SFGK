from database.db import get_connection

def get_summary_multi(period="daily"):
    conn = get_connection()
    cursor = conn.cursor()

    if period == "weekly":
        date_filter = "s.date >= CURRENT_DATE - INTERVAL '6 days'"
    elif period == "monthly":
        date_filter = "EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif period == "yearly":
        date_filter = "EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:  # daily
        date_filter = "s.date::date = CURRENT_DATE"

    # Total sales, discount, and net profit from sales table
    cursor.execute(f"""
        SELECT 
            COALESCE(SUM(s.total), 0),
            COALESCE(SUM(s.discount), 0),
            COALESCE(SUM(s.profit), 0)
        FROM sales s
        WHERE {date_filter}
        AND s.reversed = 0
    """)
    total_sales, total_discount, total_profit = cursor.fetchone()

    # Items sold from sales_items
    cursor.execute(f"""
        SELECT COALESCE(SUM(si.quantity), 0)
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        WHERE {date_filter}
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

    if period == "weekly":
        date_filter = "s.date >= CURRENT_DATE - INTERVAL '6 days'"
    elif period == "monthly":
        date_filter = "EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif period == "yearly":
        date_filter = "EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:  # daily
        date_filter = "s.date::date = CURRENT_DATE"

    cursor.execute(f"""
        SELECT 
            p.name, p.brand, p.category, SUM(si.quantity) as qty
        FROM sales_items si
        JOIN sales s ON si.sale_id = s.id
        JOIN products p ON p.id = si.product_id
        WHERE {date_filter}
        AND s.reversed = 0
        AND NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = p.id 
            AND dp.action = 'PERMANENTLY DELETED' 
            AND dp.source = 'product'
        )
        GROUP BY si.product_id, p.name, p.brand, p.category
        ORDER BY qty DESC
        LIMIT %s
    """, (limit,))

    data = cursor.fetchall()
    conn.close()
    return data


def get_sales_trend_multi(period="daily"):
    conn = get_connection()
    cursor = conn.cursor()

    if period == "daily":
        group_expr = "EXTRACT(HOUR FROM s.date)"
    elif period == "weekly":
        group_expr = "EXTRACT(DOW FROM s.date)"   # 0=Sunday
    elif period == "monthly":
        group_expr = "EXTRACT(DAY FROM s.date)"
    else:  # yearly
        group_expr = "EXTRACT(MONTH FROM s.date)"

    cursor.execute(f"""
        SELECT 
            {group_expr} as label,
            COALESCE(SUM(s.total), 0) as sales_total,
            COALESCE(SUM(s.profit), 0) as profit_total
        FROM sales s
        WHERE s.reversed = 0
        GROUP BY label
        ORDER BY label
    """)
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1], r[2]) for r in rows]