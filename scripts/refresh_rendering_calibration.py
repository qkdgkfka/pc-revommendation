"""Reviewed paired charts: extract averages only; never promote them to native FPS."""
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
CB="https://www.computerbase.de/artikel/grafikkarten/amd-fsr-nvidia-dlss-frame-generation-vergleich.86978/"
AMD="https://www.amd.com/en/products/graphics/technologies/fidelityfx/supported-games.html"

def paired_charts(raw):
    soup=BeautifulSoup(raw,"html.parser")
    fg,up=[],[]
    games={"Like a Dragon: Infinite Wealth":"like_a_dragon_infinite_wealth",
           "Starfield":"starfield","The Talos Principle 2":"talos_principle2",
           "COD: Modern Warfare 3":"cod_mw3"}
    for chart in soup.select(".chart[data-title]"):
        title=chart["data-title"]
        if not title.endswith("AVG-FPS"):continue
        game=next((key for name,key in games.items() if title.startswith(name+" –")),None)
        if game is None:continue
        group=chart.select_one(".chart__group")
        if not group or "Durchschnitt" not in group.select_one(".chart__group-header").get_text():
            raise ValueError("Average chart schema changed")
        values={r.select_one(".chart__item").get_text(" ",strip=True):
                float(r.select_one("[data-value]")["data-value"]) for r in group.select(".chart__row")}
        meta=dict(game=game,resolution="2160",source_url=CB,source_section=title,
                  evidence_sha256=hashlib.sha256(str(chart).encode()).hexdigest(),
                  collected_at=datetime.now(timezone.utc).isoformat(),
                  conditions="Same reviewed 4K scene; Quality SR; source game settings",
                  usage="relative paired calibration; not an exact target-configuration measurement")
        for gpu,name,tech in [("gpu_rx7800xt","RX 7800 XT","FSR"),("gpu_rtx4070","RTX 4070","DLSS")]:
            prefix=name+" @ "+tech+" SR Q"
            if prefix not in values:continue
            base=values[prefix]
            up.append(dict(meta,gpu_id=gpu,technology=tech,native_fps=values[name+" @ Nativ"],upscale_fps=base))
            if prefix+" + FG" in values:
                fg.append(dict(meta,gpu_id=gpu,technology=tech,factor=2,base_fps=base,display_fps=values[prefix+" + FG"]))
    if len(fg)!=7 or len(up)!=7:raise ValueError("Reviewed chart coverage changed")
    return fg,up

def amd_support(raw):
    from server_catalogs import GAME_OPTIONS
    from scripts.reviewed_game_sources import ALIASES
    icons=json.loads((ROOT/"data/game_icons.json").read_text(encoding="utf8"))
    def key(s):
        return re.sub(r"[^a-z0-9]","",unicodedata.normalize("NFKD",s).lower())
    tables={}
    for table in BeautifulSoup(raw,"html.parser").select("table"):
        heading=table.find_previous(["h2","h3","h4"]).get_text(" ",strip=True)
        if "FSR" not in heading:continue
        tables[heading]={key(td.get_text(" ",strip=True)) for td in table.select("td")}
    if not any("3" in h for h in tables):raise ValueError("AMD support schema changed")
    aliases={"dying_light2":"Dying Light 2 Stay Human: Reloaded Edition",
             "witcher3":"The Witcher 3: Wild Hunt","god_of_war_ragnarok":"God of War Ragnarök"}
    result={}
    for game in GAME_OPTIONS:
        gid=game["id"]
        name=aliases.get(gid,ALIASES.get(gid,icons.get(gid,{}).get("name","")))
        matches=[h for h,names in tables.items() if key(name) in names]
        sr=any(any(v in h for v in ("1","2","3","Redstone")) for h in matches)
        fg=any("3" in h or "Frame Generation" in h for h in matches)
        result[gid]=dict(fsr=sr,fg=fg,version="FSR 3" if fg else "FSR 2" if any("2" in h for h in matches) else "FSR 1",
                        matched_name=name if matches else None,source_url=AMD,
                        checked_at=datetime.now(timezone.utc).isoformat())
    return result

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--cached-dir",type=Path)
    args=parser.parse_args()
    def fetch(name,url):
        if args.cached_dir:return (args.cached_dir/(name+".html")).read_bytes()
        return urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read()
    fg,up=paired_charts(fetch("cbfsr",CB))
    support=amd_support(fetch("amdsupport",AMD))
    path=ROOT/"data/game_benchmarks.json"
    snapshot=json.loads(path.read_text(encoding="utf8"))
    snapshot["fg_calibration"]=[dict(r,technology=r.get("technology","DLSS")) for r in snapshot.get("fg_calibration",[]) if r["source_url"]!=CB]+fg
    snapshot["upscale_calibration"]=up
    # Existing reviewed native/Quality pairs are independently useful SR anchors.
    for row in snapshot.get("graphics_measurements",[]):
        if row.get("mode")!="upscale" or row.get("generated"):continue
        native=next((n for n in snapshot["measurements"] if all(n.get(k)==row.get(k) for k in
                    ("game","gpu_id","cpu_id","resolution","preset","source_url"))),None)
        if native:
            snapshot["upscale_calibration"].append(dict(row,technology="DLSS",
                 native_fps=native["avg_fps"],upscale_fps=row["avg_fps"]))
    snapshot["fsr_support"]=support
    from game_database import save_snapshot
    save_snapshot(snapshot)
    path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"fg_pairs":len(snapshot["fg_calibration"]),"upscale_pairs":len(snapshot["upscale_calibration"]),
                      "fsr_games":sum(r["fsr"] for r in support.values())}))
if __name__=="__main__":main()
