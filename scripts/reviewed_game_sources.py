"""Pinned, manually reviewed stock (not overclocked) charts and official support."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from pathlib import Path
from scripts.refresh_game_data import metadata,base_row,fetch,normalized

REVIEW="https://www.thefpsreview.com/2025/11/17/overclocking-nvidia-geforce-rtx-5070/"
SUPPORT="https://www.nvidia.com/content/dam/en-zz/Solutions/geforce/news/nvidia-rtx-games-engines-apps/dlss-rt-games-apps-overrides.json"
PINS={'alanwake2': '1be585568ed55e36c40d0db10d964247079d3cb6f7da269e7f5b338db6dbe518', 'clairobscur33': 'ae8e6f1146d89d1bac072f5ab21ad776acad7bc973362998fc96f956d64f63a2'}
CHARTS=[
    ("alanwake2","alan_wake2","high","High",73.6,108.2),
    ("clairobscur33","expedition33","high","Epic",47.6,74.0),
]

def reviewed_charts():
    html=fetch(REVIEW+"3/")
    _,meta=metadata(html,REVIEW+"3/")
    hardware=fetch(REVIEW+"2/")
    if "9800X3D" not in hardware:raise ValueError("Review CPU changed")
    native=[];modes=[]
    for slug,game,preset,label,avg,up in CHARTS:
        url="https://cdn.thefpsreview.com/wp-content/uploads/2025/11/"+slug+"_rtx5070_overclocked-png.webp"
        if url not in html:raise ValueError("Reviewed chart removed")
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as response:
            raw=response.read(2_000_001)
        if hashlib.sha256(raw).hexdigest()!=PINS[slug]:
            raise ValueError("Chart changed; manual review required: "+game)
        row=base_row(meta,raw.hex())
        row.update(game=game,cpu_id="cpu_r7_9800x3d",gpu_id="gpu_rtx5070",
                   reference_cpu="AMD Ryzen 7 9800X3D",resolution="1440",
                   preset=preset,preset_label=label,avg_fps=avg,chart_url=url,
                   evidence_sha256=PINS[slug],collection_method="reviewed_chart_hash",
                   source_section=game,driver="581.80",hardware_source=REVIEW+"2/",
                   workload_note="Stock Founders Edition; manual gameplay; optional hardware RT off",
                   builtin_software_lumen=game=="expedition33")
        native.append(row)
        modes.append(dict(row,avg_fps=up,mode="upscale",label="DLSS Quality",
                          upscaling="DLSS Quality",generated=False,
                          note=label+" · DLSS Quality · RT/FG 끔"))
    return native,modes

ALIASES={
    "witcher3":"The Witcher 3: Wild Hunt","ghost_of_tsushima":"Ghost of Tsushima Director's Cut",
    "horizon_forbidden_west":"Horizon Forbidden West Complete Edition","genshin_impact":"Genshin Impact",
    "dying_light2":"Dying Light 2 Stay Human","fortnite":"Fortnite",
    "cod_black_ops6":"Call of Duty: Black Ops 6","farming_sim":"Farming Simulator 25",
    "msfs2024":"Microsoft Flight Simulator 2024","resident_evil4":"Resident Evil 4",
    "god_of_war_ragnarok":"God of War Ragnarok","wow":"World of Warcraft",
}
def official_support(root):
    data=json.loads(fetch(SUPPORT))
    if not isinstance(data.get("data"),list) or len(data["data"])<100:
        raise ValueError("Changed support schema")
    from server_catalogs import GAME_OPTIONS
    icons=json.loads((root/"data/game_icons.json").read_text(encoding="utf8"))
    canonical=lambda name:normalized(unicodedata.normalize("NFKD", name))
    index={canonical(row["name"]):row for row in data["data"] if row.get("type")=="Game"}
    result={}
    for game in GAME_OPTIONS:
        key=game["id"];name=ALIASES.get(key,icons.get(key,{}).get("name",""))
        name=name.replace("®","").replace("™","").replace("ö","o")
        row=index.get(canonical(name))
        result[key]=dict(dlss=bool(row and row.get("dlss super resolution")),
                        fg=bool(row and row.get("dlss frame generation")),
                        mfg=bool(row and row.get("dlss multi frame generation")),
                        dlss_note=(row or {}).get("dlss super resolution",""),
                        fg_note=(row or {}).get("dlss frame generation",""),
                        mfg_note=(row or {}).get("dlss multi frame generation",""),
                        matched_name=(row or {}).get("name"),source_url=SUPPORT,
                        checked_at=datetime.now(timezone.utc).isoformat())
    return result
