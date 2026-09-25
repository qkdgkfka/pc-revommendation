"""Refresh reviewed, native-rendering game measurements; never writes pc.db.

Run: python crawl_game_benchmarks.py
Only explicit FPS statements in reviewed article sections are extracted. Chart
filenames verify the preset; RT/upscaling sections are excluded. A changed page
or missing measurement fails closed and leaves the existing snapshot intact.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

GN_URL = "https://gamersnexus.net/gpus/nvidia-selling-lies-rtx-5070-founders-edition-review-benchmarks"
GEEK_URL = "https://geekawhat.com/nvidia-geforce-rtx-5070-review/"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "game_benchmarks.json"

# Each rule identifies a single GPU and a single reported AVG FPS, not a
# percentage comparison, chart OCR guess, generated frame rate, or GPU index.
GN_RULES = [
    ("FFXIV 4K", "ffxiv", "2160", "ultra", "Maximum", "gpu_rtx5070", r"RTX 5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("FFXIV 1440p", "ffxiv", "1440", "ultra", "Maximum", "gpu_rtx4080super", r"4080 Super at (\d+(?:\.\d+)?) FPS"),
    ("FFXIV 1440p", "ffxiv", "1440", "ultra", "Maximum", "gpu_rtx4070", r"4070 FE at (\d+(?:\.\d+)?) FPS"),
    ("FFXIV 1080p", "ffxiv", "1080", "ultra", "Maximum", "gpu_rtx5070", r"5070 ran this workload at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 4K", "black_myth_wukong", "2160", "high", "High", "gpu_rtx5070", r"5070 at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 1440p", "black_myth_wukong", "1440", "high", "High", "gpu_rtx5070", r"5070 FE ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 1080p", "black_myth_wukong", "1080", "high", "High", "gpu_rtx5070", r"5070 down at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 4K", "starfield", "2160", "ultra", "Ultra", "gpu_rtx5070", r"RTX 5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 4K", "starfield", "2160", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti[^.]*?running a (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 4K", "starfield", "2160", "ultra", "Ultra", "gpu_rtx4070ti", r"4070 Ti.s (\d+(?:\.\d+)?) FPS"),
    ("Starfield - 1440p", "starfield", "1440", "ultra", "Ultra", "gpu_rtx5070", r"RTX 5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 1440p", "starfield", "1440", "ultra", "Ultra", "gpu_rx7900xt", r"7900 XT.{0,180}?runs at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 1080p", "starfield", "1080", "ultra", "Ultra", "gpu_rtx5070", r"5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Dragon’s Dogma 2 - 4K", "dragons_dogma2", "2160", "ultra", "Max", "gpu_rtx5070", r"RTX 5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Dragon’s Dogma 2 - 4K", "dragons_dogma2", "2160", "ultra", "Max", "gpu_rtx4090", r"RTX 4090, which is up at (\d+(?:\.\d+)?) FPS"),
    ("Dragon’s Dogma 2 - 4K", "dragons_dogma2", "2160", "ultra", "Max", "gpu_rx7900xt", r"7900 XT held a (\d+(?:\.\d+)?) FPS AVG"),
    ("Dragon’s Dogma 2 - 1440p", "dragons_dogma2", "1440", "ultra", "Max", "gpu_rx7900xt", r"7900 XT.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Dragon’s Dogma 2 - 1080p", "dragons_dogma2", "1080", "ultra", "Max", "gpu_rtx5070", r"5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Dragon’s Dogma 2 - 1080p", "dragons_dogma2", "1080", "ultra", "Max", "gpu_rtx5070ti", r"5070 Ti.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 4K", "cyberpunk2077", "2160", "ultra", "Ultra", "gpu_rtx5070", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 4K", "cyberpunk2077", "2160", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti, its (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 4K", "cyberpunk2077", "2160", "ultra", "Ultra", "gpu_rx7900xtx", r"7900 XTX.{0,70}?ahead of that at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1440p", "cyberpunk2077", "1440", "ultra", "Ultra", "gpu_rtx5070", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1440p", "cyberpunk2077", "1440", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti at (\d+(?:\.\d+)?) FPS"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rtx5070", r"with the 5070 at (\d+(?:\.\d+)?)"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rx7900xt", r"This one ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Dying Light 2 - 4K", "dying_light2", "2160", "high", "High-Custom", "gpu_rtx5070", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Dying Light 2 - 4K", "dying_light2", "2160", "high", "High-Custom", "gpu_rx7900xt", r"7900 XT.{0,70}?at (\d+(?:\.\d+)?) FPS AVG itself"),
    ("Dying Light 2 - 1440p", "dying_light2", "1440", "high", "High-Custom", "gpu_rtx5070", r"5070 at (\d+(?:\.\d+)?) FPS AVG"),
    ("Dying Light 2 - 1440p", "dying_light2", "1440", "high", "High-Custom", "gpu_rtx4070", r"4070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 4K", "resident_evil4", "2160", "high", "Prioritize Graphics", "gpu_rtx5070", r"5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 4K", "resident_evil4", "2160", "high", "Prioritize Graphics", "gpu_rtx5070ti", r"5070 Ti.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 4K", "resident_evil4", "2160", "high", "Prioritize Graphics", "gpu_rx7900xt", r"7900 XT.{0,70}?landing at (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 1440p", "resident_evil4", "1440", "high", "Prioritize Graphics", "gpu_rtx5070", r"5070 held a (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 1440p", "resident_evil4", "1440", "high", "Prioritize Graphics", "gpu_rx7900xt", r"7900 XT is now up at (\d+(?:\.\d+)?) FPS AVG"),
    ("Resident Evil 4 - 1440p", "resident_evil4", "1440", "high", "Prioritize Graphics", "gpu_rtx4070", r"(\d+(?:\.\d+)?) FPS on the 4070"),
    ("Resident Evil 4 - 1080p", "resident_evil4", "1080", "high", "Prioritize Graphics", "gpu_rtx5070", r"5070 and 5070 Ti, which now ranges from 282 FPS to (\d+(?:\.\d+)?) FPS"),
    ("Resident Evil 4 - 1080p", "resident_evil4", "1080", "high", "Prioritize Graphics", "gpu_rtx5070ti", r"5070 and 5070 Ti, which now ranges from (\d+(?:\.\d+)?) FPS to 224 FPS"),
]

# Native and generated results coexist in these sections. A reviewed chart
# caption and the exact native-result sentence must both be present.
GEEK_RULES = [
    ("Cyberpunk 2077", "cyberpunk2077", "2160", "high", "High", "gpu_rtx5070", "Cyberpunk 2077 @ 4K High, Rasterisation Only", r"RTX 5070 sits at a reasonably low (\d+(?:\.\d+)?)FPS"),
    ("Alan Wake 2", "alan_wake2", "2160", "high", "High", "gpu_rtx5070", "Alan Wake 2 @ 4K High, Rasterisation Only", r"RTX 5070 offered an average framerate of (\d+(?:\.\d+)?)FPS"),
    ("Hogwarts Legacy", "hogwarts_legacy", "1440", "high", "High", "gpu_rtx5070", "Hogwarts Legacy @ 1440p High, Rasterisation", r"RTX 5070 offered an output of (\d+(?:\.\d+)?)FPS"),
    ("Marvel Rivals", "marvel_rivals", "1440", "high", "High", "gpu_rtx5070", "Marvel Rivals @ 1440p High, Rasterisation Only", r"RTX 5070 sits.{0,70}?outputting (\d+(?:\.\d+)?)FPS on average"),
    ("COD Black Ops 6", "cod_black_ops6", "1440", "high", "High Custom · Zombies", "gpu_rtx5070", "COD Black Ops 6 (Zombies) @ 1440p High, Rasterisation Only", r"average of (\d+(?:\.\d+)?)FPS from the RTX 5070"),
    ("COD Black Ops 6", "cod_black_ops6", "1440", "high", "High Custom · Zombies", "gpu_rtx4070super", "COD Black Ops 6 (Zombies) @ 1440p High, Rasterisation Only", r"RTX 4070 SUPER sitting at (\d+(?:\.\d+)?)FPS"),
    ("Apex Legends", "apex", "1440", "high", "High", "gpu_rtx5070", "Apex Legends @ 1440p High", r"5070 held firmly at (\d+(?:\.\d+)?)FPS"),
    ("Fortnite", "fortnite", "1080", "low", "Competitive · TAA · Far View Distance", "gpu_rtx5070", "Fortnite @ 1080p Competitive", r"RTX 5070 in this run.{0,120}?monstrous (\d+(?:\.\d+)?)FPS"),
    ("Fortnite", "fortnite", "1080", "low", "Competitive · TAA · Far View Distance", "gpu_rtx4070super", "Fortnite @ 1080p Competitive", r"RTX 4070 SUPER sits.{0,100}?output of (\d+(?:\.\d+)?)FPS"),
]


def section(soup, title):
    headings = [h for h in soup.find_all(["h3", "h4"]) if h.get_text(" ", strip=True) == title]
    if len(headings) != 1:
        raise ValueError(f"Expected one benchmark section: {title}, got {len(headings)}")
    heading = headings[0]
    nodes = []
    for sibling in heading.next_siblings:
        if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
            break
        nodes.append(str(sibling))
    fragment = BeautifulSoup("".join(nodes), "html.parser")
    return fragment, re.sub(r"\s+", " ", fragment.get_text(" ", strip=True))


def measurement(text, pattern):
    matches = re.findall(pattern, text, flags=re.I)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one measurement for {pattern!r}, got {matches!r}")
    value = float(matches[0])
    if not 1 <= value <= 1500:
        raise ValueError("FPS outside reviewed range")
    return value


def parse_gn(html):
    soup = BeautifulSoup(html, "html.parser")
    if "9800X3D" not in soup.get_text():
        raise ValueError("Reference CPU cannot be verified")
    rows = []
    for title, game, resolution, preset, preset_label, gpu, pattern in GN_RULES:
        fragment, body = section(soup, title)
        heading = next(h for h in soup.find_all("h4") if h.get_text(" ", strip=True) == title)
        group = heading.find_previous("h3")
        if group is None or group.get_text(" ", strip=True) != "RTX 5070 Benchmarks":
            raise ValueError(f"Benchmark is outside the reviewed native-rendering group: {title}")
        chart_resolution = "4K" if resolution == "2160" else resolution + "p"
        chart = next((i.get("src") for i in fragment.find_all("img")
                      if f"({chart_resolution}_{preset_label})" in unquote(i.get("src", ""))), None)
        if not chart:
            raise ValueError(f"Unverified native preset chart: {title}")
        low = None
        if game == "cyberpunk2077" and resolution == "1440" and gpu == "gpu_rtx5070":
            low = measurement(body, r"lows at (\d+(?:\.\d+)?) FPS 1%")
        rows.append({
            "game": game, "gpu_id": gpu, "cpu_id": "cpu_r7_9800x3d",
            "reference_cpu": "AMD Ryzen 7 9800X3D", "resolution": resolution,
            "preset": preset, "preset_label": preset_label,
            "avg_fps": measurement(body, pattern), "low1_fps": low,
            "ray_tracing": False, "upscaling": "native", "frame_generation": False,
            "game_version": "2.21 / Phantom Liberty" if game == "cyberpunk2077" else "Dawntrail" if game == "ffxiv" else "not reported",
            "reference_ram": "not reported in article text", "published_at": "2025-03-13",
            "source_title": "GamersNexus RTX 5070 Founders Edition Review",
            "source_url": GN_URL, "chart_url": urljoin(GN_URL, chart),
            "source_section": title, "evidence_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "collection_method": "reviewed_section_regex", "reported_precision": "rounded article FPS",
            "rendering_evidence": "Native raster benchmark group; resolution and preset verified from chart filename",
            "workload_note": "GPU test area; city CPU load can differ" if game == "dragons_dogma2" else "",
        })
    return rows


def parse_geek(html):
    soup = BeautifulSoup(html, "html.parser")
    if "AMD Ryzen 7 9800X3D" not in soup.get_text(" "):
        raise ValueError("Reference CPU cannot be verified")
    rows = []
    for title, game, resolution, preset, preset_label, gpu, chart_label, pattern in GEEK_RULES:
        fragment, body = section(soup, title)
        chart_resolution = "4K" if resolution == "2160" else resolution + "p"
        if chart_resolution not in body or ("Competitive" if preset == "low" else "High") not in body:
            raise ValueError(f"Unverified settings in {title}")
        charts = [i for i in fragment.find_all("img") if i.get("alt", "").startswith(chart_label)]
        if len(charts) != 1 or not charts[0].get("src"):
            raise ValueError(f"Expected one reviewed native chart in {title}")
        # These same sections also discuss DLSS/FSR and generated FPS. Never
        # accept those images as evidence for the native measurements.
        if re.search(r"DLSS|FSR|Frame Gen|Ray Tracing", charts[0].get("alt", ""), re.I):
            raise ValueError(f"Generated/upscaled chart cannot support native FPS: {title}")
        rows.append({
            "game": game, "gpu_id": gpu, "cpu_id": "cpu_r7_9800x3d",
            "reference_cpu": "AMD Ryzen 7 9800X3D", "resolution": resolution,
            "preset": preset, "preset_label": preset_label + " (article settings)",
            "avg_fps": measurement(body, pattern), "low1_fps": None,
            "ray_tracing": False, "upscaling": "native", "frame_generation": False,
            "game_version": "not reported", "reference_ram": "not reported in article text",
            "published_at": "2025-03-04", "source_title": "GeekaWhat NVIDIA GeForce RTX 5070 Review",
            "source_url": GEEK_URL, "chart_url": urljoin(GEEK_URL, charts[0]["src"]), "source_section": title,
            "evidence_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "collection_method": "reviewed_section_regex", "reported_precision": "rounded article FPS",
            "rendering_evidence": "Native result sentence with matching reviewed chart caption",
            "workload_note": "Zombies mode; multiplayer maps can differ" if game == "cod_black_ops6" else "Competitive custom settings with TAA; view distance Far" if game == "fortnite" else "",
        })
    return rows


def parse_graphics_modes(gn_html, geek_html):
    """Keep RT/generated measurements separate from the native FPS table."""
    rows = []
    gn = BeautifulSoup(gn_html, "html.parser")
    geek = BeautifulSoup(geek_html, "html.parser")
    rules = [
        (gn, GN_URL, "Ray Tracing - Cyberpunk 4K RT Ultra", "cyberpunk2077", "2160", "ultra", "rt", "RT Ultra · Native", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG", False),
        (gn, GN_URL, "Ray Tracing - Cyberpunk 1080p RT Ultra", "cyberpunk2077", "1080", "ultra", "rt", "RT Ultra · Native", r"5070 held (\d+(?:\.\d+)?) FPS AVG", False),
        (geek, GEEK_URL, "Hogwarts Legacy", "hogwarts_legacy", "1440", "high", "upscale_fg_measured", "DLSS + FG · 원문 High 설정", r"framerates surged up to (\d+(?:\.\d+)?)FPS", True),
        (geek, GEEK_URL, "Marvel Rivals", "marvel_rivals", "1440", "high", "upscale_fg_measured", "DLSS + FG · 원문 High 설정", r"5070 jumped to a (\d+(?:\.\d+)?)FPS average", True),
        (geek, GEEK_URL, "Alan Wake 2", "alan_wake2", "2160", "high", "rt_upscale_fg_measured", "RT High + DLSS + FG · 원문 설정", r"with an average of (\d+(?:\.\d+)?)FPS", True),
    ]
    for soup, url, title, game, resolution, preset, mode, label, pattern, generated in rules:
        _, body = section(soup, title)
        rows.append({"game": game, "resolution": resolution, "preset": preset,
                     "gpu_id": "gpu_rtx5070", "cpu_id": "cpu_r7_9800x3d", "mode": mode,
                     "label": label, "avg_fps": measurement(body, pattern), "generated": generated,
                     "source_url": url, "source_section": title,
                     "evidence_sha256": hashlib.sha256(body.encode()).hexdigest(),
                     "note": "원문 DLSS 품질·FG 배율 미기재" if generated else "프레임 생성·업스케일링 OFF"})
    return rows


def crawl(output=DEFAULT_OUTPUT):
    rows, sources = [], []
    pages = []
    for url, parser in [(GN_URL, parse_gn), (GEEK_URL, parse_geek)]:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PCBuilderBenchmark/1.0)", "Accept": "text/html"})
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
        rows.extend(parser(html))
        pages.append(html)
        sources.append({"url": url, "html_sha256": hashlib.sha256(html.encode()).hexdigest()})
    snapshot = {"schema_version": 1, "collected_at": datetime.now(timezone.utc).isoformat(),
                "sources": sources, "measurements": rows,
                "graphics_measurements": parse_graphics_modes(*pages)}
    output = Path(output)
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        refreshed = {GN_URL, GEEK_URL}
        snapshot["measurements"].extend(r for r in previous.get("measurements", [])
                                        if r.get("source_url") not in refreshed)
        snapshot["sources"].extend(r for r in previous.get("sources", []) if r.get("url") not in refreshed)
        snapshot["pending_measurements"] = previous.get("pending_measurements", [])
        snapshot["graphics_measurements"].extend(r for r in previous.get("graphics_measurements", []) if r.get("source_url") not in refreshed)
        snapshot["feature_support"] = previous.get("feature_support", {})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    if output.resolve() == DEFAULT_OUTPUT.resolve():
        from game_database import save_snapshot
        save_snapshot(snapshot)
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = crawl(args.output)
    print(f"Collected {len(result['measurements'])} verified measurements from {len(result['sources'])} sources: {args.output}")
