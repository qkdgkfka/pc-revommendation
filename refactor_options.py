with open('server_fixed.py', 'r') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "GAME_OPTIONS = [" in line:
        start_idx = i
        for j in range(i, len(lines)):
            if lines[j].strip() == "]":
                end_idx = j
                break
        break

if start_idx != -1 and end_idx != -1:
    option_lines = lines[start_idx:end_idx+1]
    
    with open('server_catalogs.py', 'a') as f:
        f.write('\n')
        f.writelines(option_lines)
    
    # Also update the import in server_fixed.py
    for i, line in enumerate(lines):
        if line.startswith("from server_catalogs import "):
            lines[i] = line.replace("CATALOGS\n", "CATALOGS, GAME_OPTIONS\n")
            break
            
    new_lines = lines[:start_idx] + lines[end_idx+1:]
    
    with open('server_fixed.py', 'w') as f:
        f.writelines(new_lines)
    print("GAME_OPTIONS extracted successfully.")
