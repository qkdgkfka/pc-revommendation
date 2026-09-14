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
    ("FFXIV 1080p", "ffxiv", "1080", "ultra", "Maximum", "gpu_rtx5070", r"5070 ran this workload at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 4K", "black_myth_wukong", "2160", "high", "High", "gpu_rtx5070", r"5070 at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 1440p", "black_myth_wukong", "1440", "high", "High", "gpu_rtx5070", r"5070 FE ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Black Myth: Wukong - 1080p", "black_myth_wukong", "1080", "high", "High", "gpu_rtx5070", r"5070 down at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 4K", "starfield", "2160", "ultra", "Ultra", "gpu_rtx5070", r"RTX 5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 4K", "starfield", "2160", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti[^.]*?running a (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 1440p", "starfield", "1440", "ultra", "Ultra", "gpu_rtx5070", r"RTX 5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 1440p", "starfield", "1440", "ultra", "Ultra", "gpu_rx7900xt", r"7900 XT.{0,180}?runs at (\d+(?:\.\d+)?) FPS AVG"),
    ("Starfield - 1080p", "starfield", "1080", "ultra", "Ultra", "gpu_rtx5070", r"5070.s (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 4K", "cyberpunk2077", "2160", "ultra", "Ultra", "gpu_rtx5070", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 4K", "cyberpunk2077", "2160", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti, its (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1440p", "cyberpunk2077", "1440", "ultra", "Ultra", "gpu_rtx5070", r"5070 ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1440p", "cyberpunk2077", "1440", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti at (\d+(?:\.\d+)?) FPS"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rtx5070", r"with the 5070 at (\d+(?:\.\d+)?)"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rtx5070ti", r"5070 Ti ran at (\d+(?:\.\d+)?) FPS AVG"),
    ("Cyberpunk 2077: Phantom Liberty - 1080p", "cyberpunk2077", "1080", "ultra", "Ultra", "gpu_rx7900xt", r"This one ran at (\d+(?:\.\d+)?) FPS AVG"),
]


def section(soup, title):
    heading = next((h for h in soup.find_all(["h3", "h4"]) if h.get_text(" ", strip=True) == title), None)
    if heading is None:
        raise ValueError(f"Missing benchmark section: {title}")
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
        })
    return rows


def parse_geek(html):
    soup = BeautifulSoup(html, "html.parser")
    if "AMD Ryzen 7 9800X3D" not in soup.get_text(" "):
        raise ValueError("Reference CPU cannot be verified")
    rows = []
    for title, game, pattern in [
        ("Hogwarts Legacy", "hogwarts_legacy", r"RTX 5070 offered an output of (\d+(?:\.\d+)?)FPS"),
        ("Apex Legends", "apex", r"5070 held firmly at (\d+(?:\.\d+)?)FPS"),
    ]:
        _, body = section(soup, title)
        if "1440p" not in body or "High" not in body:
            raise ValueError(f"Unverified settings in {title}")
        rows.append({
            "game": game, "gpu_id": "gpu_rtx5070", "cpu_id": "cpu_r7_9800x3d",
            "reference_cpu": "AMD Ryzen 7 9800X3D", "resolution": "1440",
            "preset": "high", "preset_label": "High (article settings)",
            "avg_fps": measurement(body, pattern), "low1_fps": None,
            "ray_tracing": False, "upscaling": "native", "frame_generation": False,
            "game_version": "not reported", "reference_ram": "not reported in article text",
            "published_at": "2025-03-04", "source_title": "GeekaWhat NVIDIA GeForce RTX 5070 Review",
            "source_url": GEEK_URL, "chart_url": "", "source_section": title,
            "evidence_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "collection_method": "reviewed_section_regex", "reported_precision": "rounded article FPS",
        })
    return rows


def crawl(output=DEFAULT_OUTPUT):
    rows, sources = [], []
    for url, parser in [(GN_URL, parse_gn), (GEEK_URL, parse_geek)]:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PCBuilderBenchmark/1.0)", "Accept": "text/html"})
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
        rows.extend(parser(html))
        sources.append({"url": url, "html_sha256": hashlib.sha256(html.encode()).hexdigest()})
    snapshot = {"schema_version": 1, "collected_at": datetime.now(timezone.utc).isoformat(),
                "sources": sources, "measurements": rows}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = crawl(args.output)
    print(f"Collected {len(result['measurements'])} verified measurements from {len(result['sources'])} sources: {args.output}")
