"""Refresh reviewed SR/FG pairs independently of the native benchmark database."""
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CB = "https://www.computerbase.de/artikel/grafikkarten/amd-fsr-nvidia-dlss-frame-generation-vergleich.86978/"
CB5090 = "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5090-test.91081/seite-8"
CB5060 = "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/seite-6"
AMD = "https://www.amd.com/en/products/graphics/technologies/fidelityfx/supported-games.html"


def average_values(chart):
    group = chart.select_one(".chart__group")
    heading = group.select_one(".chart__group-header") if group else None
    if not heading or "Durchschnitt" not in heading.get_text():
        raise ValueError("Average chart schema changed")
    return {row.select_one(".chart__item").get_text(" ", strip=True):
            float(row.select_one("[data-value]")["data-value"])
            for row in group.select(".chart__row")}


def chart_metadata(chart, url, game, resolution, conditions):
    return dict(game=game, resolution=resolution, source_url=url,
                source_section=chart["data-title"], conditions=conditions,
                evidence_sha256=hashlib.sha256(str(chart).encode()).hexdigest(),
                collected_at=datetime.now(timezone.utc).isoformat(),
                metric="average display FPS", usage="relative paired calibration; not an exact target measurement")


def paired_charts(raw):
    fg, upscale = [], []
    games = {"Like a Dragon: Infinite Wealth": "like_a_dragon_infinite_wealth",
             "Starfield": "starfield", "The Talos Principle 2": "talos_principle2",
             "COD: Modern Warfare 3": "cod_mw3"}
    for chart in BeautifulSoup(raw, "html.parser").select(".chart[data-title]"):
        title = chart["data-title"]
        game = next((key for name, key in games.items() if title.startswith(name + " –")), None)
        if game is None or not title.endswith("AVG-FPS"):
            continue
        values = average_values(chart)
        meta = chart_metadata(chart, CB, game, "2160", "Same reviewed 4K scene; Quality SR; source game settings")
        for gpu, name, tech in [("gpu_rx7800xt", "RX 7800 XT", "FSR"), ("gpu_rtx4070", "RTX 4070", "DLSS")]:
            prefix = name + " @ " + tech + " SR Q"
            if prefix not in values:
                continue
            pair = dict(meta, gpu_id=gpu, technology=tech, quality="Quality",
                        technology_version="FSR 3" if tech == "FSR" else "DLSS 3")
            upscale.append(dict(pair, native_fps=values[name + " @ Nativ"], upscale_fps=values[prefix]))
            if prefix + " + FG" in values:
                fg.append(dict(pair, factor=2, base_fps=values[prefix], display_fps=values[prefix + " + FG"]))
    if len(fg) != 7 or len(upscale) != 7:
        raise ValueError("Reviewed DLSS3/FSR3 chart coverage changed")
    return fg, upscale


def dlss4_pairs(raw, url):
    """Use explicit FG/MFG labels from a common SR(+RR) baseline, averages only."""
    games = {"Alan Wake 2": "alan_wake2", "Cyberpunk 2077": "cyberpunk2077",
             "Star Wars: Outlaws": "star_wars_outlaws", "Doom: The Dark Ages": "doom_the_dark_ages"}
    rows = []
    for chart in BeautifulSoup(raw, "html.parser").select(".chart[data-title]"):
        title = chart["data-title"]
        game = next((key for name, key in games.items() if title.startswith(name + ",")), None)
        if (game is None or "DLSS 4 MFG –" not in title
                or not re.search(r"– (?:3\.840 × 2\.160|1\.920 × 1\.080)$", title)):
            continue
        values = average_values(chart)
        values = {re.sub(r"\s+", " ", key): value for key, value in values.items()}
        doom = game == "doom_the_dark_ages"
        meta = chart_metadata(chart, url, game, "1080" if doom else "2160",
            "DLSS 4 Quality; mandatory RT; lowest textures" if doom else
            "DLSS 4 SR + RR; source ray-tracing workload; SR quality not specified on chart")
        meta.update(technology="DLSS", quality="Quality" if doom else "unspecified", ray_tracing=True)
        for gpu, name in ([("gpu_rtx5060", "RTX 5060")] if doom else
                          [("gpu_rtx5090", "5090"), ("gpu_rtx4090", "4090")]):
            prefix = name + (" @ DLSS 4 SR Q" if doom else " @ DLSS 4 SR + RR")
            if prefix not in values:
                continue
            for factor, suffix in [(2, " + FG"), (3, " + MFG 3×"), (4, " + MFG 4×")]:
                if prefix + suffix in values:
                    rows.append(dict(meta, gpu_id=gpu, factor=factor, base_fps=values[prefix],
                                     display_fps=values[prefix + suffix]))
    return rows


def amd_support(raw):
    from server_catalogs import GAME_OPTIONS
    from scripts.reviewed_game_sources import ALIASES
    icons = json.loads((ROOT / "data/game_icons.json").read_text(encoding="utf8"))

    def key(name):
        return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).lower())

    tables = {}
    for table in BeautifulSoup(raw, "html.parser").select("table"):
        heading = table.find_previous(["h2", "h3", "h4"])
        heading = heading.get_text(" ", strip=True) if heading else ""
        if "FSR" in heading:
            tables[heading] = {key(cell.get_text(" ", strip=True)) for cell in table.select("td")}
    if not any(re.search(r"FSR.*\b3\b", heading) for heading in tables):
        raise ValueError("AMD support schema changed")
    aliases = {"dying_light2": "Dying Light 2 Stay Human: Reloaded Edition",
               "witcher3": "The Witcher 3: Wild Hunt", "god_of_war_ragnarok": "God of War Ragnarök"}
    result = {}
    for game in GAME_OPTIONS:
        gid = game["id"]
        name = aliases.get(gid, ALIASES.get(gid, icons.get(gid, {}).get("name", "")))
        matches = [heading for heading, names in tables.items() if key(name) in names]
        versions = [int(match[1]) for heading in matches
                    if (match := re.search(r"FSR[^\d]*([123])\b", heading))]
        # ML/Redstone support is a separate workload, not an FSR3 coefficient.
        result[gid] = dict(fsr=bool(versions), fg=3 in versions,
            version="FSR " + str(max(versions)) if versions else None,
            matched_name=name if matches else None, source_url=AMD,
            ml_upscale=any("Redstone" in heading for heading in matches),
            ml_fg=any("Frame Generation" in heading for heading in matches),
            checked_at=datetime.now(timezone.utc).isoformat())
    return result


def main(argv=None):
    import argparse
    from rendering_calibration import CALIBRATION_PATH, snapshot_quality_pairs
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached-dir", type=Path)
    parser.add_argument("--output", type=Path, default=CALIBRATION_PATH)
    args = parser.parse_args(argv)
    sources = []

    def fetch(name, url):
        if args.cached_dir:
            raw = (args.cached_dir / (name + ".html")).read_bytes()
        else:
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
                raw = response.read()
        sources.append({"url": url, "html_sha256": hashlib.sha256(raw).hexdigest()})
        return raw

    fg, upscale = paired_charts(fetch("cbfsr", CB))
    dlss4 = dlss4_pairs(fetch("cb5090", CB5090), CB5090)
    doom = dlss4_pairs(fetch("cb5060", CB5060), CB5060)
    if len(dlss4) != 12 or len(doom) != 3:
        raise ValueError("Reviewed DLSS4 chart coverage changed; keep previous file")
    support = amd_support(fetch("amdsupport", AMD))
    snapshot = json.loads((ROOT / "data/game_benchmarks.json").read_text(encoding="utf8"))
    upscale.extend(snapshot_quality_pairs(snapshot))
    data = dict(schema_version=1, collected_at=datetime.now(timezone.utc).isoformat(), sources=sources,
                fg_calibration=dlss4 + doom + fg, upscale_calibration=upscale, fsr_support=support)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "fg_pairs": len(data["fg_calibration"]),
                      "upscale_pairs": len(upscale), "fsr_games": sum(row["fsr"] for row in support.values())}))


if __name__ == "__main__":
    main()
