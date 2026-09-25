"""Persist representative predictions; these are NOT additional measurements."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server_fixed import estimate_fps_bundle,attach_graphics_modes
from server_catalogs import GPU_CATALOG,CPU_CATALOG,GAME_OPTIONS

def main():
    cpu=next(c for c in CPU_CATALOG if c["id"]=="cpu_r7_9800x3d")
    count=0
    for game in GAME_OPTIONS:
        for gpu in GPU_CATALOG:
            for resolution in ("1080","1440","2160"):
                fps=estimate_fps_bundle(gpu,cpu,{"gb":32},game["id"],resolution,144,"mid",[game["genre"]])
                attach_graphics_modes(fps,gpu,cpu,game["id"],resolution)
                count+=1
    print(f"Stored {count} configurations (32GB / 9800X3D). Other configurations save on request.")
if __name__=="__main__":main()
