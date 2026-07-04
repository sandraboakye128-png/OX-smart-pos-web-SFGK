#!/usr/bin/env python
# fix_missing_batches.py

from database.db import get_connection
from datetime import datetime

def fix_missing_batches():
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Find products with NO batches at all
        cursor.execute("""
            SELECT p.id, p.name, p.brand, p.stock, p.cost_price, p.selling_price, p.discount
            FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM purchase_batches pb 
                WHERE pb.product_id = p.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                AND dp.source = 'product'
            )
        """)
        
        products = cursor.fetchall()
        print(f"🔍 Found {len(products)} products with NO batches")
        
        if not products:
            print("✅ All products have batches!")
            return
        
        created_count = 0
        for product in products:
            product_id = product[0]
            name = product[1]
            stock = product[3]
            cost_price = float(product[4] or 0)
            selling_price = float(product[5] or 0)
            discount = float(product[6] or 0)
            
            action = 'auto_created' if stock > 0 else 'auto_created_depleted'
            
            cursor.execute("""
                INSERT INTO purchase_batches 
                (product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (product_id, stock, stock, cost_price, selling_price, discount, datetime.now(), action))
            
            created_count += 1
            status = f"Stock: {stock}" if stock > 0 else "DEPLETED"
            print(f"✅ Created batch for {name} ({status})")
        
        conn.commit()
        print(f"\n✅ Successfully created {created_count} batches!")
        
        # Verify
        cursor.execute("""
            SELECT COUNT(*) 
            FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM purchase_batches pb 
                WHERE pb.product_id = p.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action IN ('PERMANENTLY DELETED', 'PRODUCT DELETED')
                AND dp.source = 'product'
            )
        """)
        remaining = cursor.fetchone()[0]
        
        if remaining == 0:
            print("✅ All products now have batches!")
        else:
            print(f"⚠️ {remaining} products still have no batches")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n=== Fix Missing Batches ===\n")
    fix_missing_batches()