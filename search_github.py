import urllib.request, json, urllib.parse

def search_github(query, sort="stars"):
    url = f'https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort={sort}&order=desc&per_page=10'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()).get('items', [])
    except Exception as e:
        print(f"Error searching {query}: {e}")
        return []

results = {
    'voice_ai': [f"{r.get('full_name', '')} - Stars: {r.get('stargazers_count', 0)} - {r.get('description', '')[:100]}" for r in search_github('voice ai agent OR AI calling OR AI phone OR "voice agent"')],
    'user_repos': [f"{r.get('full_name', '')} - Stars: {r.get('stargazers_count', 0)} - {r.get('description', '')[:100]}" for r in search_github('user:wefluidmedia-prog')]
}

with open('gh_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
