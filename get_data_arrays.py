import re

with open('app.js', 'r') as f:
    content = f.read()

dicts = re.findall(r'const ([A-Z_]+) = \{.*?\};', content, flags=re.DOTALL)
print(f"Dicts found: {[d for d in dicts]}")
