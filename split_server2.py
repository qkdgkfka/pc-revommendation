import re

with open('server_fixed.py', 'r') as f:
    content = f.read()

sections = re.split(r'# ─+\n# (.*?)\n# ─+', content)
for i in range(1, len(sections), 2):
    if sections[i] == 'FPS estimation':
        with open('server_fps.py', 'w') as out:
            out.write("from typing import Dict, Any, Tuple\n")
            out.write(sections[i+1])
