
import urllib.request
import re

url = 'https://ir.mara.com/news-events/press-releases'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode('utf-8')
pattern = r'<a href="([^"]*press-releases/detail/[^"]+)">\s*([^<]+)\s*</a>'
matches = re.findall(pattern, html)
results = []
for pair in matches:
    link = pair[0]
    the_title = pair[1].strip()
    keywords = ['earnings', 'cost', 'financial', 'production', 'august', 'july', 'june', 'may', 'april', 'march', 'february', 'january', '2024', 'treasury', 'bitcoin', 'q4']
    if any(kw in the_title.lower() for kw in keywords):
        results.append('Title: ' + the_title + ' | URL: ' + link)
for r in results:
    print(r)
