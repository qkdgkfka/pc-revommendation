import re

with open('app.js', 'r') as f:
    content = f.read()

sections = re.split(r'// ─+\n// (.*?)\n// ─+', content)
utils_idx = sections.index("UTILITIES") + 1
utils_code = sections[utils_idx]

with open('app_utils.js', 'w') as f:
    f.write(utils_code)

new_content = ""
for i in range(len(sections)):
    if i == utils_idx:
        new_content += "\n// Utilities are in app_utils.js\n"
    elif i % 2 == 1:
        new_content += "// ─────────────────────────────────────────────────────────────\n// " + sections[i] + "\n// ─────────────────────────────────────────────────────────────\n"
    else:
        new_content += sections[i]

with open('app_refactored.js', 'w') as f:
    f.write(new_content)

