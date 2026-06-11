from database.db import get_connection
from datetime import datetime, timedelta

def get_summary_multi(period="daily", start_date=None, end_date=None):
    """Get sales summary for period or custom date range"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_date and end_date:
        # Custom date range
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
        
    elif period == "weekly":
        # Current week (Sunday to today)
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.total), 0),
                COALESCE(SUM(s.discount), 0),
                COALESCE(SUM(s.profit), 0),
                COALESCE(SUM(si.quantity), 0)
            FROM sales s
            LEFT JOIN sales_items si ON s.id = si.sale_id
            WHERE s.date >= DATE_TRUNC('week', CURRENT_DATE)
            AND s.reversed = 0
        """)
        
    elif period == "monthly":
        # Current month
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
        
    elif period == "yearly":
        # Current year
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
        
    elif period == "all":
        # All time
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
        
    else:  # daily
        # Current day
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
    
    total_sales = result[0] if result[0] else 0
    total_discount = result[1] if result[1] else 0
    total_profit = result[2] if result[2] else 0
    items_sold = result[3] if result[3] else 0
    
    return (items_sold, total_sales, total_discount, total_sales, total_profit)


def get_top_products_multi(period="daily", limit=10, start_date=None, end_date=None):
    """Get top selling products for period or custom range"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if start_date and end_date:
        # Custom date range
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
        # Current week
        cursor.execute("""
            SELECT 
                p.name, 
                COALESCE(p.brand, '') as brand, 
                COALESCE(p.category, '') as category, 
                COALESCE(SUM(si.quantity), 0) as qty
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON p.id = si.product_id
            WHERE s.date >= DATE_TRUNC('week', CURRENT_DATE)
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
        # Current month
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
        # Current year
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
        # All time
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
        # Current day
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
        # Custom date range - group by day
        cursor.execute("""
            SELECT 
                DATE(s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date::date BETWEEN %s AND %s
            AND s.reversed = 0
            GROUP BY DATE(s.date)
            ORDER BY label ASC
        """, (start_date, end_date))
        
    elif period == "weekly":
        # Current week - group by day of week
        cursor.execute("""
            SELECT 
                EXTRACT(DOW FROM s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date >= DATE_TRUNC('week', CURRENT_DATE)
            AND s.reversed = 0
            GROUP BY EXTRACT(DOW FROM s.date)
            ORDER BY label ASC
        """)
        
    elif period == "monthly":
        # Current month - group by day of month
        cursor.execute("""
            SELECT 
                EXTRACT(DAY FROM s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM s.date) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND s.reversed = 0
            GROUP BY EXTRACT(DAY FROM s.date)
            ORDER BY label ASC
        """)
        
    elif period == "yearly":
        # Current year - group by month
        cursor.execute("""
            SELECT 
                EXTRACT(MONTH FROM s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE EXTRACT(YEAR FROM s.date) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND s.reversed = 0
            GROUP BY EXTRACT(MONTH FROM s.date)
            ORDER BY label ASC
        """)
        
    elif period == "all":
        # All time - group by month, last 24 months
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
        # Current day - group by hour
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM s.date) as label,
                COALESCE(SUM(s.total), 0) as sales_total,
                COALESCE(SUM(s.profit), 0) as profit_total
            FROM sales s
            WHERE s.date::date = CURRENT_DATE
            AND s.reversed = 0
            GROUP BY EXTRACT(HOUR FROM s.date)
            ORDER BY label ASC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert labels to readable format
    result = []
    for row in rows:
        label = row[0]
        if period == "weekly":
            # Convert day of week number to name
            days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            label = days[int(label)] if 0 <= int(label) <= 6 else str(label)
        elif period == "monthly":
            label = f"Day {int(label)}"
        elif period == "yearly":
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            label = months[int(label) - 1] if 1 <= int(label) <= 12 else str(label)
        elif period == "all":
            if hasattr(label, 'strftime'):
                label = label.strftime('%b %Y')
            else:
                label = str(label)
        elif period == "daily":
            label = f"{int(label)}:00"
            
        result.append({
            'label': str(label),
            'sales': float(row[1]),
            'profit': float(row[2])
        })
    
    return result