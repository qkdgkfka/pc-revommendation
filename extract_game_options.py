import re

with open('server_fixed.py', 'r') as f:
    content = f.read()

match = re.search(r'GAME_OPTIONS = \[.*?\]', content, flags=re.DOTALL)
if match:
    with open('server_data.py', 'a') as f:
        f.write("\n" + match.group(0) + "\n")
    content = content.replace(match.group(0), "")

    # Modify the import
    content = content.replace("from server_data import ", "from server_data import GAME_OPTIONS, ")
    
    with open('server_fixed.py', 'w') as f:
        f.write(content)
        
    print("GAME_OPTIONS extracted.")
