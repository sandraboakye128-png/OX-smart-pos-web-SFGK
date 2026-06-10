import os
from database.db import get_connection
from datetime import datetime

# ---------------------------
# GET PRODUCTS FOR SALE
# ---------------------------
def get_products_for_sale():
    conn = get_connection()
    cursor = conn.cursor()
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
    """)
    rows = cursor.fetchall()
    conn.close()
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


# ---------------------------
# GET BATCHES FOR PRODUCT (FIFO order)
# ---------------------------
def get_batches_for_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, quantity, remaining_quantity, cost_price, selling_price, discount, date
        FROM purchase_batches
        WHERE product_id = %s AND remaining_quantity > 0
        ORDER BY date ASC
    """, (product_id,))
    rows = cursor.fetchall()
    conn.close()
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


# ---------------------------
# GET SINGLE BATCH BY ID
# ---------------------------
def get_batch_by_id(batch_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, product_id, remaining_quantity, cost_price, selling_price
        FROM purchase_batches
        WHERE id = %s
    """, (batch_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "batch_id": row[0],
            "product_id": row[1],
            "remaining_quantity": int(row[2] or 0),
            "cost_price": float(row[3] or 0),
            "selling_price": float(row[4] or 0),
        }
    return None


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
# CREATE SALE WITH CUSTOM DATE/TIME AND SELECTED BATCHES
# ---------------------------
def create_multi_sale(cart_items, sale_datetime=None, selected_batches=None):
    conn = get_connection()
    cursor = conn.cursor()

    total_subtotal = 0
    total_discount = 0
    total_profit = 0   # gross profit (sum of item profits)

    if sale_datetime:
        try:
            sale_date_obj = datetime.strptime(sale_datetime, "%Y-%m-%d %H:%M:%S")
            sale_date_str = sale_date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except:
            sale_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        sale_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert sale and get the generated ID (PostgreSQL uses RETURNING)
    cursor.execute("""
        INSERT INTO sales (subtotal, discount, total, profit, date)
        VALUES (0, 0, 0, 0, %s)
        RETURNING id
    """, (sale_date_str,))
    sale_id = cursor.fetchone()[0]

    receipt_data = []

    # ---------- CASE 1: Selected batches provided ----------
    if selected_batches:
        batches_by_product = {}
        for sb in selected_batches:
            batch = get_batch_by_id(sb["batch_id"])
            if not batch:
                raise ValueError(f"Batch {sb['batch_id']} not found")
            if batch["remaining_quantity"] < sb["qty"]:
                raise ValueError(f"Batch {sb['batch_id']} has only {batch['remaining_quantity']} left, requested {sb['qty']}")
            prod_id = batch["product_id"]
            if prod_id not in batches_by_product:
                batches_by_product[prod_id] = []
            batches_by_product[prod_id].append({"batch": batch, "qty": sb["qty"]})

        for item in cart_items:
            product = item["product"]
            product_id = product["id"]
            discount = float(item.get("discount", 0))
            expected_qty = int(item["qty"])

            prod_batches = batches_by_product.get(product_id, [])
            total_assigned = sum(b["qty"] for b in prod_batches)
            if total_assigned != expected_qty:
                raise ValueError(f"Quantity mismatch for {product['name']}: expected {expected_qty}, assigned {total_assigned}")

            subtotal = 0
            profit = 0
            batches_used = []
            for b in prod_batches:
                batch = b["batch"]
                sell_qty = b["qty"]
                batch_selling = batch["selling_price"]
                batch_cost = batch["cost_price"]

                batch_total = batch_selling * sell_qty
                batch_profit = (batch_selling - batch_cost) * sell_qty

                subtotal += batch_total
                profit += batch_profit

                cursor.execute("""
                    UPDATE purchase_batches
                    SET remaining_quantity = remaining_quantity - %s
                    WHERE id = %s
                """, (sell_qty, batch["batch_id"]))

                cursor.execute("""
                    INSERT INTO sales_items
                    (sale_id, product_id, batch_id, quantity, cost_price, selling_price, profit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (sale_id, product_id, batch["batch_id"], sell_qty, batch_cost, batch_selling, batch_profit))

                batches_used.append({"batch_id": batch["batch_id"], "qty": sell_qty})

            final_total = max(subtotal - discount, 0)
            total_subtotal += subtotal
            total_discount += discount
            total_profit += profit
            update_product_stock(cursor, product_id)

            receipt_data.append({"name": product["name"], "qty": expected_qty, "batches": batches_used})

    # ---------- CASE 2: FIFO (default) ----------
    else:
        for item in cart_items:
            product = item["product"]
            quantity = int(item["qty"])
            discount = float(item.get("discount", 0))
            product_id = product["id"]
            selling_price = float(product["selling_price"])

            remaining_qty = quantity
            subtotal = 0
            profit = 0
            batches_used = []
            batches = get_batches_for_product(product_id)

            for b in batches:
                if remaining_qty <= 0:
                    break
                sell_qty = min(b["remaining_quantity"], remaining_qty)
                batch_total = selling_price * sell_qty
                batch_profit = (selling_price - b["cost_price"]) * sell_qty
                subtotal += batch_total
                profit += batch_profit
                remaining_qty -= sell_qty

                cursor.execute("""
                    UPDATE purchase_batches
                    SET remaining_quantity = remaining_quantity - %s
                    WHERE id = %s
                """, (sell_qty, b["batch_id"]))

                cursor.execute("""
                    INSERT INTO sales_items
                    (sale_id, product_id, batch_id, quantity, cost_price, selling_price, profit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (sale_id, product_id, b["batch_id"], sell_qty, b["cost_price"], selling_price, batch_profit))

                batches_used.append({"batch_id": b["batch_id"], "qty": sell_qty})

            final_total = max(subtotal - discount, 0)
            total_subtotal += subtotal
            total_discount += discount
            total_profit += profit
            update_product_stock(cursor, product_id)

            receipt_data.append({"name": product["name"], "qty": quantity, "batches": batches_used})

    # ---------- Update sale record with net profit ----------
    net_profit = total_profit - total_discount
    grand_total = max(total_subtotal - total_discount, 0)

    cursor.execute("""
        UPDATE sales
        SET subtotal = %s, discount = %s, total = %s, profit = %s
        WHERE id = %s
    """, (total_subtotal, total_discount, grand_total, net_profit, sale_id))

    conn.commit()
    conn.close()

    return {
        "sale_id": sale_id,
        "items": receipt_data,
        "subtotal": total_subtotal,
        "discount": total_discount,
        "total": grand_total,
        "profit": net_profit,
        "date": sale_date_str
    }