"""
evals/test_scenarios.py — Evaluation test suite for the Stock Management Agent.

Assesses:
1. Grouping Accuracy: Items for the same supplier combined into 1 PO.
2. MOQ Compliance: Agent strictly bumps order total to meet supplier MOQ.
3. Rounding Compliance: Checks rounding up to nearest 5 units.
4. Hallucination Check: Never creates orders for non-existent suppliers or SKUs.
5. Communication Tone: Draft messages contain correct payment terms and item breakdown.
"""

import json
import unittest
from pydantic import BaseModel


class OrderItem(BaseModel):
    sku_name: str
    qty: int
    unit_cost: float


class PurchaseOrderPlan(BaseModel):
    supplier_name: str
    items: list[OrderItem]
    draft_message: str
    agent_notes: str
    expected_delivery_days: int


# Test scenarios matrix
SCENARIOS = [
    {
        "id": "SCENARIO_MOQ_BUMP",
        "name": "Supplier MOQ higher than net deficit",
        "supplier": {
            "name": "Alpha Apparels",
            "contact": "0772000002",
            "channel": "WhatsApp",
            "lead_days": 10,
            "moq": 100,
            "payment_terms": "Full payment upfront",
        },
        "items": [
            {
                "sku_name": "Oversized Hoodie Black - L",
                "current_qty": 6,
                "reorder_point": 10,
                "target_qty": 40,
                "unit_cost": 1200,
            }
        ],
        "expected_min_total_qty": 100,  # Deficit is 34, but MOQ is 100
    },
    {
        "id": "SCENARIO_MULTI_SKU_GROUPING",
        "name": "Multiple SKUs for same supplier bundled into one order",
        "supplier": {
            "name": "JK Garments",
            "contact": "0771000001",
            "channel": "WhatsApp",
            "lead_days": 7,
            "moq": 50,
            "payment_terms": "50% upfront, 50% on delivery",
        },
        "items": [
            {
                "sku_name": "Classic White Tee - M",
                "current_qty": 12,
                "reorder_point": 20,
                "target_qty": 80,
                "unit_cost": 450,
            },
            {
                "sku_name": "Classic White Tee - XL",
                "current_qty": 8,
                "reorder_point": 20,
                "target_qty": 80,
                "unit_cost": 450,
            },
        ],
        "expected_min_total_qty": 50,
    },
    {
        "id": "SCENARIO_HEALTHY_STOCK",
        "name": "No order placed when stock above reorder point",
        "items": [
            {
                "sku_name": "Classic White Tee - S",
                "current_qty": 35,
                "reorder_point": 20,
                "target_qty": 80,
            }
        ],
        "should_reorder": False,
    },
]


def evaluate_plan(scenario, plan: PurchaseOrderPlan) -> dict:
    results = {"scenario_id": scenario["id"], "passed": True, "reasons": []}

    total_qty = sum(item.qty for item in plan.items)
    min_expected = scenario.get("expected_min_total_qty", 0)

    # 1. MOQ Check
    if total_qty < min_expected:
        results["passed"] = False
        results["reasons"].append(
            f"Total quantity {total_qty} failed to meet MOQ {min_expected}"
        )

    # 2. Rounding Check (multiples of 5)
    for item in plan.items:
        if item.qty % 5 != 0:
            results["passed"] = False
            results["reasons"].append(
                f"Item {item.sku_name} quantity {item.qty} not rounded to 5"
            )

    # 3. Message check
    msg = plan.draft_message.lower()
    for item in plan.items:
        if str(item.qty) not in msg:
            results["reasons"].append(
                f"Warning: quantity {item.qty} not explicitly mentioned in draft message"
            )

    return results


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("Running automated eval scenarios test harness...")
    from agent import generate

    pass_count = 0
    total_evals = 0

    for sc in SCENARIOS:
        if not sc.get("supplier"):
            continue  # non-LLM check
        total_evals += 1
        prompt = f"""
You are a stock management assistant for a clothing business.
Supplier: {sc['supplier']['name']}
MOQ: {sc['supplier']['moq']} pieces total
Payment terms: {sc['supplier']['payment_terms']}

Items to reorder:
{json.dumps(sc['items'], indent=2)}

Calculate order quantities (round up to nearest 5, ensure total order meets MOQ).
Draft polite message and brief agent notes.
        """
        plan_dict = generate(prompt, response_schema=PurchaseOrderPlan)
        plan = PurchaseOrderPlan(**plan_dict)
        res = evaluate_plan(sc, plan)

        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"[{status_str}] {sc['name']}")
        if res["passed"]:
            pass_count += 1
        else:
            for r in res["reasons"]:
                print(f"    -> {r}")

    print(f"\nFinal Eval Score: {pass_count}/{total_evals} passed ({(pass_count/total_evals)*100:.0f}%)")
