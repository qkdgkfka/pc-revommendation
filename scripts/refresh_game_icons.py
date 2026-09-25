"""Download game artwork from their store/publisher, retaining a provenance manifest."""
import concurrent.futures
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
STEAM={
    "dota2":570,
    "f1_24":2488620,
    "the_last_of_us1":1888930,
    "spider_man2":2651280,
    "ratchet_clank":1895880,
    "space_marine2":2183900,
    "expedition33":1903340,

"csgo2":730,"overwatch2":2357570,"apex":1172470,"rainbow6":359550,"pubg":578080,
"cyberpunk2077":1091500,"baldurs_gate3":1086940,"god_of_war_ragnarok":2322010,
"black_myth_wukong":2358720,"witcher3":292030,"elden_ring":1245620,
"ghost_of_tsushima":2215430,"red_dead_redemption2":1174180,"horizon_forbidden_west":2420110,
"hogwarts_legacy":990080,"starfield":1716740,"wuthering_waves":3513350,
"lostark":1599340,"ffxiv":39210,"cities_skylines2":949230,"msfs2024":2537590,
"farming_sim":2300320,"marvel_rivals":2767030,"cod_black_ops6":2933620,
"dragons_dogma2":2054970,"dying_light2":534380,"resident_evil4":2050650,
}
PAGES={"valorant":"https://playvalorant.com/en-us/","csgo":"https://blog.counter-strike.net/",
       "wow":"https://worldofwarcraft.blizzard.com/en-us/","fortnite":"https://store.epicgames.com/en-US/p/fortnite",
       "alan_wake2":"https://www.alanwake.com/"}
APPLE={"genshin_impact":1517783697,"zenless_zone_zero":1606356401}
def fetch(url):
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=25) as r:return r.read(8_000_001)
DIRECT={
"fortnite":("https://www.fortnite.com/","https://cdn2.unrealengine.com/links-admin-FNECO_42-10_Tailgate_Keyart_DiscoverTile_480x270-4bceb7c5.jpg","Fortnite Battle Royale"),
"cod_black_ops6":("https://www.callofduty.com/en/store/games/blackops6","https://www.callofduty.com/content/dam/atvi/callofduty/cod-touchui/store/games/bo6/BO6_Banner.webp?imwidth=828","Call of Duty Black Ops 6"),
}
def collect(game):
    if game in DIRECT:
        page,url,name=DIRECT[game]
    elif game in STEAM:
        page="https://store.steampowered.com/app/"+str(STEAM[game])+"/"
        api="https://store.steampowered.com/api/appdetails?appids="+str(STEAM[game])+"&l=english&cc=us"
        response=next((r for r in json.loads(fetch(api)).values() if r.get("data",{}).get("steam_appid")==STEAM[game]),{})
        if not response.get("success"):raise ValueError("Store unavailable")
        data=response["data"];url=data["header_image"];name=data["name"]
    elif game in APPLE:
        page="https://apps.apple.com/app/id"+str(APPLE[game])
        data=json.loads(fetch("https://itunes.apple.com/lookup?id="+str(APPLE[game])))["results"][0]
        url=data["artworkUrl100"];name=data["trackName"]
    else:
        page=PAGES[game];s=BeautifulSoup(fetch(page),"html.parser")
        icon=s.find("link",rel=lambda x:x and "icon" in x)
        og=s.find("meta",property="og:image")
        url=urljoin(page,icon["href"] if icon and icon.get("href") else og["content"])
        name=s.title.get_text(strip=True)
    raw=fetch(url)
    with Image.open(io.BytesIO(raw)) as im:
        if im.width<16 or im.height<16:raise ValueError("Image too small")
        im=im.convert("RGBA");background=Image.new("RGBA",im.size,"white");background.alpha_composite(im);im=background.convert("RGB");im.thumbnail((144,96))
        im.save(ROOT/"assets/game-icons"/(game+".jpg"),quality=88)
    return game,{"name":name,"source_url":page,"image_url":url,"sha256":hashlib.sha256(raw).hexdigest(),"checked_at":datetime.now(timezone.utc).isoformat()}
def main():
    folder=ROOT/"assets/game-icons";folder.mkdir(parents=True,exist_ok=True)
    manifest_path=ROOT/"data/game_icons.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf8")) if manifest_path.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        pending={ex.submit(collect,game):game for game in [*STEAM,*PAGES,*APPLE]}
        for future in concurrent.futures.as_completed(pending):
            game=pending[future]
            try:
                _,record=future.result();manifest[game]=record;print(game,record["name"])
            except Exception as error:print(game,"FAILED",str(error))
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
if __name__=="__main__":
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf8")
    main()
