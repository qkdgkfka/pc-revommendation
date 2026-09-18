import re
with open('server_fixed.py', 'r') as f:
    lines = f.readlines()

def extract_dict(name):
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if line.startswith(f"{name} = {{"):
            start = i
            # Find the matching closing brace, assuming it starts with }
            for j in range(i, len(lines)):
                if lines[j].startswith("}"):
                    end = j
                    break
            break
    if start != -1 and end != -1:
        extracted = lines[start:end+1]
        del lines[start:end+1]
        
        with open('server_catalogs.py', 'a') as f:
            f.write('\n')
            f.writelines(extracted)
            
        for i, line in enumerate(lines):
            if line.startswith("from server_catalogs import "):
                lines[i] = line.replace("\n", f", {name}\n")
                break
        return True
    return False

extract_dict("BENCHMARK_FPS_BY_GPU")
extract_dict("GAME_FPS_PROFILES")
extract_dict("WORK_PROFILES")
extract_dict("WORK_ALIASES")
extract_dict("COMMON_GPU_MODEL_NUMBERS")
extract_dict("GPU_MAKER_ALIASES")
extract_dict("GPU_MAKER_LABELS")

with open('server_fixed.py', 'w') as f:
    f.writelines(lines)
print("Data extracted successfully.")
