"""
ocr_rooms.py — 文萃楼平面图 OCR 房间位置自动标定
================================================
流程：
  1. 对每层原始 3000×2000 图像运行 EasyOCR
  2. 正则过滤房间号 / 功能用房标签
  3. 后处理：纠正常见 OCR 误识（L→1、前缀丢失等）
  4. 与现有节点列表精确匹配
  5. 更新节点坐标 (x, y, ux, uy, east_m, south_m)
  6. 写出 wencui_building_v4.json + 逐层识别报告

输出：
  data/wencui_building_v4.json  — 坐标经OCR标定后的完整数据
  data/ocr_reports/             — 每层识别日志（matched/unmatched/ambiguous）
"""

from __future__ import annotations
import json, re, copy
from pathlib import Path
from collections import defaultdict

import numpy as np
from PIL import Image
import easyocr

# ─── 路径 ─────────────────────────────────────────────────────────────────────
BASE      = Path("E:/2025-2026-2/BIT-Nav-2026")
SRC_DIR   = BASE / "data/floorplans"
RPT_DIR   = BASE / "data/ocr_reports"
RPT_DIR.mkdir(exist_ok=True)
SRC_JSON  = BASE / "data/wencui_building_v5_predicted_v2.json"
DST_JSON  = BASE / "data/wencui_building_v6.json"

FLOORS = [f"{n}F" for n in range(1, 11)]

# 图例区域（在原始坐标系中，跳过此区域避免识别图例文字）
LEGEND_BOX = (950, 550, 1600, 980)   # (x0, y0, x1, y1)

# ─── 坐标换算（从 floorplan_align.py 同步）────────────────────────────────────
CROP    = (76, 100, 2841, 1820)
CROP_W, CROP_H = CROP[2] - CROP[0], CROP[3] - CROP[1]   # 2765, 1720
REAL_NS_M, REAL_EW_M = 240.9, 149.0
OUT_W, OUT_H = 745, 1205
M_PER_PX     = 1.0 / 5
HALL_PX, HALL_PY = 164, 563   # 上北下南，顺时针旋转后的报告厅坐标

def orig_to_unified(ox: float, oy: float) -> tuple[int, int]:
    """原始像素 → 统一校正图像素（顺时针 90° 变换，上北下南）"""
    cx, cy = ox - CROP[0], oy - CROP[1]
    # ROTATE_270 (CW): x_new = CROP_H-1-y_old, y_new = x_old
    rx = CROP_H - 1 - cy
    ry = cx
    ux = round(rx * OUT_W / CROP_H)
    uy = round(ry * OUT_H / CROP_W)
    return max(0, min(OUT_W-1, ux)), max(0, min(OUT_H-1, uy))

def pixel_to_coords(ux: int, uy: int) -> dict:
    return {
        "east_m":  round((ux - HALL_PX) * M_PER_PX, 2),
        "south_m": round((uy - HALL_PY) * M_PER_PX, 2),  # 向下=向南=正值
    }


# ─── OCR 后处理 ───────────────────────────────────────────────────────────────
# 平面图常见 OCR 误识映射
OCR_FIXES = {
    r"^1-":   "L-",   # L 误识为 1
    r"^l-":   "L-",
    r"^I-":   "I-",
    r"^0-":   "G-",   # G 误识为 0（少见）
    r"\s+":   "",     # 去空格
    r"—":     "-",    # 破折号→连字符
    r"－":    "-",
    r"([A-M])(\d{3})": r"\1-\2",  # 补充缺失连字符 "L101"→"L-101"
}

# 功能用房关键词
FUNC_KEYWORDS = {
    "卫生间": "toilet",
    "厕所":   "toilet",
    "楼梯":   "stairs",
    "电梯":   "elevator",
    "电梯厅": "elevator",
    "门厅":   "lobby",
    "入口":   "entrance",
    "走廊":   "corridor",
    "休息区": "lounge",
    "报告厅": "lecture_hall",
    "圆楼":   "circular",
    "圆形教室": "circular",
}

ROOM_PATTERN = re.compile(r"^([A-M])-?(\d{3,4})$", re.IGNORECASE)  # 10F用4位编号

def normalize_ocr(raw: str) -> str:
    """对OCR文本做后处理纠错，返回规范化字符串"""
    s = raw.strip()
    for pat, rep in OCR_FIXES.items():
        s = re.sub(pat, rep, s)
    return s.upper()


def in_legend(cx: float, cy: float) -> bool:
    x0, y0, x1, y1 = LEGEND_BOX
    return x0 <= cx <= x1 and y0 <= cy <= y1


# ─── 构建索引：节点ID → {floor, zone, ...} ────────────────────────────────────
def build_node_index(nodes: dict) -> dict[str, dict[str, list]]:
    """floor → zone → list of node_ids"""
    idx: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for nid, n in nodes.items():
        fl, z = n.get("floor", "?"), n.get("zone", "?")
        idx[fl][z].append(nid)
    return idx


def match_room_id(text: str, floor: str, nodes: dict) -> str | None:
    """
    尝试把 OCR 文本匹配到现有节点 ID。
    支持 3 位（1F-9F）和 4 位（10F）房间编号。
    匹配优先级：
      1. 楼层前缀替换（最可靠：消除跨层干扰）
      2. 直接精确匹配（OCR 已读对完整编号）
    """
    m = ROOM_PATTERN.match(text)
    if m:
        zone, room_num = m.group(1).upper(), m.group(2)
        floor_num = floor[:-1]   # "6F"→"6"，"10F"→"10"

        # 1) 楼层前缀替换（优先）
        #    3位: "C-503" on 6F → "C-6"+"03" = "C-603"
        #    3位: "C-101" on 10F → "C-10"+"01" = "C-1001"
        #    4位: "C-1001" on 10F → "C-10"+"01" = "C-1001"
        if len(room_num) == 3:
            canonical = f"{zone}-{floor_num}{room_num[1:]}"
        elif len(room_num) == 4:
            canonical = f"{zone}-{floor_num}{room_num[2:]}"
        else:
            canonical = None
        if canonical and canonical in nodes:
            return canonical

        # 2) 直接精确匹配（OCR 读对了完整编号，如 10F 的 "C-1001"）
        direct = f"{zone}-{room_num}"
        if direct in nodes:
            return direct

    elif text in nodes:
        return text
    return None


def match_func_label(text: str) -> str | None:
    """匹配功能用房关键词，返回类型字符串"""
    for kw, typ in FUNC_KEYWORDS.items():
        if kw in text:
            return typ
    return None


# ─── 主处理函数 ───────────────────────────────────────────────────────────────
def process_floor(floor: str, reader: easyocr.Reader,
                  nodes: dict, updated: set) -> dict:
    """处理单楼层，返回报告字典"""
    img_path = SRC_DIR / f"{floor}_official.jpg"
    if not img_path.exists():
        return {"floor": floor, "error": "图像不存在"}

    # PIL 读取（自动处理 EXIF 旋转），转 numpy
    img_np = np.array(Image.open(img_path).convert("RGB"))  # (H=2000, W=3000, 3)

    print(f"  [OCR] {floor} ...", end="", flush=True)
    raw_results = reader.readtext(img_np, detail=1, paragraph=False)
    print(f" {len(raw_results)} 条原始结果")

    report = {
        "floor": floor,
        "matched": [],
        "unmatched_rooms": [],
        "func_labels": [],
        "skipped": [],
    }

    for (box, text, conf) in raw_results:
        if conf < 0.35:
            continue

        # 中心坐标（原始像素）
        cx = sum(p[0] for p in box) / 4
        cy = sum(p[1] for p in box) / 4

        # 跳过图例区域
        if in_legend(cx, cy):
            report["skipped"].append({"text": text, "conf": round(conf, 2),
                                       "cx": round(cx), "cy": round(cy)})
            continue

        norm = normalize_ocr(text)

        # ── 尝试匹配房间号 ──────────────────────────────────────────────────
        if ROOM_PATTERN.match(norm):
            nid = match_room_id(norm, floor, nodes)
            if nid and nodes[nid].get("floor") == floor:
                ux, uy = orig_to_unified(cx, cy)
                coords = pixel_to_coords(ux, uy)
                # 更新节点
                nodes[nid].update({
                    "x": round(cx), "y": round(cy),
                    "ux": ux, "uy": uy,
                    **coords,
                    "ocr_conf": round(conf, 3),
                    "ocr_raw":  text,
                })
                updated.add(nid)
                report["matched"].append({
                    "nid": nid, "raw": text, "conf": round(conf, 2),
                    "cx": round(cx), "cy": round(cy),
                    "east_m": coords["east_m"], "south_m": coords["south_m"],
                })
            else:
                report["unmatched_rooms"].append({
                    "raw": text, "norm": norm, "conf": round(conf, 2),
                    "cx": round(cx), "cy": round(cy),
                })

        # ── 尝试匹配功能用房 ────────────────────────────────────────────────
        else:
            func_type = match_func_label(norm)
            if func_type:
                report["func_labels"].append({
                    "text": norm, "type": func_type,
                    "conf": round(conf, 2),
                    "cx": round(cx), "cy": round(cy),
                })

    return report


def main():
    print("=== OCR 房间位置标定 ===")

    # 加载现有数据
    with open(SRC_JSON, encoding="utf-8") as f:
        data = json.load(f)
    nodes = data["nodes"]
    print(f"  加载节点: {len(nodes)}")

    # 初始化 EasyOCR（中文+英文）
    print("  初始化 EasyOCR ...")
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)

    updated: set[str] = set()
    all_reports = []

    for floor in FLOORS:
        report = process_floor(floor, reader, nodes, updated)
        all_reports.append(report)

        # 写逐层报告
        rpt_path = RPT_DIR / f"{floor}_ocr.json"
        with open(rpt_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        matched_n = len(report.get("matched", []))
        unmatched_n = len(report.get("unmatched_rooms", []))
        func_n = len(report.get("func_labels", []))
        print(f"  {floor}: 匹配 {matched_n} 间 | 未匹配 {unmatched_n} 条 | 功能用房 {func_n} 处")

    # 汇总统计
    total_matched = sum(len(r.get("matched", [])) for r in all_reports)
    total_nodes   = len(nodes)
    room_nodes    = [n for n in nodes.values() if n.get("type") == "room"]

    print(f"\n  节点总数: {total_nodes}")
    print(f"  房间节点: {len(room_nodes)}")
    print(f"  OCR更新:  {len(updated)} 个节点")
    print(f"  覆盖率:   {len(updated)/len(room_nodes)*100:.1f}%")

    # 写汇总报告
    summary = {
        "total_nodes": total_nodes,
        "room_nodes": len(room_nodes),
        "ocr_updated": len(updated),
        "coverage_pct": round(len(updated) / len(room_nodes) * 100, 1),
        "floors": all_reports,
    }
    with open(RPT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 写最终 JSON
    data["nodes"] = nodes
    data["ocr_metadata"] = {
        "source_images": "data/floorplans/*_official.jpg (3000×2000 PIL)",
        "engine": "EasyOCR 1.7.2 ch_sim+en",
        "updated_nodes": len(updated),
        "room_coverage_pct": round(len(updated) / len(room_nodes) * 100, 1),
    }
    with open(DST_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  写出: {DST_JSON.name}")


if __name__ == "__main__":
    main()
