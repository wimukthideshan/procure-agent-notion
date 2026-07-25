# Notion Procurement & Stock Replenishment Agent

An automated inventory monitoring and purchase order generation agent integrated with Notion and Google Gemini. 

It monitors stock levels across multi-supplier apparel catalogs, groups shortages by manufacturer, respects Minimum Order Quantities (MOQ) and lead times, and stages structured purchase orders with draft communication ready for human review.

---

## Overview

Managing stock across multiple third-party factories requires constant monitoring of thresholds, reorder math, and manual communication. This agent automates the end-to-end replenishment pipeline:

- **Automated Stock Audit:** Scans current SKU levels against dynamic reorder points.
- **Supplier-Aware Batching:** Aggregates low-stock variants by manufacturer to consolidate orders.
- **MOQ & Lead-Time Rules:** Automatically adjusts batch sizes to meet factory minimum order constraints.
- **Draft-First Safety:** Creates staged Purchase Orders inside Notion with pre-drafted supplier messages; zero messages are dispatched without manual confirmation.
- **Type-Safe Validation:** Leverages Pydantic schemas to validate LLM output before database writes.

---

## Workflow Architecture

```mermaid
flowchart TD
    A[Notion Stock DB] -->|Query Active Inventory| B[Inventory Evaluation]
    B -->|Filter Below Threshold| C[Order Consolidation Layer]
    D[Products Catalog] --> C
    E[Suppliers Database] --> C
    C -->|Grouped Manufacturer Shortages| F[Gemini Replenishment Agent]
    F -->|Validated JSON Schema| G[PO Generator]
    G -->|Create Staged Orders| H[Notion Purchase Orders DB]
    H -->|Review & Send| I[Supplier Channels (WhatsApp / Email)]
```

---

## Database Schema (Notion)

The agent interfaces with four linked Notion databases:

1. **Suppliers:** Factory directory recording primary contact channels, lead times, Minimum Order Quantities (MOQ), and payment terms.
2. **Products / SKUs:** Master product catalog including SKU names, categories, sizes, colourways, and cost/retail pricing.
3. **Stock:** Real-time stock levels with automated status formulas indicating inventory health.
4. **Purchase Orders:** Staged PO entries containing itemized line items, cost totals, expected delivery windows, and draft supplier messages.

---

## Quickstart

### Prerequisites

- Python 3.10+
- Notion Integration Token (with database read/write permissions)
- Google Gemini API Key

### Installation

```bash
git clone https://github.com/wimukthideshan/procure-agent-notion.git
cd procure-agent-notion
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and provide your credentials:

```bash
cp .env.example .env
```

Fill in your `.env` variables:

```ini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
NOTION_TOKEN=your_notion_token
NOTION_SUPPLIERS_DB=your_suppliers_database_id
NOTION_PRODUCTS_DB=your_products_database_id
NOTION_STOCK_DB=your_stock_database_id
NOTION_PURCHASE_ORDERS_DB=your_purchase_orders_database_id
```

### Usage

Run the daily replenishment agent:

```bash
python agent.py
```

Inspect generated purchase orders:

```bash
python inspect_pos.py
```

---

## Testing & Evaluations

The project includes an automated test suite verifying ordering logic, supplier batching, and MOQ adjustments:

```bash
python evals/test_scenarios.py
```
