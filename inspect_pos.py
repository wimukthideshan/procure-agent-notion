import os
import urllib.request, json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("NOTION_TOKEN")
PO_DB = os.environ.get("NOTION_PURCHASE_ORDERS_DB")

req = urllib.request.Request(f'https://api.notion.com/v1/databases/{PO_DB}/query', data=b'{}', headers={
    'Authorization': f'Bearer {TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
})
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print('--- LIVE PURCHASE ORDERS IN NOTION ---')
    for r in data.get('results', []):
        p = r['properties']
        po_num = ''.join([t['plain_text'] for t in p['PO Number']['title']])
        supp = ''.join([t['plain_text'] for t in p['Supplier']['rich_text']])
        cost = p['Total Cost (LKR)']['number']
        status = p['Status']['select']['name']
        msg = ''.join([t['plain_text'] for t in p['Draft Message']['rich_text']])
        notes = ''.join([t['plain_text'] for t in p['Agent Notes']['rich_text']])
        print(f'\n* [{status}] {po_num} -> {supp} | Total: LKR {cost}')
        print(f'  Notes: {notes}')
        print(f'  Draft Message:\n    "{msg}"')
