"""
agent.py — Gemini tool-calling agent for clothing business stock management.

Architecture decisions:
  - Single agent (not multi-agent): task scope is narrow; simpler to trace/debug.
  - LLM handles: grouping judgement, message drafting, anomaly flagging.
  - Deterministic code handles: threshold checks, quantity maths, Notion writes.
  - Draft-only: nothing sent to suppliers without human approval.
  - Provider-swappable: all LLM calls go through generate(), one-line change.
"""

import os
import json
import time
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

# ── LLM wrapper with automatic retries and fallback ───────────────────────────

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODELS  = [
    os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]


def generate(prompt: str, response_schema=None) -> str | dict:
    """
    Robust generator:
    - Retries with exponential backoff on 503 / 429
    - Falls back across candidate models if one is overloaded
    - Supports structured JSON parsing
    """
    last_err = None
    for model_name in dict.fromkeys(MODELS):
        for attempt in range(3):
            try:
                config_args = {}
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema

                config = types.GenerateContentConfig(**config_args) if config_args else None
                response = _client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                text = response.text.strip()
                if response_schema:
                    # Clean potential markdown wrapping
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    return json.loads(text.strip())
                return text
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"All models failed. Last error: {last_err}")


# ── Tool functions (registered with the agent) ────────────────────────────────

from tools.notion_tools import (
    get_low_stock_items,
    get_supplier_info,
    get_product_info,
    create_draft_purchase_order,
    get_overdue_purchase_orders,
)


# ── Pydantic schemas for validated LLM output ────────────────────────────────

class OrderItem(BaseModel):
    sku_name:  str
    qty:       int
    unit_cost: float

class PurchaseOrderPlan(BaseModel):
    supplier_name:          str
    items:                  list[OrderItem]
    draft_message:          str
    agent_notes:            str
    expected_delivery_days: int


# ── Core agent logic ──────────────────────────────────────────────────────────

def run_stock_check():
    print("\n" + "="*60)
    print("STOCK AGENT — Daily Run")
    print("="*60)

    # STEP 1: Find all low-stock items (deterministic)
    low_stock = get_low_stock_items()
    if not low_stock:
        print("All stock levels are healthy. No action needed.")
        return

    print(f"\nFound {len(low_stock)} item(s) below reorder point:")
    for item in low_stock:
        print(f"  - {item['sku_name']}: {int(item['current_qty'])} units "
              f"(reorder at {int(item['reorder_point'])}, target {int(item['target_qty'])})")

    # STEP 2: Enrich with product + supplier info
    enriched = []
    for item in low_stock:
        product = get_product_info(item["sku_name"])
        if not product:
            print(f"  WARNING: No product info found for '{item['sku_name']}' — skipping.")
            continue
        supplier = get_supplier_info(product["supplier_name"])
        if not supplier:
            print(f"  WARNING: No supplier found for '{product['supplier_name']}' — skipping.")
            continue
        enriched.append({**item, **product, "supplier": supplier})

    if not enriched:
        print("No actionable items after enrichment.")
        return

    # STEP 3: LLM groups items by supplier and decides order quantities
    # Trade-off: LLM for grouping handles edge cases (same supplier, MOQ rounding)
    # better than hand-coded rules, while keeping costs low (small prompt).
    suppliers_summary = {}
    for e in enriched:
        s = e["supplier_name"]
        if s not in suppliers_summary:
            suppliers_summary[s] = {
                "supplier": e["supplier"],
                "items": []
            }
        suppliers_summary[s]["items"].append({
            "sku_name":      e["sku_name"],
            "current_qty":   e["current_qty"],
            "reorder_point": e["reorder_point"],
            "target_qty":    e["target_qty"],
            "unit_cost":     e["unit_cost"],
        })

    created_pos = []

    for supplier_name, data in suppliers_summary.items():
        supplier_info = data["supplier"]
        items_data    = data["items"]

        prompt = f"""
You are a stock management assistant for a clothing business in Sri Lanka.

Supplier: {supplier_name}
Contact: {supplier_info['contact']} via {supplier_info['channel']}
Lead time: {supplier_info['lead_days']} days
Minimum order quantity (MOQ): {supplier_info['moq']} pieces total
Payment terms: {supplier_info['payment_terms']}

Items to reorder:
{json.dumps(items_data, indent=2)}

Your job:
1. Calculate the order quantity for each item: bring it up to target_qty.
   Round up to the nearest 5. Ensure total order meets MOQ.
2. Draft a short, polite WhatsApp/email message in English to the supplier
   listing the items and quantities needed.
3. Write brief agent_notes explaining any decisions (e.g. MOQ bump, rounding).
4. Set expected_delivery_days based on the supplier's lead time.

Return a valid JSON matching the schema exactly.
        """.strip()

        print(f"\nAsking Gemini to plan order for: {supplier_name}")
        plan_dict = generate(prompt, response_schema=PurchaseOrderPlan)

        # Validate with Pydantic before touching Notion
        plan = PurchaseOrderPlan(**plan_dict)

        # STEP 4: Create Draft PO in Notion (awaits human approval)
        po_url = create_draft_purchase_order(
            supplier_name=plan.supplier_name,
            items=[i.model_dump() for i in plan.items],
            draft_message=plan.draft_message,
            agent_notes=plan.agent_notes,
            expected_delivery_days=plan.expected_delivery_days,
        )
        created_pos.append((supplier_name, po_url))
        print(f"  Draft PO created: {po_url}")

    # STEP 5: Check for overdue orders
    overdue = get_overdue_purchase_orders()
    if overdue:
        print(f"\nOVERDUE ORDERS ({len(overdue)}):")
        for po in overdue:
            follow_up = generate(
                f"Write a short, polite follow-up WhatsApp message to supplier "
                f"'{po['supplier']}' about purchase order '{po['po_number']}' "
                f"which was expected on {po['expected']} and hasn't arrived. "
                f"Items: {po['items_summary']}. Keep it under 3 sentences."
            )
            print(f"\n  PO: {po['po_number']} | Supplier: {po['supplier']}")
            print(f"  Follow-up draft:\n    {follow_up}")

    # STEP 6: Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Low-stock items found : {len(low_stock)}")
    print(f"  Draft POs created     : {len(created_pos)}")
    print(f"  Overdue orders flagged: {len(overdue)}")
    print("\nDraft POs (review and approve in Notion):")
    for name, url in created_pos:
        print(f"  - {name}: {url}")
    print("\nNo messages sent. Review drafts in Notion -> Purchase Orders.")


if __name__ == "__main__":
    run_stock_check()
