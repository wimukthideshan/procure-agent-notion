import os
import urllib.request, json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("NOTION_TOKEN")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "3efec7ef-d080-8066-a20e-d984d454f688")

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

def create_database(title, properties):
    return notion_request('POST', 'databases', {
        'parent': {'type': 'page_id', 'page_id': PARENT_PAGE_ID},
        'title': [{'type': 'text', 'text': {'content': title}}],
        'properties': properties
    })

# 1. SUPPLIERS DATABASE
print('Creating Suppliers database...')
suppliers = create_database('Suppliers', {
    'Name':            {'title': {}},
    'Contact':         {'rich_text': {}},
    'Contact Channel': {'select': {'options': [
                            {'name': 'WhatsApp', 'color': 'green'},
                            {'name': 'Email', 'color': 'blue'},
                            {'name': 'Phone', 'color': 'yellow'}
                        ]}},
    'Lead Time (days)':{'number': {'format': 'number'}},
    'Min Order Qty':   {'number': {'format': 'number'}},
    'Payment Terms':   {'rich_text': {}},
    'Reliability':     {'select': {'options': [
                            {'name': 'High', 'color': 'green'},
                            {'name': 'Medium', 'color': 'yellow'},
                            {'name': 'Low', 'color': 'red'}
                        ]}},
    'Notes':           {'rich_text': {}}
})
suppliers_id = suppliers['id']
print(f'  Suppliers DB ID: {suppliers_id}')

# 2. PRODUCTS/SKUs DATABASE
print('Creating Products/SKUs database...')
products = create_database('Products / SKUs', {
    'SKU Name':       {'title': {}},
    'Category':       {'select': {'options': [
                           {'name': 'T-Shirt', 'color': 'blue'},
                           {'name': 'Shorts', 'color': 'green'},
                           {'name': 'Hoodie', 'color': 'purple'},
                           {'name': 'Dress', 'color': 'pink'},
                           {'name': 'Pants', 'color': 'orange'},
                           {'name': 'Other', 'color': 'gray'}
                       ]}},
    'Size':           {'select': {'options': [
                           {'name': 'XS'}, {'name': 'S'}, {'name': 'M'},
                           {'name': 'L'}, {'name': 'XL'}, {'name': 'XXL'},
                           {'name': 'Free Size'}
                       ]}},
    'Colour':         {'rich_text': {}},
    'Unit Cost (LKR)':{'number': {'format': 'number'}},
    'Selling Price (LKR)': {'number': {'format': 'number'}},
    'Supplier Name':  {'rich_text': {}},
    'Active':         {'checkbox': {}}
})
products_id = products['id']
print(f'  Products DB ID: {products_id}')

# 3. STOCK DATABASE
print('Creating Stock database...')
stock = create_database('Stock', {
    'SKU Name':           {'title': {}},
    'Current Qty':        {'number': {'format': 'number'}},
    'Reorder Point':      {'number': {'format': 'number'}},
    'Target Qty':         {'number': {'format': 'number'}},
    'Last Updated':       {'date': {}},
    'Status':             {'formula': {'expression': 'if(prop("Current Qty") <= prop("Reorder Point"), "🔴 Reorder Now", "🟢 OK")'}}
})
stock_id = stock['id']
print(f'  Stock DB ID: {stock_id}')

# 4. PURCHASE ORDERS DATABASE
print('Creating Purchase Orders database...')
purchase_orders = create_database('Purchase Orders', {
    'PO Number':           {'title': {}},
    'Supplier':            {'rich_text': {}},
    'Items Summary':       {'rich_text': {}},
    'Total Cost (LKR)':    {'number': {'format': 'number'}},
    'Status':              {'select': {'options': [
                                {'name': 'Draft', 'color': 'gray'},
                                {'name': 'Approved', 'color': 'blue'},
                                {'name': 'Sent', 'color': 'yellow'},
                                {'name': 'Received', 'color': 'green'},
                                {'name': 'Late', 'color': 'red'}
                            ]}},
    'Order Date':          {'date': {}},
    'Expected Delivery':   {'date': {}},
    'Actual Delivery':     {'date': {}},
    'Draft Message':       {'rich_text': {}},
    'Agent Notes':         {'rich_text': {}}
})
po_id = purchase_orders['id']
print(f'  Purchase Orders DB ID: {po_id}')

print('\n✅ ALL 4 DATABASES CREATED!')
print(f'\nAdd these to your .env file:')
print(f'NOTION_SUPPLIERS_DB={suppliers_id}')
print(f'NOTION_PRODUCTS_DB={products_id}')
print(f'NOTION_STOCK_DB={stock_id}')
print(f'NOTION_PURCHASE_ORDERS_DB={po_id}')
