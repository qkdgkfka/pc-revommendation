with open('server_fixed.py', 'r') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "CPU_CATALOG = [" in line:
        start_idx = i
    if "CATALOGS = {" in line:
        for j in range(i, len(lines)):
            if lines[j].strip() == "}":
                end_idx = j
                break
        break

if start_idx != -1 and end_idx != -1:
    catalog_lines = lines[start_idx:end_idx+1]
    
    with open('server_catalogs.py', 'w') as f:
        f.write('from typing import Dict, List, Any\n\n')
        f.writelines(catalog_lines)
    
    new_lines = lines[:start_idx] + ["from server_catalogs import CPU_CATALOG, GPU_CATALOG, RAM_CATALOG, MB_CATALOG, PSU_CATALOG, STORAGE_CATALOG, HDD_CATALOG, CASE_CATALOG, SOFTWARE_CATALOG, CATALOGS\n"] + lines[end_idx+1:]
    
    with open('server_fixed.py', 'w') as f:
        f.writelines(new_lines)
    print("server_fixed.py refactored successfully.")
