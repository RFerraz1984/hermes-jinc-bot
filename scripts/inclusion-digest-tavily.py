#!/usr/bin/env python3
"""
Inclusion Digest - Standalone script using Tavily API directly.
No agent context, no LLM - pure programmatic filtering.
Uses only stdlib (urllib, json).
"""
import os
import sys
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

# Get Tavily API key from environment or .env file
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
if not TAVILY_API_KEY:
    try:
        with open('/opt/data/.env') as f:
            for line in f:
                if line.startswith('TAVILY_API_KEY='):
                    TAVILY_API_KEY = line.strip().split('=', 1)[1]
                    break
    except:
        pass

if not TAVILY_API_KEY:
    print("[SILENT]")
    sys.exit(0)

QUERIES = [
    "acessibilidade PcD Brasil 2026 site:jornalistainclusivo.com",
    "inclusao deficiencia 2026 site:diariopcd.com.br",
    "direitos humanos acessibilidade 2026 site:agenciabrasil.ebc.com.br",
    "MDHC 2026 acessibilidade",
    "Dataverso PcD 2026"
]

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

HEADERS = {"Authorization": "Bearer " + TAVILY_API_KEY, "Content-Type": "application/json"}

def http_post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print("HTTP {}: {}".format(e.code, e.read().decode()), file=sys.stderr)
    except Exception as e:
        print("Request error: {}".format(e), file=sys.stderr)
    return None

def search_tavily(query, max_results=3):
    payload = {"query": query, "max_results": max_results, "search_depth": "basic", "include_raw_content": False}
    result = http_post(TAVILY_SEARCH_URL, payload)
    return result.get('results', []) if result else []

def extract_content(url):
    payload = {"urls": [url], "include_raw_content": True}
    result = http_post(TAVILY_EXTRACT_URL, payload)
    if result and result.get('results'):
        return result['results'][0].get('raw_content', '')
    return ''

def is_2026_content(text):
    text_lower = text.lower()
    if '2026' not in text_lower:
        return False
    for year in ['2025', '2024', '2023']:
        if year in text_lower and '2026' not in text_lower:
            return False
    return True

def main():
    all_items = []
    
    for query in QUERIES:
        results = search_tavily(query, max_results=3)
        for r in results:
            r['query'] = query
            all_items.append(r)
    
    if not all_items:
        print("[SILENT]")
        return 0
    
    seen_urls = set()
    unique_items = []
    for item in all_items:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_items.append(item)
    
    output_lines = []
    for item in unique_items[:15]:
        url = item.get('url', '')
        title = item.get('title', 'Sem titulo')[:120]
        source = urlparse(url).netloc if url else 'Web'
        
        content = extract_content(url)
        if not content:
            content = item.get('content', '')
        
        if is_2026_content(content):
            summary = content[:300].replace('\n', ' ').strip()
            output_lines.append("- {} — {} — {} — {}".format(title, source, url, summary))
            
            if len(output_lines) >= 5:
                break
    
    if not output_lines:
        print("[SILENT]")
    else:
        print('\n'.join(output_lines))
    
    return 0

if __name__ == '__main__':
    sys.exit(main())