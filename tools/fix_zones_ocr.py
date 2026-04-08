"""
fix_zones_ocr.py -- Targeted OCR fix for low-coverage zones
对 I, J, B, G(部分), A(部分) 等区域运行裁剪后的高精度 OCR
"""
from __future__ import annotations
import json, re
from pathlib import Path
import numpy as np
from PIL import Image
import easyocr

BASE     = Path("E:/2025-2026-2/BIT-Nav-2026")
SRC_DIR  = BASE / "data/floorplans"
SRC_JSON = BASE / "data/wencui_building_v6.json"
DST_JSON = BASE / "data/wencui_building_v6.json"

FLOORS = [f"{n}F" for n in range(1, 11)]

CROP   = (76, 100, 2841, 1820)
CROP_W, CROP_H = 2765, 1720
OUT_W, OUT_H   = 745, 1205
M_PER_PX       = 0.2
HALL_PX, HALL_PY = 164, 564

ROOM_PATTERN = re.compile(r"^([A-M])-?(\d{3,4})$", re.IGNORECASE)

OCR_FIXES = {
    r"^1-":  "L-", r"^l-": "L-",
    r"\s+":  "",   r"[--]": "-",
    r"([A-M])(\d{3,4})$": r"\1-\2",
}

def normalize_ocr(raw: str) -> str:
    s = raw.strip()
    for pat, rep in OCR_FIXES.items():
        s = re.sub(pat, rep, s)
    return s.upper()

def _zone_normalize(raw: str, letter: str) -> str:
    """Generic normalizer for zones whose letter is misread as '1' by OCR."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # "1-101" or "l-101" or "1101" or "l101" -> "X-101" (where X=letter)
    m = re.match(r"^[1l]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"{letter}-{m.group(1)}"
    # Already correct form: "X-101" or "X101"
    m2 = re.match(rf"^{re.escape(letter)}-?(\d{{3,4}})$", s, re.IGNORECASE)
    if m2:
        return f"{letter}-{m2.group(1)}"
    return s.upper()

def normalize_ocr_i(raw: str) -> str:
    """I zone: OCR misreads 'I' as '1'; also handles bare 3/4-digit numbers."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # Already correct
    m2 = re.match(r"^I-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"I-{m2.group(1)}"
    # I misread as '1' or 'l'
    m = re.match(r"^[1l]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"I-{m.group(1)}"
    # Bare 3/4-digit number
    m3 = re.match(r"^(\d{3,4})$", s)
    if m3:
        return f"I-{m3.group(1)}"
    return s.upper()

def normalize_ocr_j(raw: str) -> str:
    """J zone: OCR misreads 'J' as '1' or 'L'; also handles bare 3/4-digit numbers."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # Already correct: J-xxx or Jxxx
    m2 = re.match(r"^J-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"J-{m2.group(1)}"
    # J misread as '1', 'l', or 'L'
    m = re.match(r"^[1lL]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"J-{m.group(1)}"
    # Bare 3/4-digit number (zone confirmed by search box + zone filter)
    m3 = re.match(r"^(\d{3,4})$", s)
    if m3:
        return f"J-{m3.group(1)}"
    return s.upper()

def normalize_ocr_b(raw: str) -> str:
    """B zone: OCR misreads 'B' as '8', '6', or '0'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^[860]-?(\d{3,4})$", s)
    if m:
        return f"B-{m.group(1)}"
    m2 = re.match(r"^B-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"B-{m2.group(1)}"
    return s.upper()

def normalize_ocr_a(raw: str) -> str:
    """A zone: OCR misreads 'A' as '0' (zero) or '4'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # "0-301", "4-301", "0301", "4301" -> "A-301"
    m = re.match(r"^[04]-?(\d{3,4})$", s)
    if m:
        return f"A-{m.group(1)}"
    m2 = re.match(r"^A-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"A-{m2.group(1)}"
    return s.upper()

def normalize_ocr_f(raw: str) -> str:
    """F zone: OCR misreads 'F' as '0' or 'D'; also handles bare 3/4-digit numbers."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # Already correct
    m2 = re.match(r"^F-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"F-{m2.group(1)}"
    # F misread as '0' or 'D'
    m = re.match(r"^[0D]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"F-{m.group(1)}"
    # Bare 3/4-digit number
    m3 = re.match(r"^(\d{3,4})$", s)
    if m3:
        return f"F-{m3.group(1)}"
    return s.upper()

def normalize_ocr_e(raw: str) -> str:
    """E zone: OCR misreads 'E' as 'F'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^F-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"E-{m.group(1)}"
    m2 = re.match(r"^E-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"E-{m2.group(1)}"
    return s.upper()

def normalize_ocr_c(raw: str) -> str:
    """C zone: OCR misreads 'C' as '0' (zero) or 'G'; also handles bare 3/4-digit numbers."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # Already correct: C-xxx or Cxxx
    m2 = re.match(r"^C-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"C-{m2.group(1)}"
    # C misread as '0' or 'G'
    m = re.match(r"^[0G]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"C-{m.group(1)}"
    # Bare 3/4-digit number (zone confirmed by search box + zone filter)
    m3 = re.match(r"^(\d{3,4})$", s)
    if m3:
        return f"C-{m3.group(1)}"
    return s.upper()

def normalize_ocr_g(raw: str) -> str:
    """G zone: OCR misreads 'G' as '6' or '5'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^[65]-?(\d{3,4})$", s)
    if m:
        return f"G-{m.group(1)}"
    m2 = re.match(r"^G-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"G-{m2.group(1)}"
    return s.upper()

def normalize_ocr_m(raw: str) -> str:
    """M zone: OCR misreads 'M' as 'V', 'W', '1', or multiple '1's."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # Already correct
    m2 = re.match(r"^M-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"M-{m2.group(1)}"
    # Single-char misread: V/W/1/l prefix
    m = re.match(r"^[VW1l]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"M-{m.group(1)}"
    # Multi-char prefix like '11-128', 'MV-134'
    m3 = re.match(r"^[MV1l]{1,3}-(\d{3,4})$", s, re.IGNORECASE)
    if m3:
        return f"M-{m3.group(1)}"
    return s.upper()

def normalize_ocr_l(raw: str) -> str:
    """L zone: OCR misreads 'L' as '1' or 'l'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^[1l]-?(\d{3,4})$", s, re.IGNORECASE)
    if m:
        return f"L-{m.group(1)}"
    m2 = re.match(r"^L-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"L-{m2.group(1)}"
    return s.upper()

def normalize_ocr_h(raw: str) -> str:
    """H zone: OCR misreads 'H' as '4' or '#'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^[4#]-?(\d{3,4})$", s)
    if m:
        return f"H-{m.group(1)}"
    m2 = re.match(r"^H-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"H-{m2.group(1)}"
    return s.upper()

def normalize_ocr_d(raw: str) -> str:
    """D zone: OCR misreads 'D' as '0' (zero) or '4'."""
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    # "0-301", "4-301" -> "D-301"；纯数字 "301" 也接受
    m = re.match(r"^[04]-?(\d{3,4})$", s)
    if m:
        return f"D-{m.group(1)}"
    m2 = re.match(r"^D-?(\d{3,4})$", s, re.IGNORECASE)
    if m2:
        return f"D-{m2.group(1)}"
    # 纯三/四位数字（无前缀）也尝试匹配
    m3 = re.match(r"^(\d{3,4})$", s)
    if m3:
        return f"D-{m3.group(1)}"
    return s.upper()

def orig_to_unified(ox, oy):
    cx, cy = ox - CROP[0], oy - CROP[1]
    rx = CROP_H - 1 - cy
    ry = cx
    ux = round(rx * OUT_W / CROP_H)
    uy = round(ry * OUT_H / CROP_W)
    return max(0, min(OUT_W-1, ux)), max(0, min(OUT_H-1, uy))

def pixel_to_coords(ux, uy):
    return {
        "east_m":  round((ux - HALL_PX) * M_PER_PX, 2),
        "south_m": round((uy - HALL_PY) * M_PER_PX, 2),
    }

def unified_box_to_orig_crop(ux_min, uy_min, ux_max, uy_max):
    """
    反变换统一坐标框到原始图像裁剪区域
    统一坐标变换: cx=ry=uy*CROP_W/OUT_H, cy=CROP_H-1-rx=CROP_H-1-ux*CROP_H/OUT_W
    """
    def ux_to_cy(ux):
        rx = ux * CROP_H / OUT_W
        return CROP_H - 1 - rx

    def uy_to_cx(uy):
        return uy * CROP_W / OUT_H

    # ux -> cy -> oy = cy + CROP[1]
    oy_from_ux_max = ux_to_cy(ux_max) + CROP[1]  # small oy (east)
    oy_from_ux_min = ux_to_cy(ux_min) + CROP[1]  # large oy (west)

    # uy -> cx -> ox = cx + CROP[0]
    ox_from_uy_min = uy_to_cx(uy_min) + CROP[0]  # small ox (north)
    ox_from_uy_max = uy_to_cx(uy_max) + CROP[0]  # large ox (south)

    left   = max(0,    int(ox_from_uy_min))
    right  = min(3000, int(ox_from_uy_max))
    top    = max(0,    int(oy_from_ux_max))
    bottom = min(2000, int(oy_from_ux_min))
    return left, top, right, bottom

def match_room_id(text, floor, nodes):
    m = ROOM_PATTERN.match(text)
    if not m:
        return nodes.get(text) and text
    zone, room_num = m.group(1).upper(), m.group(2)
    floor_num = floor[:-1]
    if len(room_num) == 3:
        canonical = f"{zone}-{floor_num}{room_num[1:]}"
    elif len(room_num) == 4:
        canonical = f"{zone}-{floor_num}{room_num[2:]}"
    else:
        canonical = None
    if canonical and canonical in nodes:
        return canonical
    direct = f"{zone}-{room_num}"
    return direct if direct in nodes else None

# Zone search boxes: (ux_min, uy_min, ux_max, uy_max) in unified coords
# ux=east-west (0=west, 744=east), uy=north-south (0=north, 1204=south)
ZONE_BOXES = {
    'I':       (20,  180, 700, 430),    # northeast, north of hall（扩展至西边界）
    'J':       (0,   0,   590, 270),    # far north strip
    'B':       (530, 600, 744, 1180),   # east side，1F/2F only
    'G_north': (0,   300, 400, 1200),   # G zone 1F/2F rooms (G misread as '6' or '5')
    # A zone: A misread as '0' or '4'; valid rooms uy<=797, cap at 850 to exclude D zone
    'A_north': (390, 0,   744, 850),    # A zone (uy>850 overlaps D zone territory)
    'E':       (30,  420, 560, 1210),   # E zone，1F-10F
    'F':       (190, 360, 595, 1085),   # F zone，1F-7F
    'C':       (290, 330, 730, 1210),   # C zone，1F-10F
    'D':       (258, 962, 454, 1166),   # D zone（收紧到确认节点范围）
    # M zone: northeast corner
    'M':       (380, 0,   744, 560),    # M zone（扩展至ux=380覆盖M-135，M→V/W/1）
    'H':       (0,   20,  560, 810),    # H zone（1F/2F only，扩展至ux=560）
    'L':       (20,  0,   720, 550),    # L zone，1F-10F（L misread as '1'）
}

BOX_TO_ZONE = {
    'I': 'I', 'J': 'J', 'B': 'B',
    'E': 'E', 'F': 'F', 'C': 'C', 'G_north': 'G', 'A_north': 'A',
    'D': 'D', 'M': 'M', 'H': 'H', 'L': 'L',
}

def process_zone_floor(zone_key, floor, reader, nodes, updated, conf_thresh=0.30):
    img_path = SRC_DIR / f"{floor}_official.jpg"
    if not img_path.exists():
        return 0

    ux_min, uy_min, ux_max, uy_max = ZONE_BOXES[zone_key]
    left, top, right, bottom = unified_box_to_orig_crop(ux_min, uy_min, ux_max, uy_max)

    if right <= left or bottom <= top:
        return 0

    img = Image.open(img_path).convert("RGB")
    crop_img = img.crop((left, top, right, bottom))
    img_np = np.array(crop_img)

    raw_results = reader.readtext(img_np, detail=1, paragraph=False)

    count = 0
    for (box, text, conf) in raw_results:
        if conf < conf_thresh:
            continue
        cx_crop = sum(p[0] for p in box) / 4
        cy_crop = sum(p[1] for p in box) / 4
        cx = cx_crop + left
        cy = cy_crop + top

        # Zone-specific normalizers for systematic OCR misreads:
        # I/J -> 1, A -> 0 or 4, B -> 8 or 6
        if zone_key == 'I':
            norm = normalize_ocr_i(text)
        elif zone_key == 'J':
            norm = normalize_ocr_j(text)
        elif zone_key in ('A_north', 'A_south'):
            norm = normalize_ocr_a(text)
        elif zone_key in ('G_north', 'G_south'):
            norm = normalize_ocr_g(text)
        elif zone_key == 'B':
            norm = normalize_ocr_b(text)
        elif zone_key == 'D':
            norm = normalize_ocr_d(text)
        elif zone_key == 'F':
            norm = normalize_ocr_f(text)
        elif zone_key == 'E':
            norm = normalize_ocr_e(text)
        elif zone_key == 'C':
            norm = normalize_ocr_c(text)
        elif zone_key == 'H':
            norm = normalize_ocr_h(text)
        elif zone_key == 'L':
            norm = normalize_ocr_l(text)
        elif zone_key == 'M':
            norm = normalize_ocr_m(text)
        else:
            norm = normalize_ocr(text)
        if not ROOM_PATTERN.match(norm):
            continue

        nid = match_room_id(norm, floor, nodes)
        if nid and nodes[nid].get("floor") == floor:
            expected_zone = BOX_TO_ZONE[zone_key]
            if nodes[nid].get("zone") != expected_zone:
                continue
            # 已人工确认/纠正/推算的节点不覆盖
            v = nodes[nid]
            if v.get("verified_ok") or v.get("verified_fixed") or v.get("inferred_from"):
                continue
            # 标记点直接取 OCR 文字框中心
            ux, uy = orig_to_unified(cx, cy)
            coords = pixel_to_coords(ux, uy)
            v.update({
                "x": round(cx), "y": round(cy),
                "ux": ux, "uy": uy,
                **coords,
                "ocr_conf": round(conf, 3),
                "ocr_raw": text,
            })
            updated.add(nid)
            count += 1
    return count

def main():
    print("=== Low-coverage zone targeted OCR fix ===")

    with open(SRC_JSON, encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]

    # Initial coverage
    def zone_coverage():
        stats = {}
        for k, v in nodes.items():
            z = v.get("zone", "?")
            if z not in stats:
                stats[z] = [0, 0]
            stats[z][0] += 1
            if "ocr_conf" in v:
                stats[z][1] += 1
        return stats

    before = zone_coverage()
    print("Before:")
    for z in ['I', 'J', 'B', 'G', 'A', 'D', 'H']:
        t, o = before.get(z, [0, 0])
        pct = o/t*100 if t else 0
        print(f"  {z}: {o}/{t} ({pct:.0f}%)")

    print("\nInitializing EasyOCR ...")
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)

    updated: set[str] = set()

    for zone_key in ZONE_BOXES:
        orig_box = unified_box_to_orig_crop(*ZONE_BOXES[zone_key])
        print(f"\n[{zone_key}] unified={ZONE_BOXES[zone_key]} orig={orig_box}")

        floor_totals = {}
        for floor in FLOORS:
            cnt = process_zone_floor(zone_key, floor, reader, nodes, updated)
            if cnt > 0:
                floor_totals[floor] = cnt
                print(f"  {floor}: +{cnt}")

        total = sum(floor_totals.values())
        print(f"  subtotal: {total}")

    after = zone_coverage()
    print("\nAfter:")
    all_t, all_o = 0, 0
    for z in sorted(after.keys()):
        t, o = after[z]
        all_t += t
        all_o += o
        pct = o/t*100 if t else 0
        print(f"  {z}: {o}/{t} ({pct:.0f}%)")
    print(f"  Total: {all_o}/{all_t} ({all_o/all_t*100:.1f}%)")
    print(f"  Updated this run: {len(updated)}")

    data["nodes"] = nodes
    with open(DST_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {DST_JSON.name}")

if __name__ == "__main__":
    main()
