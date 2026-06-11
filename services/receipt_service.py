import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

# --------------------------- SHOP INFO ---------------------------
SHOP_NAME = "SEEK FOR GOD'S KINGDOM ENTERPRISE"
COMPLEMENT = "DEALERS IN HOME APPLIANCES, FRIDGES,TVs,BLENDERS AND OTHER MORE"
PHONE = "0541442431"
EMAIL = "HT-0000-3866 ,Zongo Road Near Town Park"

# --------------------------- DEVELOPER INFO ---------------------------
DEV_NAME = "HUMMINGBIRD DIGITAL SOLUTIONS"
DEV_CONTACT = "0533052562 / 0201404188"

RECEIPTS_DIR = "receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)


# ==============================================================
# THERMAL RECEIPT GENERATOR (80mm PROFESSIONAL STYLE)
# ==============================================================
def generate_receipt_multi(cart_items, total):
    """
    Generates a professional thermal-style 80mm receipt.
    cart_items: list of cart items from SalesPage, each containing:
        - product: dict (name, brand, etc.)
        - selected_batches: list of dicts with keys "batch" and "qty"
        - discount: discount applied to this product
        - final: final total for this product (not used directly, we compute per batch)
    total: grand total of the sale
    Returns: (filepath, preview_text)
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")
    receipt_no = now.strftime("%Y%m%d%H%M%S")

    filename = os.path.join(RECEIPTS_DIR, f"receipt_{receipt_no}.pdf")

    # ---------------- THERMAL SIZE ----------------
    width = 80 * mm
    height = 260 * mm
    c = canvas.Canvas(filename, pagesize=(width, height))

    y = height - 8 * mm
    center = width / 2

    def divider(style="solid"):
        nonlocal y
        c.setFont("Helvetica", 8)
        line = "-" * 32 if style == "solid" else "." * 32
        c.drawCentredString(center, y, line)
        y -= 5 * mm

    def space(h=3):
        nonlocal y
        y -= h * mm

    # ---------------- HEADER ----------------
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center, y, SHOP_NAME)
    y -= 5 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(center, y, COMPLEMENT)
    y -= 4 * mm

    c.drawCentredString(center, y, f"Tel: {PHONE}")
    y -= 4 * mm
    c.drawCentredString(center, y, EMAIL)
    y -= 5 * mm

    divider()

    # ---------------- RECEIPT INFO ----------------
    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, y, f"Receipt No: {receipt_no}")
    y -= 4 * mm
    c.drawString(5 * mm, y, f"Date: {date_str}")
    y -= 5 * mm

    divider("dot")

    # ---------------- ITEMS HEADER ----------------
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5 * mm, y, "Item / Batch")
    c.drawRightString(width - 5 * mm, y, "Total")
    y -= 4 * mm

    divider("dot")

    preview_lines = [
        SHOP_NAME,
        COMPLEMENT,
        f"Tel: {PHONE}",
        EMAIL,
        "-" * 32
    ]

    # ---------------- PRODUCTS WITH BATCHES ----------------
    for item in cart_items:
        product = item["product"]
        name = product["name"]
        brand = product.get("brand", "")
        discount = item.get("discount", 0)
        selected_batches = item.get("selected_batches", [])

        # For each batch in this product, print a line
        for sb in selected_batches:
            batch = sb["batch"]
            batch_id = batch.get("batch_id", "?")
            qty = sb["qty"]
            price = batch["selling_price"]   # ← USE BATCH SELLING PRICE
            subtotal = qty * price

            # Product name + batch ID
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5 * mm, y, f"{name} ({brand})" if brand else name)
            y -= 4 * mm

            c.setFont("Helvetica", 7)
            c.drawString(5 * mm, y, f"  Batch: {batch_id} | {qty} x ₵{price:.2f}")
            c.drawRightString(width - 5 * mm, y, f"₵{subtotal:.2f}")
            y -= 4 * mm

            # Add to preview
            preview_lines.append(f"{name} ({brand})" if brand else name)
            preview_lines.append(f"  Batch {batch_id}: {qty} x ₵{price:.2f} = ₵{subtotal:.2f}")

        # Discount line for this product (if any)
        if discount > 0:
            c.setFont("Helvetica", 7)
            c.drawString(5 * mm, y, "Discount")
            c.drawRightString(width - 5 * mm, y, f"-₵{discount:.2f}")
            y -= 4 * mm
            preview_lines.append(f"  Discount: -₵{discount:.2f}")

        divider("dot")

    # ---------------- TOTAL ----------------
    space(2)
    divider()

    c.setFont("Helvetica-Bold", 11)
    c.drawString(5 * mm, y, "TOTAL")
    c.drawRightString(width - 5 * mm, y, f"₵{total:.2f}")
    y -= 6 * mm

    divider()

    # ---------------- FOOTER ----------------
    c.setFont("Helvetica", 8)
    c.drawCentredString(center, y, f"{date_str}")
    y -= 5 * mm

    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(center, y, "Thank you for shopping with us!")
    y -= 4 * mm
    c.drawCentredString(center, y, "We appreciate your business ❤️")
    y -= 4 * mm
    c.drawCentredString(center, y, "Please come again anytime")
    y -= 6 * mm

    divider("dot")

    # ---------------- DEVELOPER FOOTER ----------------
    c.setFont("Helvetica", 7)
    c.drawCentredString(center, y, "Powered by")
    y -= 4 * mm

    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(center, y, DEV_NAME)
    y -= 4 * mm

    c.setFont("Helvetica", 7)
    c.drawCentredString(center, y, DEV_CONTACT)

    c.save()

    # ---------------- PREVIEW TEXT ----------------
    preview_lines.append("-" * 32)
    preview_lines.append(f"TOTAL: ₵{total:.2f}")
    preview_lines.append(date_str)
    preview_lines.append("Thank you for shopping!")
    preview_lines.append("Come again anytime ❤️")
    preview_lines.append("-" * 32)
    preview_lines.append(DEV_NAME)
    preview_lines.append(DEV_CONTACT)

    preview = "\n".join(preview_lines)

    return filename, preview