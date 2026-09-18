import re

with open('server_data.py', 'r') as f:
    content = f.read()

match = re.search(r'GAME_OPTIONS = \[.*?\]\n', content, flags=re.DOTALL)
if match:
    game_options_str = match.group(0)
    content = content.replace(game_options_str, "")
    
    # insert after typing imports
    lines = content.split('\n')
    lines.insert(2, game_options_str)
    
    with open('server_data.py', 'w') as f:
        f.write('\n'.join(lines))
    print("Fixed GAME_OPTIONS order.")
