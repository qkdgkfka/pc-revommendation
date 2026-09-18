import re

with open('app.js', 'r') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "let GPUS_NVIDIA = [" in line:
        start_idx = i
    if "let SOFTWARES = [" in line:
        for j in range(i, len(lines)):
            if lines[j].strip() == "];":
                end_idx = j
                break
        break

if start_idx != -1 and end_idx != -1:
    data_lines = lines[start_idx:end_idx+1]
    
    with open('app_data.js', 'w') as f:
        f.writelines(data_lines)
    
    new_lines = lines[:start_idx] + lines[end_idx+1:]
    
    with open('app.js', 'w') as f:
        f.writelines(new_lines)
    
    with open('index.html', 'r') as f:
        html = f.read()
    
    html = html.replace('<script src="app.js"></script>', '<script src="app_data.js"></script>\n    <script src="app.js"></script>')
    
    with open('index.html', 'w') as f:
        f.write(html)
        
    print("app.js refactored successfully.")
else:
    print("Could not find data bounds in app.js")

