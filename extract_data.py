import re

with open('server_fixed.py', 'r') as f:
    content = f.read()

# We can search for the definitions
constants = [
    "GPU_DANAWA_CATEGORY_IDS", "STORAGE_DANAWA_CATEGORY_IDS", "MB_DANAWA_CATEGORY_IDS",
    "DANAWA_BROWSE_CATEGORY_IDS", "GPU_MAKER_ALIASES", "GPU_MAKER_LABELS",
    "COMPUZONE_CATEGORY_IDS", "COMMON_GPU_MODEL_NUMBERS", "GAME_GENRE_FACTORS",
    "BENCHMARK_FPS_BY_GPU", "GAME_FPS_PROFILES", "GAME_FRAME_CAPS",
    "WORK_PROFILES", "WORK_ALIASES"
]

out = "from typing import Dict, Any, Tuple, Set\n\n"

for c in constants:
    # Use regex to find `c = { ... }` or `c = set(...)`
    # It might span multiple lines
    match = re.search(r'^' + c + r'\s*:\s*.*?=\s*\{.*?\n(?:[^\n]*\n)*?\}', content, flags=re.MULTILINE)
    if not match:
        match = re.search(r'^' + c + r'\s*=\s*\{.*?\n(?:[^\n]*\n)*?\}', content, flags=re.MULTILINE)
    if not match:
        match = re.search(r'^' + c + r'\s*=\s*\{.*?\}', content, flags=re.MULTILINE)

    if match:
        out += match.group(0) + "\n\n"
        # Remove from content
        content = content.replace(match.group(0), "")

with open('server_data.py', 'w') as f:
    f.write(out)

# Now inject the import at the top
import_stmt = f"from server_data import {', '.join(constants)}\n"
lines = content.split('\n')
for i, line in enumerate(lines):
    if "from server_catalogs import" in line:
        lines.insert(i+1, import_stmt)
        break

with open('server_fixed.py', 'w') as f:
    f.write('\n'.join(lines))
    
print("Constants extracted.")
