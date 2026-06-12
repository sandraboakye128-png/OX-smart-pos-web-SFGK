from database.db import get_connection
from datetime import datetime, timedelta, date

def get_summary_multi(period="daily", start_date=None, end_date=None):
    """Get sales summary for period or custom date range"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # For custom date range (from date picker)
    if start_date and end_date:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.date::date BETWEEN %s AND %s
            AND s.reversed = 0
        """, (start_date, end_date))
    
    # For Today button
    elif period == "daily":
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
        """)
    
    # For This Week button (last 7 days including today)
    elif period == "weekly":
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.date >= CURRENT_DATE - INTERVAL '6 days'
            AND s.reversed = 0
        """)
    
    # For This Month button
    elif period == "monthly":
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND s.reversed = 0
        """)
    
    # For This Year button
    elif period == "yearly":
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND s.reversed = 0
        """)
    
    # For All Time button
    elif period == "all":
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.reversed = 0
        """)
    
    else:
        # Default to daily
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
        """)
    
    result = cursor.fetchone()
    conn.close()
    
    total_sales = float(result[0] if result[0] else 0)
    total_discount = float(result[1] if result[1] else 0)
    total_profit = float(result[2] if result[2] else 0)
    items_sold = int(result[3] if result[3] else 0)
    
    return (items_sold, total_sales, total_discount, total_sales, total_profit)


def get_top_products_multi(period="daily", limit=10, start_date=None, end_date=None):
    """Get top selling products for period or custom range"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_date and end_date:
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE s.date::date BETWEEN %s AND %s
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
        """, (start_date, end_date, limit))
    elif period == "weekly":
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE s.date >= CURRENT_DATE - INTERVAL '6 days'
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
    elif period == "monthly":
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE)
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
    elif period == "yearly":
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
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
    elif period == "all":
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE s.reversed = 0
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
    else:  # daily
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE s.date::date = CURRENT_DATE
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


def get_sales_trend_multi(period="daily", start_date=None, end_date=None):
    """Get sales trend data for chart"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_date and end_date:
        cursor.execute("""
            SELECT 
                s.date::date as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date::date BETWEEN %s AND %s
            AND s.reversed = 0
            GROUP BY s.date::date
            ORDER BY label ASC
        """, (start_date, end_date))
    elif period == "weekly":
        cursor.execute("""
            SELECT 
                s.date::date as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date >= CURRENT_DATE - INTERVAL '6 days'
            AND s.reversed = 0
            GROUP BY s.date::date
            ORDER BY label ASC
        """)
    elif period == "monthly":
        cursor.execute("""
            SELECT 
                s.date::date as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND s.reversed = 0
            GROUP BY s.date::date
            ORDER BY label ASC
        """)
    elif period == "yearly":
        cursor.execute("""
            SELECT 
                DATE_TRUNC('month', s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND s.reversed = 0
            GROUP BY DATE_TRUNC('month', s.date)
            ORDER BY label ASC
        """)
    elif period == "all":
        cursor.execute("""
            SELECT 
                DATE_TRUNC('month', s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.reversed = 0
            GROUP BY DATE_TRUNC('month', s.date)
            ORDER BY label ASC
            LIMIT 24
        """)
    else:  # daily
        cursor.execute("""
            SELECT 
                s.date::date as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
            GROUP BY s.date::date
            ORDER BY label ASC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        label = row[0]
        if period in ['yearly', 'all']:
            if hasattr(label, 'strftime'):
                label = label.strftime('%b %Y')
            else:
                label = str(label)
        else:
            if hasattr(label, 'strftime'):
                label = label.strftime('%Y-%m-%d')
            else:
                label = str(label)
        
        result.append({
            'label': str(label),
            'sales': float(row[1]),
            'profit': float(row[2])
        })
    
    return result