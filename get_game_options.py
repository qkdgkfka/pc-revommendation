import re
with open('server_fixed.py', 'r') as f:
    content = f.read()
match = re.search(r'GAME_OPTIONS = \[.*?\]', content, flags=re.DOTALL)
if match:
    print(match.group(0))
