from database.db import get_connection
from datetime import datetime

# ---------------- RECALCULATE STOCK ----------------
def recalc_stock(cursor, product_id):
    cursor.execute("""
        SELECT COALESCE(SUM(remaining_quantity), 0)
        FROM purchase_batches
        WHERE product_id = %s AND remaining_quantity > 0
    """, (product_id,))
    stock = cursor.fetchone()[0] or 0
    cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (stock, product_id))
    return stock

# ---------------- DELETE SINGLE BATCH (KEEPS HISTORY) ----------------
def delete_batch(batch_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, quantity, remaining_quantity, cost_price, selling_price, discount FROM purchase_batches WHERE id = %s", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        return False
    product_id, batch_qty, batch_rem, cost_price, selling_price, discount = batch

    cursor.execute("SELECT name, brand, category FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if product:
        cursor.execute("""
            INSERT INTO deleted_products
            (name, brand, cost_price, selling_price, stock, category, discount, action, source, batch_id, batch_quantity, batch_remaining, product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (product[0], product[1], cost_price, selling_price, batch_rem, product[2], discount, "BATCH DELETED", "batch", batch_id, batch_qty, batch_rem, product_id))

    cursor.execute("DELETE FROM purchase_batches WHERE id = %s", (batch_id,))
    new_stock = recalc_stock(cursor, product_id)
    conn.commit()
    conn.close()
    return True

# ---------------- DELETE SINGLE BATCH (CLEAN EVERYTHING) ----------------
def delete_batch_clean_all(batch_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, quantity, remaining_quantity, cost_price, selling_price, discount FROM purchase_batches WHERE id = %s", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        return False
    product_id, batch_qty, batch_rem, cost_price, selling_price, discount = batch

    cursor.execute("SELECT name, brand, category FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if product:
        cursor.execute("""
            INSERT INTO deleted_products
            (name, brand, cost_price, selling_price, stock, category, discount, action, source, batch_id, batch_quantity, batch_remaining, product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (product[0], product[1], cost_price, selling_price, batch_rem, product[2], discount, "PERMANENTLY DELETED", "batch", batch_id, batch_qty, batch_rem, product_id))

    cursor.execute("DELETE FROM sales_items WHERE batch_id = %s", (batch_id,))
    cursor.execute("DELETE FROM purchase_batches WHERE id = %s", (batch_id,))
    new_stock = recalc_stock(cursor, product_id)
    conn.commit()
    conn.close()
    return True

# ---------------- DELETE FULL PRODUCT (KEEPS HISTORY) ----------------
def delete_product_keep_history(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, brand, cost_price, selling_price, stock, category, discount FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if product:
        cursor.execute("SELECT id, quantity, remaining_quantity, cost_price, selling_price, discount FROM purchase_batches WHERE product_id = %s", (product_id,))
        batches = cursor.fetchall()
        for batch in batches:
            batch_id, batch_qty, batch_rem, cost_price, selling_price, discount = batch
            cursor.execute("""
                INSERT INTO deleted_products
                (name, brand, cost_price, selling_price, stock, category, discount, action, source, batch_id, batch_quantity, batch_remaining, product_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (product[0], product[1], cost_price, selling_price, batch_rem, product[2], discount, "BATCH DELETED", "product_delete", batch_id, batch_qty, batch_rem, product_id))
        cursor.execute("""
            INSERT INTO deleted_products 
            (name, brand, cost_price, selling_price, stock, category, discount, action, source, product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (*product, "PRODUCT DELETED", "product", product_id))
    cursor.execute("DELETE FROM purchase_batches WHERE product_id = %s", (product_id,))
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()

# ---------------- DELETE PRODUCT (CLEAN EVERYTHING) ----------------
def delete_product_clean_all(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, brand, cost_price, selling_price, stock, category, discount FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if product:
        cursor.execute("""
            INSERT INTO deleted_products 
            (name, brand, cost_price, selling_price, stock, category, discount, action, source, product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (*product, "PERMANENTLY DELETED", "product", product_id))
    cursor.execute("DELETE FROM purchase_batches WHERE product_id = %s", (product_id,))
    cursor.execute("DELETE FROM sales_items WHERE product_id = %s", (product_id,))
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()

# ---------------- UPDATE BATCH ----------------
def update_product(batch_id, name, brand, category, quantity, cost_price, discount, selling_price):
    quantity = int(quantity)
    cost_price = float(cost_price)
    discount = float(discount or 0)
    selling_price = float(selling_price)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pb.product_id, pb.quantity, pb.remaining_quantity, pb.cost_price, pb.selling_price, pb.discount,
                   p.name, p.brand, p.category
            FROM purchase_batches pb
            JOIN products p ON p.id = pb.product_id
            WHERE pb.id = %s
        """, (batch_id,))
        old = cursor.fetchone()
        if not old:
            raise ValueError("Batch not found")
        (product_id, old_qty, old_rem, old_cost, old_selling, old_disc,
         old_name, old_brand, old_category) = old
        cursor.execute("""
            INSERT INTO deleted_products
            (name, brand, cost_price, selling_price, stock, category, discount, action, source, batch_id, batch_quantity, batch_remaining, product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (old_name, old_brand, old_cost, old_selling, old_rem, old_category, old_disc, "UPDATED", "product", batch_id, old_qty, old_rem, product_id))
        cursor.execute("""
            UPDATE purchase_batches
            SET quantity = %s, remaining_quantity = %s, cost_price = %s, selling_price = %s, discount = %s, date = %s, action = %s
            WHERE id = %s
        """, (quantity, quantity, cost_price, selling_price, discount, datetime.now(), "updated", batch_id))
        cursor.execute("UPDATE products SET category = %s WHERE id = %s", (category, product_id))
        recalc_stock(cursor, product_id)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ---------------- GET ALL PRODUCTS (ONLY ACTIVE PRODUCTS - EXCLUDES DELETED) ----------------
def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, brand, cost_price, selling_price, stock, category, discount
        FROM products
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted_products dp 
            WHERE dp.product_id = products.id 
            AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
            AND dp.source = 'product'
        )
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    products = []
    for r in rows:
        products.append({
            "product_id": r[0],
            "name": r[1] or "-",
            "brand": r[2] or "-",
            "cost_price": r[3] or 0.0,
            "selling_price": r[4] or 0.0,
            "stock": r[5] or 0,
            "category": r[6] or "-",
            "discount": r[7] or 0.0
        })
    return products

# ---------------- GET DELETED PRODUCTS ----------------
def get_deleted_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, brand, cost_price, selling_price, stock, category, discount, action, deleted_at,
               batch_id, batch_quantity, batch_remaining, product_id, source
        FROM deleted_products
        ORDER BY deleted_at DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return data

# ---------------- RESTORE ARCHIVED ----------------
def restore_archive(archive_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deleted_products WHERE id = %s", (archive_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Archive record not found")
        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))
        name = record['name']
        brand = record['brand']
        category = record['category']
        cost_price = record['cost_price']
        selling_price = record['selling_price']
        stock = record['stock']
        discount = record['discount']
        action = record['action']
        source = record.get('source', 'product')
        batch_id = record.get('batch_id')
        batch_qty = record.get('batch_quantity')
        batch_rem = record.get('batch_remaining')
        product_id = record.get('product_id')
        deleted_action = record.get('action')
        if deleted_action == "PERMANENTLY DELETED":
            raise ValueError("This item was permanently deleted and cannot be restored!")
        # Restore logic
        if source == 'batch' and batch_id:
            cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
            prod = cursor.fetchone()
            if not prod:
                cursor.execute("""
                    INSERT INTO products (name, brand, cost_price, selling_price, stock, category, discount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, brand, cost_price, selling_price, 0, category, discount))
                product_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO purchase_batches
                (id, product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (batch_id, product_id, batch_qty, batch_rem, cost_price, selling_price, discount, datetime.now(), "restored"))
            recalc_stock(cursor, product_id)
        elif source == 'product_delete' and product_id:
            cursor.execute("SELECT id FROM products WHERE name = %s AND brand = %s", (name, brand))
            prod = cursor.fetchone()
            if prod:
                product_id = prod[0]
            else:
                cursor.execute("""
                    INSERT INTO products (id, name, brand, cost_price, selling_price, stock, category, discount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (product_id, name, brand, cost_price, selling_price, 0, category, discount))
            cursor.execute("""
                SELECT batch_id, batch_quantity, batch_remaining, cost_price, selling_price, discount
                FROM deleted_products
                WHERE product_id = %s AND source = 'product_delete' AND action = 'BATCH DELETED'
            """, (product_id,))
            batches = cursor.fetchall()
            for batch in batches:
                old_batch_id, old_qty, old_rem, old_cost, old_selling, old_disc = batch
                cursor.execute("""
                    INSERT INTO purchase_batches
                    (id, product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (old_batch_id, product_id, old_qty, old_rem, old_cost, old_selling, old_disc, datetime.now(), "restored"))
            recalc_stock(cursor, product_id)
        elif action == "UPDATED" and batch_id:
            cursor.execute("SELECT id FROM purchase_batches WHERE id = %s", (batch_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE purchase_batches
                    SET quantity = %s, remaining_quantity = %s, cost_price = %s, selling_price = %s, discount = %s, date = %s, action = %s
                    WHERE id = %s
                """, (batch_qty, batch_rem, cost_price, selling_price, discount, datetime.now(), "restored", batch_id))
                if product_id:
                    recalc_stock(cursor, product_id)
            else:
                if not product_id:
                    cursor.execute("SELECT id FROM products WHERE name = %s AND brand = %s", (name, brand))
                    prod = cursor.fetchone()
                    if prod:
                        product_id = prod[0]
                    else:
                        cursor.execute("""
                            INSERT INTO products (name, brand, cost_price, selling_price, stock, category, discount)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (name, brand, cost_price, selling_price, 0, category, discount))
                        product_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO purchase_batches
                    (id, product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (batch_id, product_id, batch_qty, batch_rem, cost_price, selling_price, discount, datetime.now(), "restored"))
                recalc_stock(cursor, product_id)
        elif source == 'product' and deleted_action == "DELETED":
            cursor.execute("SELECT id FROM products WHERE name = %s AND brand = %s", (name, brand))
            prod = cursor.fetchone()
            if prod:
                product_id = prod[0]
                cursor.execute("""
                    INSERT INTO purchase_batches
                    (product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (product_id, stock, stock, cost_price, selling_price, discount, datetime.now(), "restored"))
                recalc_stock(cursor, product_id)
            else:
                cursor.execute("""
                    INSERT INTO products
                    (name, brand, cost_price, selling_price, stock, category, discount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, brand, cost_price, selling_price, 0, category, discount))
                product_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO purchase_batches
                    (product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (product_id, stock, stock, cost_price, selling_price, discount, datetime.now(), "restored"))
                recalc_stock(cursor, product_id)
        if source == 'product_delete' and product_id:
            cursor.execute("DELETE FROM deleted_products WHERE product_id = %s AND source = 'product_delete'", (product_id,))
        else:
            cursor.execute("DELETE FROM deleted_products WHERE id = %s", (archive_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()