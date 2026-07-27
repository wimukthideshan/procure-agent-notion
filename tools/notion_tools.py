"""
notion_tools.py — All Notion API interactions for the stock agent.
Keeps deterministic logic (maths, thresholds) out of the LLM.
Uses raw urllib requests for compatibility with any notion-client version.
"""
import os
import json
import urllib.request
from datetime import date
from dotenv import load_dotenv

load_dotenv()

_TOKEN       = os.environ["NOTION_TOKEN"]
SUPPLIERS_DB = os.environ["NOTION_SUPPLIERS_DB"]
PRODUCTS_DB  = os.environ["NOTION_PRODUCTS_DB"]
STOCK_DB     = os.environ["NOTION_STOCK_DB"]
PO_DB        = os.environ["NOTION_PURCHASE_ORDERS_DB"]


# ── low-level HTTP ────────────────────────────────────────────────────────────

def _request(method: str, endpoint: str, data: dict = None) -> dict:
    url  = f"https://api.notion.com/v1/{endpoint}"
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization":  f"Bearer {_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type":   "application/json",
    })
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())

def _query_db(db_id: str, filter_body: dict = None) -> list[dict]:
    payload = {"page_size": 100}
    if filter_body:
        payload["filter"] = filter_body
    return _request("POST", f"databases/{db_id}/query", payload)["results"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _text(prop) -> str:
    items = prop.get("rich_text") or prop.get("title") or []
    return "".join(t["plain_text"] for t in items)

def _num(prop) -> float:
    return prop.get("number") or 0

def _select(prop) -> str:
    s = prop.get("select")
    return s["name"] if s else ""

def _date_str(prop) -> str:
    d = prop.get("date")
    return d["start"] if d else ""


# ── public tool functions (called by the agent) ───────────────────────────────

def get_low_stock_items() -> list[dict]:
    """
    Query Stock DB and return items where current_qty <= reorder_point.
    Pure deterministic — no LLM needed here.
    """
    results = _query_db(STOCK_DB)
    low = []
    for r in results:
        p = r["properties"]
        current = _num(p["Current Qty"])
        reorder  = _num(p["Reorder Point"])
        if current <= reorder:
            low.append({
                "id":            r["id"],
                "sku_name":      _text(p["SKU Name"]),
                "current_qty":   current,
                "reorder_point": reorder,
                "target_qty":    _num(p["Target Qty"]),
            })
    return low


def get_supplier_info(supplier_name: str) -> dict | None:
    """Fetch a supplier's details by name."""
    results = _query_db(SUPPLIERS_DB, {
        "property": "Name", "title": {"equals": supplier_name}
    })
    if not results:
        return None
    p = results[0]["properties"]
    return {
        "name":          _text(p["Name"]),
        "contact":       _text(p["Contact"]),
        "channel":       _select(p["Contact Channel"]),
        "lead_days":     _num(p["Lead Time (days)"]),
        "moq":           _num(p["Min Order Qty"]),
        "payment_terms": _text(p["Payment Terms"]),
        "reliability":   _select(p["Reliability"]),
        "notes":         _text(p["Notes"]),
    }


def get_product_info(sku_name: str) -> dict | None:
    """Fetch product details (cost, supplier) for a SKU."""
    results = _query_db(PRODUCTS_DB, {
        "property": "SKU Name", "title": {"equals": sku_name}
    })
    if not results:
        return None
    p = results[0]["properties"]
    return {
        "sku_name":      _text(p["SKU Name"]),
        "category":      _select(p["Category"]),
        "size":          _select(p["Size"]),
        "colour":        _text(p["Colour"]),
        "unit_cost":     _num(p["Unit Cost (LKR)"]),
        "selling_price": _num(p["Selling Price (LKR)"]),
        "supplier_name": _text(p["Supplier Name"]),
    }


def create_draft_purchase_order(
    supplier_name: str,
    items: list[dict],
    draft_message: str,
    agent_notes: str,
    expected_delivery_days: int,
) -> str:
    """
    Create a Draft PO in Notion. Returns the PO page URL.
    Nothing is sent to the supplier — awaits human approval.
    """
    from datetime import timedelta
    today     = date.today()
    po_number = f"PO-{today.strftime('%Y%m%d')}-{supplier_name[:3].upper()}"
    total_cost = sum(i["qty"] * i["unit_cost"] for i in items)
    items_summary = "\n".join(
        f"  * {i['sku_name']} x{i['qty']} @ LKR {i['unit_cost']}"
        for i in items
    )
    expected = today + timedelta(days=int(expected_delivery_days))

    page = _request("POST", "pages", {
        "parent": {"database_id": PO_DB},
        "properties": {
            "PO Number":        {"title": [{"text": {"content": po_number}}]},
            "Supplier":         {"rich_text": [{"text": {"content": supplier_name}}]},
            "Items Summary":    {"rich_text": [{"text": {"content": items_summary}}]},
            "Total Cost (LKR)": {"number": round(total_cost, 2)},
            "Status":           {"select": {"name": "Draft"}},
            "Order Date":       {"date": {"start": str(today)}},
            "Expected Delivery":{"date": {"start": str(expected)}},
            "Draft Message":    {"rich_text": [{"text": {"content": draft_message}}]},
            "Agent Notes":      {"rich_text": [{"text": {"content": agent_notes}}]},
        }
    })
    return page.get("url", f"https://notion.so/{page['id'].replace('-','')}")


def get_overdue_purchase_orders() -> list[dict]:
    """Return POs with status=Sent and expected delivery date in the past."""
    today = str(date.today())
    results = _query_db(PO_DB, {
        "and": [
            {"property": "Status", "select": {"equals": "Sent"}},
            {"property": "Expected Delivery", "date": {"before": today}},
        ]
    })
    overdue = []
    for r in results:
        p = r["properties"]
        overdue.append({
            "id":            r["id"],
            "po_number":     _text(p["PO Number"]),
            "supplier":      _text(p["Supplier"]),
            "expected":      _date_str(p["Expected Delivery"]),
            "items_summary": _text(p["Items Summary"]),
        })
    return overdue


def update_stock_qty(stock_page_id: str, new_qty: int):
    """Update a stock entry's current quantity and last-updated date."""
    _request("PATCH", f"pages/{stock_page_id}", {
        "properties": {
            "Current Qty":  {"number": new_qty},
            "Last Updated": {"date": {"start": str(date.today())}},
        }
    })
