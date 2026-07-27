import os
import urllib.request, json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("NOTION_TOKEN")

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

result = notion_request('POST', 'search', {'page_size': 50})
for r in result.get('results', []):
    t = r.get('object')
    title = ''
    if t == 'page':
        props = r.get('properties', {})
        for v in props.values():
            if v.get('type') == 'title':
                title = ''.join([x['plain_text'] for x in v.get('title', [])])
    elif t == 'database':
        title_list = r.get('title', [])
        title = ''.join([x['plain_text'] for x in title_list])
    print(f"{t.upper()}: '{title}' | id: {r['id']}")
