import os
from database.db import get_connection, get_db_connection, get_param_style
from datetime import datetime
from functools import wraps
import time

# ---------------------------
# DECORATOR FOR TIMEOUT HANDLING
# ---------------------------
def handle_timeout(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            print(f"{func.__name__} completed in {elapsed:.2f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"{func.__name__} failed after {elapsed:.2f} seconds: {str(e)}")
            raise
    return wrapper

# ---------------------------
# GET PRODUCTS FOR SALE
# ---------------------------
def get_products_for_sale():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.name, p.brand, p.selling_price, p.stock
            FROM products p
            WHERE p.stock > 0
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
            ORDER BY p.name ASC
            LIMIT 1000
        """)
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "name": r[1],
                "brand": r[2] or "",
                "selling_price": float(r[3] or 0),
                "stock": int(r[4] or 0),
            }
            for r in rows
        ]
    finally:
        from database.db import return_connection
        return_connection(conn)

# ---------------------------
# GET BATCHES FOR PRODUCT (FIFO order)
# ---------------------------
def get_batches_for_product(product_id, limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, quantity, remaining_quantity, cost_price, selling_price, discount, date
            FROM purchase_batches
            WHERE product_id = %s AND remaining_quantity > 0
            ORDER BY date ASC
            LIMIT %s
        """, (product_id, limit))
        rows = cursor.fetchall()
        return [
            {
                "batch_id": r[0],
                "quantity": int(r[1] or 0),
                "remaining_quantity": int(r[2] or 0),
                "cost_price": float(r[3] or 0),
                "selling_price": float(r[4] or 0),
                "discount": float(r[5] or 0),
                "date": r[6],
            }
            for r in rows
        ]
    finally:
        from database.db import return_connection
        return_connection(conn)

# ---------------------------
# GET SINGLE BATCH BY ID
# ---------------------------
def get_batch_by_id(batch_id):
    """Get a single batch by its ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, product_id, remaining_quantity, cost_price, selling_price
            FROM purchase_batches
            WHERE id = %s
        """, (batch_id,))
        row = cursor.fetchone()
        if row:
            return {
                "batch_id": row[0],
                "product_id": row[1],
                "remaining_quantity": int(row[2] or 0),
                "cost_price": float(row[3] or 0),
                "selling_price": float(row[4] or 0),
            }
        return None
    finally:
        from database.db import return_connection
        return_connection(conn)

# ---------------------------
# GET MULTIPLE BATCHES IN SINGLE QUERY
# ---------------------------
def get_batches_by_ids(batch_ids):
    """Fetch multiple batches in one query for better performance"""
    if not batch_ids:
        return {}
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ','.join(['%s'] * len(batch_ids))
        cursor.execute(f"""
            SELECT id, product_id, remaining_quantity, cost_price, selling_price
            FROM purchase_batches
            WHERE id IN ({placeholders})
        """, batch_ids)
        
        rows = cursor.fetchall()
        return {
            r[0]: {
                "batch_id": r[0],
                "product_id": r[1],
                "remaining_quantity": int(r[2] or 0),
                "cost_price": float(r[3] or 0),
                "selling_price": float(r[4] or 0),
            }
            for r in rows
        }
    finally:
        from database.db import return_connection
        return_connection(conn)

# ---------------------------
# UPDATE PRODUCT STOCK
# ---------------------------
def update_product_stock(cursor, product_id):
    cursor.execute("""
        SELECT COALESCE(SUM(remaining_quantity), 0)
        FROM purchase_batches
        WHERE product_id = %s
    """, (product_id,))
    new_stock = cursor.fetchone()[0]
    cursor.execute("""
        UPDATE products SET stock = %s WHERE id = %s
    """, (int(new_stock), product_id))

# ---------------------------
# BULK UPDATE PRODUCT STOCKS
# ---------------------------
def bulk_update_product_stocks(cursor, product_ids):
    """Update multiple product stocks in bulk"""
    for product_id in product_ids:
        update_product_stock(cursor, product_id)

# ---------------------------
# MAIN SALE CREATION FUNCTION (WITH PAYMENT METHOD)
# ---------------------------
@handle_timeout
def create_multi_sale(cart_items, sale_datetime=None, selected_batches=None, payment_method='cash', cheque_number=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Format sale date
        if sale_datetime:
            try:
                sale_date_obj = datetime.strptime(sale_datetime, "%Y-%m-%d %H:%M:%S")
                sale_date_str = sale_date_obj.strftime("%Y-%m-%d %H:%M:%S")
            except:
                sale_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            sale_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 2. Insert sale record with payment fields
        cursor.execute("""
            INSERT INTO sales (subtotal, discount, total, profit, date, payment_method, cheque_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (0, 0, 0, 0, sale_date_str, payment_method, cheque_number))
        sale_id = cursor.fetchone()[0]
        
        # Prepare data structures
        all_sales_items = []
        batch_updates = []
        total_subtotal = 0
        total_discount = 0
        total_gross_profit = 0
        receipt_data = []
        affected_products = set()
        
        # 3. Pre-fetch all needed batches if using selected_batches
        batches_cache = {}
        if selected_batches:
            batch_ids = [sb["batch_id"] for sb in selected_batches]
            batches_cache = get_batches_by_ids(batch_ids)
        
        # 4. Process each cart item
        for item in cart_items:
            product = item["product"]
            product_id = product["id"]
            quantity = int(item["qty"])
            discount = float(item.get("discount", 0))
            selling_price = float(product.get("selling_price", 0))
            
            subtotal = 0
            profit = 0
            batches_used = []
            
            if selected_batches:
                # Use selected batches (pre-fetched)
                product_batches = []
                for sb in selected_batches:
                    batch = batches_cache.get(sb["batch_id"])
                    if batch and batch["product_id"] == product_id:
                        # Validate stock
                        if batch["remaining_quantity"] < sb["qty"]:
                            raise ValueError(f"Batch {sb['batch_id']} has only {batch['remaining_quantity']} left")
                        product_batches.append({
                            "batch_id": sb["batch_id"],
                            "qty": sb["qty"],
                            "cost_price": batch["cost_price"],
                            "selling_price": batch.get("selling_price", selling_price)
                        })
                
                # Verify quantity
                total_assigned = sum(b["qty"] for b in product_batches)
                if total_assigned != quantity:
                    raise ValueError(f"Quantity mismatch for {product['name']}")
                
                for b in product_batches:
                    batch_total = b["selling_price"] * b["qty"]
                    batch_profit = (b["selling_price"] - b["cost_price"]) * b["qty"]
                    
                    subtotal += batch_total
                    profit += batch_profit
                    
                    # Queue updates
                    batch_updates.append((b["qty"], b["batch_id"]))
                    all_sales_items.append((
                        sale_id, product_id, b["batch_id"], b["qty"],
                        b["cost_price"], b["selling_price"], batch_profit
                    ))
                    batches_used.append({"batch_id": b["batch_id"], "qty": b["qty"]})
                    affected_products.add(product_id)
            
            else:
                # FIFO: Get batches in single query
                cursor.execute("""
                    SELECT id, remaining_quantity, cost_price, selling_price
                    FROM purchase_batches
                    WHERE product_id = %s AND remaining_quantity > 0
                    ORDER BY date ASC
                    LIMIT 100
                """, (product_id,))
                batches = cursor.fetchall()
                
                remaining_qty = quantity
                
                for batch in batches:
                    if remaining_qty <= 0:
                        break
                    
                    batch_id = batch[0]
                    batch_remaining = int(batch[1] or 0)
                    batch_cost = float(batch[2] or 0)
                    batch_selling = float(batch[3] or selling_price)
                    
                    sell_qty = min(batch_remaining, remaining_qty)
                    batch_total = batch_selling * sell_qty
                    batch_profit = (batch_selling - batch_cost) * sell_qty
                    
                    subtotal += batch_total
                    profit += batch_profit
                    remaining_qty -= sell_qty
                    
                    batch_updates.append((sell_qty, batch_id))
                    all_sales_items.append((
                        sale_id, product_id, batch_id, sell_qty,
                        batch_cost, batch_selling, batch_profit
                    ))
                    batches_used.append({"batch_id": batch_id, "qty": sell_qty})
                    affected_products.add(product_id)
                
                if remaining_qty > 0:
                    raise ValueError(f"Insufficient stock for {product['name']}. Needed {quantity}, available {quantity - remaining_qty}")
            
            final_total = max(subtotal - discount, 0)
            total_subtotal += subtotal
            total_discount += discount
            total_gross_profit += profit
            
            receipt_data.append({
                "name": product["name"],
                "qty": quantity,
                "batches": batches_used,
                "subtotal": subtotal,
                "discount": discount,
                "total": final_total
            })
        
        # 5. Execute batch updates
        if batch_updates:
            cursor.executemany("""
                UPDATE purchase_batches 
                SET remaining_quantity = remaining_quantity - %s 
                WHERE id = %s
            """, batch_updates)
        
        # 6. Insert all sales items
        if all_sales_items:
            cursor.executemany("""
                INSERT INTO sales_items 
                (sale_id, product_id, batch_id, quantity, cost_price, selling_price, profit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, all_sales_items)
        
        # 7. Update product stocks
        for product_id in affected_products:
            update_product_stock(cursor, product_id)
        
        # 8. Update sale totals
        net_profit = total_gross_profit - total_discount
        grand_total = max(total_subtotal - total_discount, 0)
        
        cursor.execute("""
            UPDATE sales 
            SET subtotal = %s, discount = %s, total = %s, profit = %s 
            WHERE id = %s
        """, (total_subtotal, total_discount, grand_total, net_profit, sale_id))
        
        # IMPORTANT: Commit the transaction BEFORE returning connection
        conn.commit()
        
        # Prepare the result with payment info
        result = {
            "sale_id": sale_id,
            "items": receipt_data,
            "subtotal": total_subtotal,
            "discount": total_discount,
            "total": grand_total,
            "profit": net_profit,
            "date": sale_date_str,
            "payment_method": payment_method,
            "cheque_number": cheque_number
        }
        
        # Return connection to pool AFTER preparing result
        from database.db import return_connection
        return_connection(conn)
        
        return result
        
    except Exception as e:
        conn.rollback()
        from database.db import return_connection
        return_connection(conn)
        print(f"Sale creation failed: {str(e)}")
        raise e

# ---------------------------
# GET SALE DETAILS (WITH PAYMENT INFO)
# ---------------------------
def get_sale_details(sale_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get sale header with payment info
        cursor.execute("""
            SELECT id, subtotal, discount, total, profit, date, payment_method, cheque_number
            FROM sales
            WHERE id = %s
        """, (sale_id,))
        sale = cursor.fetchone()
        
        if not sale:
            return None
        
        # Get sale items with product names
        cursor.execute("""
            SELECT 
                si.product_id,
                p.name as product_name,
                si.quantity,
                si.selling_price,
                si.cost_price,
                si.profit,
                si.batch_id
            FROM sales_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = %s
        """, (sale_id,))
        
        items = cursor.fetchall()
        
        result = {
            "id": sale[0],
            "subtotal": float(sale[1] or 0),
            "discount": float(sale[2] or 0),
            "total": float(sale[3] or 0),
            "profit": float(sale[4] or 0),
            "date": sale[5],
            "payment_method": sale[6] if len(sale) > 6 else 'unknown',
            "cheque_number": sale[7] if len(sale) > 7 else None,
            "items": [
                {
                    "product_id": item[0],
                    "product_name": item[1],
                    "quantity": int(item[2] or 0),
                    "selling_price": float(item[3] or 0),
                    "cost_price": float(item[4] or 0),
                    "profit": float(item[5] or 0),
                    "batch_id": item[6]
                }
                for item in items
            ]
        }
        
        from database.db import return_connection
        return_connection(conn)
        
        return result
        
    except Exception as e:
        from database.db import return_connection
        return_connection(conn)
        print(f"Get sale details failed: {str(e)}")
        raise e

# ---------------------------
# GET TODAY'S SALES (WITH PAYMENT INFO)
# ---------------------------
def get_todays_sales():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, subtotal, discount, total, profit, date, payment_method, cheque_number
            FROM sales
            WHERE DATE(date) = CURRENT_DATE
            ORDER BY date DESC
        """)
        rows = cursor.fetchall()
        
        result = [
            {
                "id": r[0],
                "subtotal": float(r[1] or 0),
                "discount": float(r[2] or 0),
                "total": float(r[3] or 0),
                "profit": float(r[4] or 0),
                "date": r[5],
                "payment_method": r[6] if len(r) > 6 else 'unknown',
                "cheque_number": r[7] if len(r) > 7 else None
            }
            for r in rows
        ]
        
        from database.db import return_connection
        return_connection(conn)
        
        return result
        
    except Exception as e:
        from database.db import return_connection
        return_connection(conn)
        print(f"Get today's sales failed: {str(e)}")
        raise e

# ---------------------------
# GET SALES BY DATE RANGE (WITH PAYMENT INFO)
# ---------------------------
def get_sales_by_date_range(start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, subtotal, discount, total, profit, date, payment_method, cheque_number
            FROM sales
            WHERE DATE(date) BETWEEN %s AND %s
            ORDER BY date DESC
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        
        result = [
            {
                "id": r[0],
                "subtotal": float(r[1] or 0),
                "discount": float(r[2] or 0),
                "total": float(r[3] or 0),
                "profit": float(r[4] or 0),
                "date": r[5],
                "payment_method": r[6] if len(r) > 6 else 'unknown',
                "cheque_number": r[7] if len(r) > 7 else None
            }
            for r in rows
        ]
        
        from database.db import return_connection
        return_connection(conn)
        
        return result
        
    except Exception as e:
        from database.db import return_connection
        return_connection(conn)
        print(f"Get sales by date range failed: {str(e)}")
        raise e