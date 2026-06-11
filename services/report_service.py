import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

from database.db import get_connection

REPORT_FOLDER = "reports"
os.makedirs(REPORT_FOLDER, exist_ok=True)

def generate_sales_report():
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch today's sales with batch info and payment method
    cursor.execute("""
        SELECT 
            products.name,
            products.brand,
            sales_items.quantity,
            (sales_items.quantity * sales_items.selling_price) AS total,
            sales_items.profit,
            purchase_batches.id AS batch_id,
            purchase_batches.cost_price,
            sales.date,
            sales.payment_method,
            sales.cheque_number
        FROM sales
        JOIN sales_items ON sales.id = sales_items.sale_id
        JOIN products ON products.id = sales_items.product_id
        JOIN purchase_batches ON purchase_batches.id = sales_items.batch_id
        WHERE DATE(sales.date) = DATE('now','localtime')
        AND sales.reversed = 0
        ORDER BY sales.date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Calculate totals
    total_qty = sum(r[2] for r in rows)
    total_sales = sum(r[3] for r in rows)
    total_profit = sum(r[4] for r in rows)
    
    # Calculate payment method totals
    payment_totals = {}
    for r in rows:
        payment_method = r[8] if len(r) > 8 else 'cash'
        payment_totals[payment_method] = payment_totals.get(payment_method, 0) + r[3]

    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(REPORT_FOLDER, f"sales_report_{today_str}.pdf")

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("SEEK FOR GOD'S KINGDOM ENTERPRISE", styles['Title']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("DEALERS IN HOME APPLIANCES, FRIDGES, TVs, BLENDERS AND MORE", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Daily Sales Report - {today_str}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # Summary Section
    elements.append(Paragraph("SALES SUMMARY", styles['Heading3']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"Total Items Sold: {total_qty}", styles['Normal']))
    elements.append(Paragraph(f"Total Sales: ₵{total_sales:.2f}", styles['Normal']))
    elements.append(Paragraph(f"Total Profit: ₵{total_profit:.2f}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Payment Method Breakdown
    elements.append(Paragraph("PAYMENT BREAKDOWN", styles['Heading3']))
    elements.append(Spacer(1, 5))
    for method, amount in payment_totals.items():
        if method == 'cash':
            elements.append(Paragraph(f"💵 Cash: ₵{amount:.2f}", styles['Normal']))
        elif method == 'momo':
            elements.append(Paragraph(f"📱 Mobile Money: ₵{amount:.2f}", styles['Normal']))
        elif method == 'cheque':
            elements.append(Paragraph(f"📝 Cheque: ₵{amount:.2f}", styles['Normal']))
        else:
            elements.append(Paragraph(f"❓ {method.title()}: ₵{amount:.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table data with payment method
    table_data = [
        ["Product", "Brand", "Batch", "Qty", "Cost (₵)", "Total (₵)", "Profit (₵)", "Payment", "Time"]
    ]

    for r in rows:
        time_str = str(r[7]).split(" ")[1] if " " in str(r[7]) else str(r[7])
        payment_method = r[8] if len(r) > 8 else 'cash'
        
        # Format payment method display
        if payment_method == 'cash':
            payment_display = "Cash"
        elif payment_method == 'momo':
            payment_display = "MoMo"
        elif payment_method == 'cheque':
            cheque_num = r[9] if len(r) > 9 else ''
            payment_display = f"Cheque #{cheque_num[:10]}" if cheque_num else "Cheque"
        else:
            payment_display = payment_method.title()
        
        table_data.append([
            r[0][:25] + "..." if len(r[0]) > 25 else r[0],  # Truncate long names
            r[1] or "-",
            f"#{r[5]}",
            r[2],
            f"{r[6]:.2f}",
            f"{r[3]:.2f}",
            f"{r[4]:.2f}",
            payment_display,
            time_str
        ])

    # Add totals row
    table_data.append([
        "TOTAL", "", "", total_qty, "", f"{total_sales:.2f}", f"{total_profit:.2f}", "", ""
    ])

    # Column widths
    col_widths = [5*cm, 3.5*cm, 2*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (3,1), (6,-2), "CENTER"),
        ("ALIGN", (3,-1), (6,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Paragraph("Powered by HUMMINGBIRD DIGITAL SOLUTIONS", styles['Normal']))

    doc = SimpleDocTemplate(filename, pagesize=A4)
    doc.build(elements)

    return filename


def generate_sales_report_by_date_range(start_date, end_date):
    """
    Generate sales report for a date range with payment information
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            products.name,
            products.brand,
            sales_items.quantity,
            (sales_items.quantity * sales_items.selling_price) AS total,
            sales_items.profit,
            purchase_batches.id AS batch_id,
            purchase_batches.cost_price,
            sales.date,
            sales.payment_method,
            sales.cheque_number,
            sales.id as sale_id
        FROM sales
        JOIN sales_items ON sales.id = sales_items.sale_id
        JOIN products ON products.id = sales_items.product_id
        JOIN purchase_batches ON purchase_batches.id = sales_items.batch_id
        WHERE DATE(sales.date) BETWEEN %s AND %s
        AND sales.reversed = 0
        ORDER BY sales.date DESC
    """, (start_date, end_date))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Calculate totals
    total_qty = sum(r[2] for r in rows)
    total_sales = sum(r[3] for r in rows)
    total_profit = sum(r[4] for r in rows)
    
    # Calculate payment method totals
    payment_totals = {}
    unique_sales = set()
    for r in rows:
        payment_method = r[8] if len(r) > 8 else 'cash'
        sale_id = r[10] if len(r) > 10 else None
        if sale_id not in unique_sales:
            unique_sales.add(sale_id)
            payment_totals[payment_method] = payment_totals.get(payment_method, 0) + r[3]

    start_date_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
    end_date_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)
    filename = os.path.join(REPORT_FOLDER, f"sales_report_{start_date_str}_to_{end_date_str}.pdf")

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("SEEK FOR GOD'S KINGDOM ENTERPRISE", styles['Title']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("DEALERS IN HOME APPLIANCES, FRIDGES, TVs, BLENDERS AND MORE", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Sales Report - {start_date_str} to {end_date_str}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # Summary Section
    elements.append(Paragraph("SALES SUMMARY", styles['Heading3']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"Total Items Sold: {total_qty}", styles['Normal']))
    elements.append(Paragraph(f"Total Sales: ₵{total_sales:.2f}", styles['Normal']))
    elements.append(Paragraph(f"Total Profit: ₵{total_profit:.2f}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Payment Method Breakdown
    elements.append(Paragraph("PAYMENT BREAKDOWN", styles['Heading3']))
    elements.append(Spacer(1, 5))
    for method, amount in payment_totals.items():
        if method == 'cash':
            elements.append(Paragraph(f"💵 Cash: ₵{amount:.2f}", styles['Normal']))
        elif method == 'momo':
            elements.append(Paragraph(f"📱 Mobile Money: ₵{amount:.2f}", styles['Normal']))
        elif method == 'cheque':
            elements.append(Paragraph(f"📝 Cheque: ₵{amount:.2f}", styles['Normal']))
        else:
            elements.append(Paragraph(f"❓ {method.title()}: ₵{amount:.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table data
    table_data = [
        ["Date", "Product", "Brand", "Batch", "Qty", "Total (₵)", "Profit (₵)", "Payment"]
    ]

    for r in rows:
        date_str = r[7].strftime("%Y-%m-%d %H:%M") if hasattr(r[7], 'strftime') else str(r[7])[:16]
        payment_method = r[8] if len(r) > 8 else 'cash'
        
        if payment_method == 'cash':
            payment_display = "Cash"
        elif payment_method == 'momo':
            payment_display = "MoMo"
        elif payment_method == 'cheque':
            cheque_num = r[9] if len(r) > 9 else ''
            payment_display = f"Cheque #{cheque_num[:10]}" if cheque_num else "Cheque"
        else:
            payment_display = payment_method.title()
        
        table_data.append([
            date_str,
            r[0][:20] + "..." if len(r[0]) > 20 else r[0],
            r[1] or "-",
            f"#{r[5]}",
            r[2],
            f"{r[3]:.2f}",
            f"{r[4]:.2f}",
            payment_display
        ])

    # Add totals row
    table_data.append([
        "TOTAL", "", "", "", total_qty, f"{total_sales:.2f}", f"{total_profit:.2f}", ""
    ])

    col_widths = [4*cm, 5*cm, 3.5*cm, 2*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (4,1), (6,-2), "CENTER"),
        ("ALIGN", (4,-1), (6,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Paragraph("Powered by HUMMINGBIRD DIGITAL SOLUTIONS", styles['Normal']))

    doc = SimpleDocTemplate(filename, pagesize=A4)
    doc.build(elements)

    return filename