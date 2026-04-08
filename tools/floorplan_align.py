"""
floorplan_align.py — 文萃楼平面图统一校正脚本
================================================
转换流程（每层完全一致）：
  1. 统一裁切  (76, 100, 2841, 1820) — 去除白色边框，保留全部房间节点
  2. 旋转      PIL ROTATE_270 (顺时针 90°)
               原图：左=北 右=南 上=东 下=西
               结果：上=北 下=南 左=西 右=东  （上北下南，左西右东，标准朝向）
  3. 缩放      统一 5 px/m，输出 745×1205 px

输出坐标系（以圆形报告厅/圆楼中心为原点）：
  x 轴：向右 = 向东，正值（米）
  y 轴：向下 = 向南，正值（米）[图像像素惯例，与标准地图一致]

换算公式：
  x_east_m  = (pixel_x - HALL_PX) * M_PER_PX
  y_south_m = (pixel_y - HALL_PY) * M_PER_PX   ← 南正（向下为正，标准图像坐标）
"""

from __future__ import annotations
import json
from pathlib import Path

from PIL import Image

# ─── 路径配置 ─────────────────────────────────────────────────────────────────
BASE    = Path("E:/2025-2026-2/BIT-Nav-2026")
SRC_DIR = BASE / "data/archive/floorplans"
DST_DIR = BASE / "data/archive/floorplans_unified"
DST_DIR.mkdir(exist_ok=True)

FLOORS = [f"{n}F" for n in range(1, 11)]   # 1F ~ 10F

# ─── 变换参数（基于 3000×2000 原始图）────────────────────────────────────────
# 圆形报告厅/圆楼 中心（原始像素坐标）
# 根据 room_verifier 截图观察：原点在圆楼右上边缘，圆楼中心在原点左下方
# 需要调整：向左约 30px，向下约 30px（在 unified 坐标系中）
# 转换到原始图：30px × (2765/745) ≈ 111px
HALL_ORIG_X = 1237  # 1348 - 111，向左调整
HALL_ORIG_Y = 1381  # 1270 + 111，向下调整

# 统一裁切框：覆盖所有房间节点，零越界
CROP = (76, 100, 2841, 1820)          # (left, top, right, bottom)
CROP_W = CROP[2] - CROP[0]            # 2765 px = 240.9 m（南北）
CROP_H = CROP[3] - CROP[1]            # 1720 px = 149.0 m（东西）

# 建筑真实尺寸（来自 GPS）
REAL_NS_M = 240.9    # 南北跨度（米）
REAL_EW_M = 149.0    # 东西跨度（米）

# 输出图额外边距（south 方向）
EXTRA_SOUTH_M = 20   # 增加 20m south 边距

# 输出分辨率：5 px/m
PX_PER_M   = 5
OUT_W      = round(REAL_EW_M * PX_PER_M)   # 745  px（东西，水平方向）
OUT_H      = round(REAL_NS_M * PX_PER_M)   # 1205 px（南北，垂直方向）
M_PER_PX   = 1.0 / PX_PER_M               # 0.2 m/px

# ─── 推导报告厅在输出图中的像素坐标 ─────────────────────────────────────────
# 步骤 1：裁切后坐标
_hcx = HALL_ORIG_X - CROP[0]    # 1370 - 76  = 1294
_hcy = HALL_ORIG_Y - CROP[1]    # 1440 - 100 = 1340

# 步骤 2：ROTATE_270（顺时针 90°）
#   裁切图尺寸：(CROP_W, CROP_H) = (2765, 1720)
#   旋转后尺寸：(CROP_H, CROP_W) = (1720, 2765)  ← width=EW, height=NS
#   像素变换：  x_new = CROP_H - 1 - y_old,  y_new = x_old
#   结果朝向：  上=北 下=南 左=西 右=东（标准地图方向）
_hrx = CROP_H - 1 - _hcy          # 1720 - 1 - 1340 = 379
_hry = _hcx                        # 1294

# 步骤 3：缩放到 OUT_W × OUT_H
HALL_PX = round(_hrx * OUT_W / CROP_H)    # round(379 * 745/1720) = 164
HALL_PY = round(_hry * OUT_H / CROP_W)    # round(1294 * 1205/2765) = 564

# 报告厅 GPS（从坐标系推算）
# 建筑坐标系原点（左上）GPS：lat=39.732402, lon=116.168583
# 报告厅在原始建筑坐标系中：
#   x_m = (_hcx) * (REAL_NS_M / CROP_W) = 1294 * 240.9/2765 = 112.7 m（南向）
#   y_m = (_hcy) * (REAL_EW_M / CROP_H) = 1340 * 149.0/1720 = 116.1 m（西向）
_hall_xm = _hcx * REAL_NS_M / CROP_W      # 112.7 m southward from N edge
_hall_ym = _hcy * REAL_EW_M / CROP_H      # 116.1 m westward from E edge
HALL_GPS = {
    "lat": round(39.732402 - _hall_xm / 111000, 6),
    "lon": round(116.168583 - _hall_ym / 85365, 6),
}


# ─── 高分辨率导出参数（仅供可视化，不影响导航坐标）────────────────────────────
HIRES_PX_PER_M = 15
HIRES_OUT_W    = round(REAL_EW_M * HIRES_PX_PER_M)   # 2235 px
HIRES_OUT_H    = round((REAL_NS_M + EXTRA_SOUTH_M) * HIRES_PX_PER_M)   # 3913 px (增加边距)
HIRES_DIR      = BASE / "data/floorplans_hires"
HIRES_DIR.mkdir(exist_ok=True)

# ─── 图像变换函数 ─────────────────────────────────────────────────────────────
def transform(img: Image.Image, out_w: int = OUT_W, out_h: int = OUT_H, 
              extra_south_px: int = 0) -> Image.Image:
    """原始 3000×2000 → 统一校正输出（可指定输出尺寸）"""
    # 1. 裁切
    img = img.crop(CROP)                                    # 2765×1720
    # 2. 顺时针旋转 90°（ROTATE_270 in PIL）→ 上北下南，左西右东
    img = img.transpose(Image.Transpose.ROTATE_270)         # 1720×2765
    # 3. 缩放到统一尺寸
    img = img.resize((out_w, out_h), Image.Resampling.LANCZOS)
    
    # 4. 如果需要，在底部添加边距（保持原点不变）
    if extra_south_px > 0:
        from PIL import Image as PILImage
        new_h = out_h + extra_south_px
        new_img = PILImage.new('RGB', (out_w, new_h), (255, 255, 255))
        new_img.paste(img, (0, 0))
        img = new_img
    
    return img


def pixel_to_coords(px: float, py: float) -> dict:
    """输出图像素坐标 → 实际米坐标（以报告厅中心为原点）"""
    return {
        "x_east_m":  round((px - HALL_PX) * M_PER_PX, 2),
        "y_south_m": round((py - HALL_PY) * M_PER_PX, 2),  # 南为正（向下为正，标准图像坐标）
    }


def orig_pixel_to_unified(ox: float, oy: float) -> tuple[int, int]:
    """原始 3000×2000 像素坐标 → 输出像素坐标（顺时针 90° 变换）"""
    # 裁切
    cx = ox - CROP[0]
    cy = oy - CROP[1]
    # ROTATE_270（顺时针 90°）：x_new = CROP_H-1-y_old, y_new = x_old
    rx = CROP_H - 1 - cy
    ry = cx
    # 缩放
    ux = round(rx * OUT_W / CROP_H)
    uy = round(ry * OUT_H / CROP_W)
    return ux, uy


# ─── 主程序 ──────────────────────────────────────────────────────────────────
def main() -> None:
    print("文萃楼平面图统一校正")
    print(f"  裁切: {CROP}  裁切后: {CROP_W}×{CROP_H} px")
    print(f"  旋转: ROTATE_270_CW（上北下南，左西右东，标准朝向）")
    print(f"  输出: {OUT_W}×{OUT_H} px  @  {PX_PER_M} px/m = {M_PER_PX} m/px")
    print(f"  报告厅中心: 原始({HALL_ORIG_X},{HALL_ORIG_Y}) → 输出({HALL_PX},{HALL_PY})")
    print(f"  报告厅 GPS: {HALL_GPS}")
    print()

    failed: list[str] = []

    for floor in FLOORS:
        src = SRC_DIR / f"{floor}_official.jpg"
        dst = DST_DIR / f"{floor}_unified.jpg"

        if not src.exists():
            print(f"  [SKIP] {floor}: {src.name} 不存在")
            failed.append(floor)
            continue

        img = Image.open(src).convert("RGB")
        assert img.size == (3000, 2000), f"{floor} 图像尺寸异常: {img.size}"

        out = transform(img)
        assert out.size == (OUT_W, OUT_H), f"输出尺寸异常: {out.size}"

        out.save(dst, quality=95, optimize=True)
        print(f"  [OK] {floor} → {dst.name}")

    # 生成坐标系参数 JSON
    coord_params = {
        "description": "文萃楼平面图统一校正坐标系",
        "orientation": "上北下南，左西右东（标准地图朝向）",
        "origin": "圆形报告厅/圆楼中心",
        "origin_gps": HALL_GPS,
        "output_size_px": {"width": OUT_W, "height": OUT_H},
        "scale": {
            "px_per_m": PX_PER_M,
            "m_per_px": M_PER_PX,
        },
        "hall_pixel": {"x": HALL_PX, "y": HALL_PY},
        "axes": {
            "x": "向右 = 向东（正值）",
            "y": "向下 = 向南（正值，与标准地图一致）",
        },
        "formulas": {
            "x_east_m":  f"(pixel_x - {HALL_PX}) * {M_PER_PX}",
            "y_south_m": f"(pixel_y - {HALL_PY}) * {M_PER_PX}",
            "pixel_x":   f"x_east_m / {M_PER_PX} + {HALL_PX}",
            "pixel_y":   f"y_south_m / {M_PER_PX} + {HALL_PY}",
        },
        "crop_original_3000x2000": list(CROP),
        "transform_sequence": [
            f"1. crop {CROP}",
            "2. PIL ROTATE_270 (顺时针 90°) → 上北下南",
            f"3. resize to {OUT_W}×{OUT_H} (LANCZOS)",
        ],
        "building_bounds": {
            "real_ew_m": REAL_EW_M,
            "real_ns_m": REAL_NS_M,
        },
        "failed_floors": failed,
    }

    params_path = DST_DIR / "unified_params.json"
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(coord_params, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] 坐标参数 → {params_path.name}")

    # 导出高分辨率图（供可视化/OCR校验，不影响导航坐标）
    _export_hires()

    # 顺便把节点坐标换算为统一坐标系
    _convert_node_coords()


def _export_hires() -> None:
    """将所有楼层导出为高分辨率版（15 px/m，供可视化与房间号校验）"""
    extra_south_px = round(EXTRA_SOUTH_M * HIRES_PX_PER_M)  # 20m = 300px
    actual_h = round(REAL_NS_M * HIRES_PX_PER_M)  # 原始高度 3614
    print(f"\n  [高分辨率导出] {HIRES_OUT_W}×{HIRES_OUT_H} px @ {HIRES_PX_PER_M} px/m")
    print(f"    原始高度: {actual_h}px, 额外边距: {extra_south_px}px")
    for floor in FLOORS:
        src = SRC_DIR / f"{floor}_official.jpg"
        dst = HIRES_DIR / f"{floor}_hires.jpg"
        if not src.exists():
            print(f"  [SKIP] {floor}: 源文件不存在")
            continue
        img = Image.open(src).convert("RGB")
        # 使用原始高度生成，然后添加边距
        out = transform(img, out_w=HIRES_OUT_W, out_h=actual_h, extra_south_px=extra_south_px)
        out.save(dst, quality=95, optimize=True)
        print(f"  [OK] {floor} → {dst.name} ({out.size[1]}px)")
    print(f"  高分辨率图已存入: {HIRES_DIR.relative_to(BASE)}")


def _convert_node_coords() -> None:
    """将 wencui_building_v2.json 的节点坐标换算到统一校正坐标系"""
    src = BASE / "data/wencui_building_v2.json"
    if not src.exists():
        print("  [SKIP] wencui_building_v2.json 不存在，跳过节点换算")
        return

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    for nid, node in data["nodes"].items():
        ox, oy = node["x"], node["y"]
        ux, uy = orig_pixel_to_unified(ox, oy)
        coords = pixel_to_coords(ux, uy)
        node["ux"] = ux                          # 统一校正图像素 x
        node["uy"] = uy                          # 统一校正图像素 y
        node["east_m"]  = coords["x_east_m"]    # 距报告厅，东为正
        node["south_m"] = coords["y_south_m"]   # 距报告厅，南为正

    # 更新坐标系元数据
    data["unified_coordinate_system"] = {
        "image_dir": "data/floorplans_unified/",
        "origin": "圆形报告厅/圆楼中心",
        "origin_gps": HALL_GPS,
        "hall_pixel_in_unified_image": {"x": HALL_PX, "y": HALL_PY},
        "m_per_px": M_PER_PX,
        "node_fields": {
            "ux": "统一校正图 pixel_x",
            "uy": "统一校正图 pixel_y",
            "east_m":  "距报告厅 东为正（米）",
            "south_m": "距报告厅 南为正（米）",
        },
    }

    dst = BASE / "data/wencui_building_v3.json"
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 节点坐标换算 → wencui_building_v3.json")
    print(f"       节点总数: {len(data['nodes'])}")

    # 抽样验证
    samples = ["circular_hall_1F", "L-101", "G-130", "H-130", "A-301"]
    print("\n  抽样验证（east_m=0 应在报告厅列, south_m=0 应在报告厅行）:")
    for nid in samples:
        n = data["nodes"].get(nid)
        if n:
            print(f"    {nid}: ux={n['ux']}, uy={n['uy']}, "
                  f"east={n['east_m']}m, south={n['south_m']}m")


if __name__ == "__main__":
    main()
