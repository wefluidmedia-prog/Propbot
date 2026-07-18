import urllib.request, json, urllib.parse

def search_hf_datasets(query):
    url = f'https://huggingface.co/api/datasets?search={urllib.parse.quote(query)}&limit=10&sort=downloads&direction=-1'
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        print(f"Error searching {query}: {e}")
        return []

results = {
    'hindi_speech': [f"{d.get('id', '')} - DLs: {d.get('downloads', 0)} - Tags: {', '.join([t for t in d.get('tags', []) if ':' in t][:3])}" for d in search_hf_datasets('hindi speech')],
    'call_center': [f"{d.get('id', '')} - DLs: {d.get('downloads', 0)} - Tags: {', '.join([t for t in d.get('tags', []) if ':' in t][:3])}" for d in search_hf_datasets('call center')],
    'customer_service': [f"{d.get('id', '')} - DLs: {d.get('downloads', 0)} - Tags: {', '.join([t for t in d.get('tags', []) if ':' in t][:3])}" for d in search_hf_datasets('customer service voice')],
    'indic_tts': [f"{d.get('id', '')} - DLs: {d.get('downloads', 0)} - Tags: {', '.join([t for t in d.get('tags', []) if ':' in t][:3])}" for d in search_hf_datasets('indic tts')]
}

with open('hf_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
