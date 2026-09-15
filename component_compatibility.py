"""Conservative platform checks; installed board BIOS cannot be inferred from a listing."""
from __future__ import annotations

import re

PLATFORMS = {
    "AM4": {"A520", "B550", "X570"},
    "AM5": {"A620", "B650", "B650E", "X670", "X670E", "B840", "B850", "X870", "X870E"},
    "LGA1700": {"H610", "B660", "H670", "Z690", "B760", "H770", "Z790"},
    "LGA1851": {"H810", "B860", "Z890"},
}
SOURCES = {
    "AMD": "https://www.amd.com/en/products/processors/chipsets/am5.html",
    "Intel": "https://www.intel.com/content/www/us/en/support/articles/000092149/processors.html",
}


def socket_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper()).replace("SOCKET", "")


def chipset_key(board):
    text = str(board.get("chipset") or board.get("name") or board.get("product_name") or "").upper()
    match = re.search(r"(?<![A-Z0-9])([ABHXZ]\d{3}E?)(?=[^A-Z0-9]|M|I|$)", text)
    return match.group(1) if match else ""


def cpu_family(cpu):
    text = " ".join(str(cpu.get(key) or "") for key in ("name", "product_name", "id", "performance_ref_id")).lower()
    if "ultra" in text:
        match = re.search(r"(?:^|[^0-9])(2\d{2})[a-z]?(?:[^0-9]|$)", text)
        return "Intel", "200" if match else ""
    match = re.search(r"i[3579][\s_-]*(1[234])\d{3}", text)
    if match:
        return "Intel", match.group(1)
    match = re.search(r"(?:ryzen\s*[3579]|라이젠\s*[3579]|r[3579])[\s_-]*([5789])\d{3}", text)
    if match:
        return "AMD", match.group(1) + "000"
    return str(cpu.get("vendor") or ""), ""


def platform_compatibility(cpu, board, ram=None):
    """Check socket, chipset/CPU family, RAM and explicit manufacturer support.

    `compatible` means the platform can support this CPU with appropriate BIOS,
    not that an unknown retail board's installed firmware has been verified.
    """
    cpu_socket, board_socket = socket_key(cpu.get("socket")), socket_key(board.get("socket"))
    chipset = chipset_key(board)
    vendor, family = cpu_family(cpu)
    checks, warnings = [], []

    def check(label, ok, message):
        checks.append({"label": label, "status": "pass" if ok else "fail", "message": message})

    check("CPU 소켓", bool(cpu_socket and cpu_socket == board_socket),
          f"CPU {cpu_socket or '미확인'} / 메인보드 {board_socket or '미확인'}")
    known_chipset = chipset in PLATFORMS.get(cpu_socket, set())
    supported_family = family in {
        "AM4": {"5000"}, "AM5": {"7000", "8000", "9000"},
        "LGA1700": {"12", "13", "14"}, "LGA1851": {"200"},
    }.get(cpu_socket, set())
    check("CPU 세대·칩셋", known_chipset and supported_family,
          f"{vendor or '제조사 미확인'} {family or '세대 미확인'} / {chipset or '칩셋 미확인'}")

    cpu_ids = {str(cpu.get(k)) for k in ("id", "performance_ref_id") if cpu.get(k)}
    if board.get("supported_cpu_ids") is not None:
        check("제조사 CPU 지원 목록", bool(cpu_ids.intersection(map(str, board["supported_cpu_ids"]))),
              "메인보드에 명시된 CPU 지원 목록 대조")
    if ram is not None:
        memory = str(ram.get("type") or "").upper().replace(" ", "")
        board_memory = str(board.get("ram_type") or "").upper().replace(" ", "")
        allowed = {"AM4": {"DDR4"}, "AM5": {"DDR5"}, "LGA1700": {"DDR4", "DDR5"}, "LGA1851": {"DDR5"}}
        check("메모리 규격", bool(memory and memory == board_memory and memory in allowed.get(cpu_socket, set())),
              f"RAM {memory or '미확인'} / 메인보드 {board_memory or '미확인'}")
        if board.get("max_memory_gb"):
            check("메모리 용량", 0 < float(ram.get("gb") or 0) <= float(board["max_memory_gb"]),
                  f"{ram.get('gb', 0)}GB / 최대 {board['max_memory_gb']}GB")

    compatible = all(item["status"] == "pass" for item in checks)
    # A board's supported model and its shipped BIOS version are separate facts.
    bios_verified = bool(cpu_ids.intersection(map(str, board.get("bios_verified_cpu_ids") or [])))
    if compatible and not bios_verified:
        message = "플랫폼 호환 · 구매 전 정확한 보드 모델의 CPU 지원 목록과 출고 BIOS 버전을 확인하세요"
        warnings.append(message)
        checks.append({"label": "BIOS", "status": "warning", "message": message})
    elif compatible:
        checks.append({"label": "BIOS", "status": "pass", "message": "해당 CPU 지원 BIOS 확인 기록 있음"})
    return {
        "compatible": compatible,
        "status": "incompatible" if not compatible else "compatible" if bios_verified else "bios_check_required",
        "socket": cpu_socket, "chipset": chipset, "checks": checks, "warnings": warnings,
        "source_url": SOURCES.get(vendor, ""),
    }
