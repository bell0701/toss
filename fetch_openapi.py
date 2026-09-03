import urllib.request
import json
import traceback

url = "https://openapi.tossinvest.com/openapi-docs/latest/openapi.json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
        data = json.loads(content)
        target_paths = {}
        for path, methods in data.get('paths', {}).items():
            if 'conditional-orders' in path:
                target_paths[path] = methods
        with open('openapi_out.txt', 'w', encoding='utf-8') as out:
            out.write(json.dumps(target_paths, indent=2, ensure_ascii=False))
except Exception as e:
    with open('openapi_out.txt', 'w', encoding='utf-8') as out:
        out.write(str(e))
        out.write(traceback.format_exc())
