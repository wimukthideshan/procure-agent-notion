import os
import urllib.request, json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("NOTION_TOKEN")

SUPPLIERS_DB  = os.environ.get("NOTION_SUPPLIERS_DB", "405ec7ef-d080-81ab-97cc-cb77badbf556")
PRODUCTS_DB   = os.environ.get("NOTION_PRODUCTS_DB", "405ec7ef-d080-81bc-996e-c8d853e5f8ed")
STOCK_DB      = os.environ.get("NOTION_STOCK_DB", "405ec7ef-d080-81ce-83c7-e43e5641cb13")
PO_DB         = os.environ.get("NOTION_PURCHASE_ORDERS_DB", "405ec7ef-d080-81df-9b9f-c37e0e70acea")

def notion_request(method, endpoint, data=None):
    url = f'https://api.notion.com/v1/{endpoint}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'Bearer {TOKEN}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    })
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())

def add_supplier(name, contact, channel, lead_days, moq, payment, reliability, notes=''):
    notion_request('POST', 'pages', {
        'parent': {'database_id': SUPPLIERS_DB},
        'properties': {
            'Name':             {'title': [{'text': {'content': name}}]},
            'Contact':          {'rich_text': [{'text': {'content': contact}}]},
            'Contact Channel':  {'select': {'name': channel}},
            'Lead Time (days)': {'number': lead_days},
            'Min Order Qty':    {'number': moq},
            'Payment Terms':    {'rich_text': [{'text': {'content': payment}}]},
            'Reliability':      {'select': {'name': reliability}},
            'Notes':            {'rich_text': [{'text': {'content': notes}}]}
        }
    })
    print(f"  Added supplier: {name}")

def add_product(sku_name, category, size, colour, cost, price, supplier):
    notion_request('POST', 'pages', {
        'parent': {'database_id': PRODUCTS_DB},
        'properties': {
            'SKU Name':          {'title': [{'text': {'content': sku_name}}]},
            'Category':          {'select': {'name': category}},
            'Size':              {'select': {'name': size}},
            'Colour':            {'rich_text': [{'text': {'content': colour}}]},
            'Unit Cost (LKR)':   {'number': cost},
            'Selling Price (LKR)': {'number': price},
            'Supplier Name':     {'rich_text': [{'text': {'content': supplier}}]},
            'Active':            {'checkbox': True}
        }
    })
    print(f"  Added product: {sku_name}")

def add_stock(sku_name, current_qty, reorder_point, target_qty):
    from datetime import date
    notion_request('POST', 'pages', {
        'parent': {'database_id': STOCK_DB},
        'properties': {
            'SKU Name':      {'title': [{'text': {'content': sku_name}}]},
            'Current Qty':   {'number': current_qty},
            'Reorder Point': {'number': reorder_point},
            'Target Qty':    {'number': target_qty},
            'Last Updated':  {'date': {'start': str(date.today())}}
        }
    })
    print(f"  Added stock: {sku_name} ({current_qty} units)")

# ── SUPPLIERS (real names from your Notion) ──────────────────────────────────
print("\n[1/3] Adding Suppliers...")
suppliers = [
    ("JK Garments (Ibbagamuwa)",        "0771000001", "WhatsApp", 7,  50,  "50% upfront, 50% on delivery", "High",   "Main t-shirt supplier"),
    ("Alpha Apparels (Polgahawela)",     "0772000002", "WhatsApp", 10, 100, "Full payment upfront",         "High",   "Hoodies and sweaters"),
    ("KU Apparel (Kurunegala)",          "0773000003", "WhatsApp", 5,  30,  "Cash on delivery",             "Medium", "Shorts and casual wear"),
    ("GRACE Creations (Kurunegala)",     "0774000004", "WhatsApp", 7,  50,  "50% upfront",                  "High",   "Dresses and ladies wear"),
    ("Thusitha Graphics (Kurunegala)",   "0775000005", "WhatsApp", 3,  20,  "Cash on delivery",             "High",   "Printing and graphics"),
    ("Marsylka Manufacturing (EPZ)",     "0776000006", "Email",    14, 200, "30-day credit",                "Medium", "Bulk orders, EPZ quality"),
]
for s in suppliers:
    add_supplier(*s)

# ── PRODUCTS ──────────────────────────────────────────────────────────────────
print("\n[2/3] Adding Products/SKUs...")
products = [
    # (SKU Name, Category, Size, Colour, Cost, Price, Supplier)
    ("Classic White Tee - S",       "T-Shirt", "S",  "White",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic White Tee - M",       "T-Shirt", "M",  "White",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic White Tee - L",       "T-Shirt", "L",  "White",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic White Tee - XL",      "T-Shirt", "XL", "White",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic Black Tee - S",       "T-Shirt", "S",  "Black",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic Black Tee - M",       "T-Shirt", "M",  "Black",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Classic Black Tee - L",       "T-Shirt", "L",  "Black",  450,  950,  "JK Garments (Ibbagamuwa)"),
    ("Oversized Hoodie Black - M",  "Hoodie",  "M",  "Black", 1200, 2500,  "Alpha Apparels (Polgahawela)"),
    ("Oversized Hoodie Black - L",  "Hoodie",  "L",  "Black", 1200, 2500,  "Alpha Apparels (Polgahawela)"),
    ("Oversized Hoodie Grey - M",   "Hoodie",  "M",  "Grey",  1200, 2500,  "Alpha Apparels (Polgahawela)"),
    ("Oversized Hoodie Grey - L",   "Hoodie",  "L",  "Grey",  1200, 2500,  "Alpha Apparels (Polgahawela)"),
    ("Cargo Shorts Khaki - M",      "Shorts",  "M",  "Khaki",  700, 1600,  "KU Apparel (Kurunegala)"),
    ("Cargo Shorts Khaki - L",      "Shorts",  "L",  "Khaki",  700, 1600,  "KU Apparel (Kurunegala)"),
    ("Cargo Shorts Black - M",      "Shorts",  "M",  "Black",  700, 1600,  "KU Apparel (Kurunegala)"),
    ("Floral Midi Dress - Free",    "Dress",   "Free Size", "Floral", 900, 2200, "GRACE Creations (Kurunegala)"),
    ("Linen Dress White - Free",    "Dress",   "Free Size", "White",  950, 2200, "GRACE Creations (Kurunegala)"),
]
for p in products:
    add_product(*p)

# ── STOCK ─────────────────────────────────────────────────────────────────────
print("\n[3/3] Adding Stock levels...")
stock_levels = [
    # (SKU Name, Current Qty, Reorder Point, Target Qty)
    ("Classic White Tee - S",      35, 20, 80),
    ("Classic White Tee - M",      12, 20, 80),   # <-- below reorder point (agent will flag)
    ("Classic White Tee - L",      28, 20, 80),
    ("Classic White Tee - XL",      8, 20, 80),   # <-- below reorder point
    ("Classic Black Tee - S",      40, 20, 80),
    ("Classic Black Tee - M",      15, 20, 80),
    ("Classic Black Tee - L",       5, 20, 80),   # <-- below reorder point
    ("Oversized Hoodie Black - M", 18, 10, 40),
    ("Oversized Hoodie Black - L",  6, 10, 40),   # <-- below reorder point
    ("Oversized Hoodie Grey - M",  22, 10, 40),
    ("Oversized Hoodie Grey - L",  11, 10, 40),
    ("Cargo Shorts Khaki - M",     30, 15, 60),
    ("Cargo Shorts Khaki - L",     14, 15, 60),
    ("Cargo Shorts Black - M",      9, 15, 60),   # <-- below reorder point
    ("Floral Midi Dress - Free",   17, 10, 30),
    ("Linen Dress White - Free",    4, 10, 30),   # <-- below reorder point
]
for s in stock_levels:
    add_stock(*s)

print("\nDone! All data loaded into Notion.")
print("Items below reorder point (agent should flag these):")
for name, qty, rp, _ in stock_levels:
    if qty <= rp:
        print(f"  REORDER: {name} — {qty} units (reorder at {rp})")
