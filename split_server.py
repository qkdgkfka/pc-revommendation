import re

with open('server_fixed.py', 'r') as f:
    content = f.read()

sections = re.split(r'# ─+\n# (.*?)\n# ─+', content)
for i in range(1, len(sections), 2):
    title = sections[i]
    code = sections[i+1]
    print(f"{title}: {len(code.splitlines())} lines")
