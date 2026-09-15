"""Small, dated Steam survey snapshot used only as a GPU popularity tie-breaker."""
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

SOURCE_URL = "https://store.steampowered.com/hwsurvey/videocard/"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "steam_gpu_usage.json"


def gpu_key(name):
    text = str(name or "").lower()
    if any(token in text for token in ("laptop", "notebook", "mobile")):
        return ""
    match = re.search(r"\b(rtx|gtx|rx)\s*(\d{3,5})\s*(ti\s*super|super|ti|xtx|xt|gre)?\b", text)
    return "".join(match.groups(default="")).replace(" ", "") if match else ""


def parse_steam_survey(html):
    heading = re.search(r"Hardware &amp; Software Survey:\s*([A-Za-z]+)\s+(\d{4})|Hardware & Software Survey:\s*([A-Za-z]+)\s+(\d{4})", html)
    if not heading:
        raise ValueError("Steam survey month was not found")
    month, year = heading.group(1, 2) if heading.group(1) else heading.group(3, 4)
    month_number = datetime.strptime(month, "%B").month
    start = html.index("ALL VIDEO CARDS")
    end_match = re.search(r'class="substats_col_left col_header"[^>]*>DIRECTX', html[start:], re.I)
    section = html[start:start + end_match.start()] if end_match else html[start:]
    rows = re.split(r'<div\s+class="substats_row\s+row_\d+"[^>]*>', section)[1:]
    cards = {}
    for row in rows:
        label = re.search(r'<div\s+class="hws_flex"[^>]*>.*?<span[^>]*>(.*?)</span>', row, re.S)
        value = re.search(r'class="substats_col_month_last_pct"[^>]*>\s*(?:<strong>)?\s*([0-9.]+)%', row)
        if not label or not value:
            continue
        name = unescape(re.sub(r"<[^>]+>", "", label.group(1))).strip()
        key = gpu_key(name)
        if key and key not in cards:
            cards[key] = {"name": name, "share_percent": float(value.group(1))}
    if len(cards) < 10:
        raise ValueError("Steam survey table was incomplete")
    return {
        "source_url": SOURCE_URL,
        "survey_month": f"{year}-{month_number:02d}",
        "survey_label": f"{year}년 {month_number}월",
        "population": "Steam 하드웨어 설문 참여 사용자 · 전체 그래픽카드 표",
        "note": "전체 PC 사용자의 전수 통계가 아니며, 점유율은 성능 지표가 아닙니다. 노트북 GPU는 데스크톱 추천에서 제외합니다.",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cards": cards,
    }


def _load_snapshot():
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"source_url": SOURCE_URL, "cards": {}}


_SNAPSHOT = _load_snapshot()


def steam_gpu_share(name):
    return float(_SNAPSHOT.get("cards", {}).get(gpu_key(name), {}).get("share_percent", 0.0))


def steam_survey_metadata():
    return {key: value for key, value in _SNAPSHOT.items() if key != "cards"}


if __name__ == "__main__":
    # Deliberately manual: recommendation requests never wait for Steam.
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=10) as response:
        snapshot = parse_steam_survey(response.read().decode("utf-8"))
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(snapshot['cards'])} desktop GPU usage rows ({snapshot['survey_month']})")
