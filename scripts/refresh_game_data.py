"""Collect reviewed game evidence, preserving previous sources on failure.
python scripts/refresh_game_data.py
"""
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server_catalogs import GAME_OPTIONS, GPU_CATALOG

B2G = "https://www.back2gaming.com/review/nvidia-geforce-rtx-5070-founders-edition/"
CSV_URL = "https://www.back2gaming.com/data/GPU/GPUDB-Q1-2025/GPU-DB-Perf-Q1-2025-5070.csv"
GAMES = {
    "DOTA 2": ("dota2", "Very High Preset"),
    "Black Myth: Wukong": ("black_myth_wukong", "Cinematic Preset"),
    "Cyberpunk 2077": ("cyberpunk2077", "Ultra Preset"),
    "F1 24": ("f1_24", "Very High Preset"),
    "Hogwarts Legacy": ("hogwarts_legacy", "Ultra Quality Preset"),
    "The Last of Us Part I": ("the_last_of_us1", "Ultra Settings"),
    "Spider-Man2": ("spider_man2", "Very High Preset"),
    "Ratchet & Clank: Rift Apart": ("ratchet_clank", "Ultra Preset"),
    "Resident Evil 4": ("resident_evil4", "Ultra Preset"),
    "Starfield": ("starfield", "Ultra Preset"),
    "Warhammer 40,000: Space Marine 2": ("space_marine2", "Ultra Preset"),
    "Counter-Strike 2": ("csgo2", "Very High Preset"),
    "PUBG": ("pubg", "Very High Preset"),
    "Rainbow Six Siege": ("rainbow6", "Ultra Preset"),
    "Baldur's Gate 3": ("baldurs_gate3", "Ultra Preset"),
    "Ghost of Tsushima": ("ghost_of_tsushima", "Ultra High Preset"),
    "Horizon Forbidden West": ("horizon_forbidden_west", "Very High Preset"),
    "FlightSimulator2024": ("msfs2024", "Ultra Detail Settings"),
}
GPU_IDS = {row["id"] for row in GPU_CATALOG}
def normalized(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())
GPU_MAP = {
    "rtx4060":"gpu_rtx4060", "rtx4060ti":"gpu_rtx4060ti",
    "rtx4070":"gpu_rtx4070", "rtx4070super":"gpu_rtx4070super",
    "rtx4070sp":"gpu_rtx4070super", "rtx4070tisuper":"gpu_rtx4070tisuper",
    "rtx4070tisp":"gpu_rtx4070tisuper", "rtx5070":"gpu_rtx5070",
    "rtx5070ti":"gpu_rtx5070ti", "rtx5060":"gpu_rtx5060",
    "rtx5060ti16gb":"gpu_rtx5060ti16", "rx9070xt":"gpu_rx9070xt",
}
CPU_MAP = {"Ryzen7 9800X 3D":("cpu_r7_9800x3d","AMD Ryzen 7 9800X3D"),
           "Ryzen7 7800X 3D":("cpu_r7_7800x3d","AMD Ryzen 7 7800X3D"),
           "i9":("cpu_i9_14900k","Intel Core i9-14900K"),
           "i5":("cpu_i5_14400f","Intel Core i5-14400F"),
           "Corei9 14900K":("cpu_i9_14900k","Intel Core i9-14900K"),
           "Corei5 14400F":("cpu_i5_14400f","Intel Core i5-14400F")}
def fetch(url):
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (PCBuilder game data refresh)"}),timeout=30) as response:
        return response.read(8_000_001).decode("utf-8-sig")
def number(value):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value.strip()):
        return None
    value=float(value)
    return value if 0 < value <= 1500 else None
def metadata(html, url):
    soup=BeautifulSoup(html,"html.parser")
    date=None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data=json.loads(script.string or script.get_text())
            candidates=data if isinstance(data,list) else [data]
            for obj in candidates:
                for item in obj.get("@graph",[obj]):
                    if item.get("@type") in ("Article","BlogPosting","NewsArticle","ItemPage"):
                        date=item.get("dateModified") or item.get("datePublished")
        except (ValueError,AttributeError):
            continue
    if not date: raise ValueError("Source publication date missing")
    return soup, {"source_url":url,"source_title":soup.h1.get_text(" ",strip=True),
                  "published_at":date,"game_version":"not reported",
                  "reference_ram":"not reported","collected_at":datetime.now(timezone.utc).isoformat()}
def base_row(meta, evidence):
    return dict(meta, evidence_sha256=hashlib.sha256(evidence.encode()).hexdigest(),
                ray_tracing=False,upscaling="native",frame_generation=False,
                low1_fps=None,chart_url=meta["source_url"],collection_method="reviewed_table",
                reported_precision="source table")
def parse_b2g(html, csv_text):
    soup,meta=metadata(html,B2G)
    text=soup.get_text(" ",strip=True).replace("’","'").replace("”",'"').replace("″",'"')
    for token in ("Ryzen 7 9800X3D","Upscaling technologies are covered in separate articles","Ray tracing has its own dedicated performance section"):
        if token not in text:raise ValueError("Changed benchmark methodology")
    rows=[]
    reader=csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    expected={"Game Name","GPU Name","Average FPS","1% low average FPS","Model","Resolution","Mode"}
    if set(reader.fieldnames or []) != expected:raise ValueError("Changed CSV schema")
    for item in reader:
        if item["Mode"] != "Raster" or item["Game Name"] not in GAMES:continue
        game,preset_label=GAMES[item["Game Name"]]
        # The article's own chart binds the CSV dataset, game, and preset.
        charts=re.findall(r"\[amcharts[^\]]+\]",text)
        if not any('data-game="'+item["Game Name"]+'"' in c and
                   'data-quality="'+preset_label+'"' in c and 'data-mode="Raster"' in c and
                   '/GPU-DB-Perf-Q1-2025-5070.csv' in c for c in charts):
            raise ValueError("Changed chart/preset: "+game)
        gpu="gpu_"+normalized(item["GPU Name"].replace("NVIDIA GeForce ",""))
        if gpu not in GPU_IDS:continue
        resolution={"1920x1080":"1080","2560x1440":"1440","3840x2160":"2160"}.get(item["Resolution"])
        avg,low=number(item["Average FPS"]),number(item["1% low average FPS"])
        if not resolution or avg is None or low is None or low>avg:continue
        row=base_row(meta,json.dumps(item,sort_keys=True))
        row.update(game=game,gpu_id=gpu,cpu_id="cpu_r7_9800x3d",reference_cpu="AMD Ryzen 7 9800X3D",
                   reference_ram="G.Skill DDR5-6000 CL30",resolution=resolution,preset="ultra",
                   preset_label=preset_label,avg_fps=avg,low1_fps=low,source_section=item["Game Name"],
                   source_gpu_model=item["Model"],data_url=CSV_URL,rendering_evidence="Raster CSV + review methodology")
        rows.append(row)
    if not rows:raise ValueError("No validated CSV rows")
    # Prefer the reference Founders Edition over factory-overclocked variants.
    unique={}
    for row in sorted(rows,key=lambda r: "Founders Edition" not in r["source_gpu_model"]):
        key=(row["game"],row["gpu_id"],row["resolution"],row["preset"])
        unique.setdefault(key,row)
    return list(unique.values()),[]

def parse_clockup(html, slug):
    url="https://clockupcore.com/"+slug+"/"
    soup,meta=metadata(html,url)
    rows,pending=[],[]
    if slug in ("zenlesszonezero","wutheringwaves"):
        game={"zenlesszonezero":"zenless_zone_zero","wutheringwaves":"wuthering_waves"}[slug]
        text=soup.get_text(" ",strip=True)
        required="レンダリング" if slug=="zenlesszonezero" else "最高設定"
        if required not in text:raise ValueError("Graphics settings missing")
        for table in soup.find_all("table"):
            header=table.find("thead")
            if not header:continue
            labels=[c.get_text(" ",strip=True) for c in header.select("th")]
            wanted="戦闘1.0" if slug=="zenlesszonezero" else "DLSS無 フレーム生成無"
            if not labels or labels[0]!=wanted:continue
            heading=table.find_previous(["h2","h3"])
            title=heading.get_text(" ",strip=True)
            res=next((r for token,r in [("3840×2160","2160"),("1920×1080","1080"),("2560×1440","1440")] if token in title),None)
            if not res:raise ValueError("Resolution heading missing")
            for tr in table.select("tbody tr"):
                cells=[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"],recursive=False)]
                if len(cells)!=len(labels):raise ValueError("Changed CPU columns")
                gpu=GPU_MAP.get(normalized(cells[0]))
                if not gpu:continue # Never 'correct' RX7080XT or assume unspecified Ti memory.
                for label,cell in zip(labels[1:],cells[1:]):
                    cpu=CPU_MAP.get(label);avg=number(cell)
                    if not cpu or avg is None:continue
                    if cpu[1].split()[-1].replace("-","").lower() not in normalized(text):
                        continue
                    row=base_row(meta,table.get_text(" ",strip=True))
                    row.update(game=game,gpu_id=gpu,cpu_id=cpu[0],reference_cpu=cpu[1],
                               resolution=res,preset="high",preset_label="High / render scale 1.0" if slug=="zenlesszonezero" else "Highest reported raster settings",
                               avg_fps=avg,source_section=title,rendering_evidence=wanted,
                               workload_note="Bringer boss battle" if slug=="zenlesszonezero" else "City traversal; native 120 FPS limit")
                    if slug=="wutheringwaves":
                        # The article does not identify the preset version; capped
                        # results cannot be treated as uncapped hardware capacity.
                        row["exclusion_reason"]="Preset version and native frame cap require validation"
                        pending.append(row)
                    else:rows.append(row)
    else:
        game={"genshinimpact":"genshin_impact","valorant":"valorant","overwatch2":"overwatch2","eldenring":"elden_ring"}[slug]
        for graph in soup.select(".pb-bar-graph"):
            title=graph.get_text(" ",strip=True).split("RTX")[0]
            if not any(t in title for t in ("フルHD","WQHD","4K")):continue
            if "制限解除" in title:continue
            res="2160" if "4K" in title else "1440" if "WQHD" in title else "1080"
            for item in graph.select(".pb-bar-graph__item"):
                name=item.select_one(".pb-bar-graph__label");value=item.select_one(".pb-bar-graph__value")
                if not name or not value:continue
                gpu=GPU_MAP.get(normalized(name.get_text()))
                avg=number(value.get_text().removesuffix("fps"))
                if not gpu or avg is None:continue
                pending.append(dict(meta,game=game,gpu_id=gpu,resolution=res,avg_fps=avg,
                                    source_section=title,evidence_sha256=hashlib.sha256(str(graph).encode()).hexdigest(),
                                    exclusion_reason="Reference CPU or exact preset/rendering conditions not fully reported"))
    if not rows and not pending:raise ValueError("No validated game observations")
    return rows,pending

def merge_source(snapshot,url,rows,pending):
    snapshot["measurements"]=[r for r in snapshot.get("measurements",[]) if r.get("source_url")!=url]+rows
    snapshot["pending_measurements"]=[r for r in snapshot.get("pending_measurements",[]) if r.get("source_url")!=url]+pending

def main():
    path=ROOT/"data/game_benchmarks.json"
    snapshot=json.loads(path.read_text(encoding="utf8"))
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"sources":[]}
    for slug in ["b2g","zenlesszonezero","wutheringwaves","genshinimpact","valorant","overwatch2","eldenring"]:
        url=B2G if slug=="b2g" else "https://clockupcore.com/"+slug+"/"
        try:
            html=fetch(url)
            rows,pending=parse_b2g(html,fetch(CSV_URL)) if slug=="b2g" else parse_clockup(html,slug)
            merge_source(snapshot,url,rows,pending)
            snapshot["sources"]=[s for s in snapshot.get("sources",[]) if s.get("url")!=url]+[{"url":url,"html_sha256":hashlib.sha256(html.encode()).hexdigest(),"collected_at":report["checked_at"]}]
            report["sources"].append({"url":url,"active":len(rows),"pending":len(pending)})
        except (OSError,ValueError) as error:
            report["sources"].append({"url":url,"error":str(error)})
    from scripts.reviewed_game_sources import reviewed_charts, official_support, REVIEW, SUPPORT
    try:
        rows,modes=reviewed_charts()
        merge_source(snapshot,REVIEW+"3/",rows,[])
        snapshot["graphics_measurements"]=[r for r in snapshot.get("graphics_measurements",[]) if r.get("source_url")!=REVIEW+"3/"]+modes
        report["sources"].append({"url":REVIEW+"3/","active":len(rows),"graphics":len(modes)})
    except (OSError,ValueError) as error:
        report["sources"].append({"url":REVIEW+"3/","error":str(error)})
    try:
        snapshot["feature_support"]=official_support(ROOT)
        report["sources"].append({"url":SUPPORT,"matched":sum(bool(r["matched_name"]) for r in snapshot["feature_support"].values())})
    except (OSError,ValueError) as error:
        report["sources"].append({"url":SUPPORT,"error":str(error)})
    snapshot["collected_at"]=report["checked_at"]
    from game_database import save_snapshot
    save_snapshot(snapshot)
    counts={g["id"]:sum(r["game"]==g["id"] for r in snapshot["measurements"]) for g in GAME_OPTIONS}
    report["coverage"]=counts
    snapshot["collected_at"]=report["checked_at"]
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf8");tmp.replace(path)
    (ROOT/"data/game_data_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
