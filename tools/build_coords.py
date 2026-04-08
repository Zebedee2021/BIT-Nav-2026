"""
build_coords.py
根据真实 GPS 数据为文萃楼各节点添加实际米坐标，并补全 G/H/B/M 区缺失房间。

坐标系（与平面图像素一一对应）
  原点 (0, 0) = 平面图左上角 = 建筑最北端、最东侧
  x 轴：向右（向南），单位：米
  y 轴：向下（向西），单位：米

像素 → 米换算（以 3000×2000 原始图为基准）：
  x_m = (pixel_x - PIX_X0) * SCALE_X
  y_m = (pixel_y - PIX_Y0) * SCALE_Y
"""

import json, math, copy

# ─── 真实 GPS 区域边界（来自 OpenStreetMap Overpass API）─────────────────────
ZONES_GPS = {
    "A": {"lat_min": 39.730942, "lat_max": 39.731628,
          "lon_min": 116.168180, "lon_max": 116.168515},
    "B": {"lat_min": 39.730232, "lat_max": 39.731139,
          "lon_min": 116.167757, "lon_max": 116.168583},
    "C": {"lat_min": 39.730236, "lat_max": 39.730521,
          "lon_min": 116.167936, "lon_max": 116.168371},
    "D": {"lat_min": 39.730351, "lat_max": 39.730522,
          "lon_min": 116.167560, "lon_max": 116.167939},
    "E": {"lat_min": 39.730244, "lat_max": 39.730526,
          "lon_min": 116.167121, "lon_max": 116.167562},
    "F": {"lat_min": 39.730689, "lat_max": 39.730889,
          "lon_min": 116.167319, "lon_max": 116.168084},
    "G": {"lat_min": 39.730248, "lat_max": 39.731147,
          "lon_min": 116.166838, "lon_max": 116.167705},
    "H": {"lat_min": 39.731564, "lat_max": 39.732402,
          "lon_min": 116.166912, "lon_max": 116.167708},
    "I": {"lat_min": 39.731807, "lat_max": 39.732007,
          "lon_min": 116.167307, "lon_max": 116.168071},
    "J": {"lat_min": 39.732138, "lat_max": 39.732402,
          "lon_min": 116.167081, "lon_max": 116.167581},
    "K": {"lat_min": 39.732135, "lat_max": 39.732293,
          "lon_min": 116.167579, "lon_max": 116.167897},
    "L": {"lat_min": 39.732132, "lat_max": 39.732394,
          "lon_min": 116.167895, "lon_max": 116.168333},
    "M": {"lat_min": 39.731564, "lat_max": 39.732395,
          "lon_min": 116.167775, "lon_max": 116.168556},
}

# ─── 全局边界 ─────────────────────────────────────────────────────────────────
LAT_MAX = max(v["lat_max"] for v in ZONES_GPS.values())   # 39.732402  最北
LAT_MIN = min(v["lat_min"] for v in ZONES_GPS.values())   # 39.730232  最南
LON_MAX = max(v["lon_max"] for v in ZONES_GPS.values())   # 116.168583 最东
LON_MIN = min(v["lon_min"] for v in ZONES_GPS.values())   # 116.166838 最西

# 比例尺
LAT_SCALE = 111_000                              # m/degree 纬度
LON_SCALE = 111_000 * math.cos(math.radians(39.731))  # ≈ 85 365 m/degree 经度

TOTAL_NS = (LAT_MAX - LAT_MIN) * LAT_SCALE      # 南北跨度 ≈ 240.9 m
TOTAL_EW = (LON_MAX - LON_MIN) * LON_SCALE      # 东西跨度 ≈ 149.0 m

# ─── 像素 → 米 换算参数（基于 3000×2000 原始平面图）────────────────────────
# 平面图方向：左←北，右→南；上←东，下→西
# 即：x_pixel 增加 = 向南；y_pixel 增加 = 向西
PIX_X0   = 76      # 左（北）边界像素
PIX_XMAX = 2841    # 右（南）边界像素
PIX_Y0   = 100     # 上（东）边界像素
PIX_YMAX = 1820    # 下（西）边界像素

SCALE_X = TOTAL_NS / (PIX_XMAX - PIX_X0)   # ≈ 0.0871 m/px
SCALE_Y = TOTAL_EW / (PIX_YMAX - PIX_Y0)   # ≈ 0.0866 m/px

def pix2m(px: float, py: float) -> tuple[float, float]:
    """像素坐标 → 实际米坐标（保留 1 位小数）"""
    return round((px - PIX_X0) * SCALE_X, 1), round((py - PIX_Y0) * SCALE_Y, 1)

def m2pix(xm: float, ym: float) -> tuple[int, int]:
    """实际米坐标 → 像素坐标"""
    return round(xm / SCALE_X + PIX_X0), round(ym / SCALE_Y + PIX_Y0)

def gps2m(lat: float, lon: float) -> tuple[float, float]:
    """GPS → 本地米坐标"""
    return round((LAT_MAX - lat) * LAT_SCALE, 1), round((LON_MAX - lon) * LON_SCALE, 1)


# ─── 计算各区本地坐标范围 ─────────────────────────────────────────────────────
def zone_local_bounds(z: str) -> dict:
    g = ZONES_GPS[z]
    x_min, y_min = gps2m(g["lat_max"], g["lon_max"])  # 北端最东 = 左上
    x_max, y_max = gps2m(g["lat_min"], g["lon_min"])  # 南端最西 = 右下
    return {
        "gps": g,
        "x_min_m": x_min, "x_max_m": x_max,
        "y_min_m": y_min, "y_max_m": y_max,
        "width_m":  round(x_max - x_min, 1),
        "height_m": round(y_max - y_min, 1),
    }


# ─── G / H / B / M 区补全数据 ────────────────────────────────────────────────
# 从平面图目测像素坐标，房间中心点（原始 3000×2000 尺度）
# G区 (x: 139~239m, y: 75~149m) → pixel x: 1675~2817, y: 966~1820
EXTRA_NODES = {
    # ── G 区 1F ──────────────────────────────────────────────────────────────
    # 底部横向排 (y≈1820, 西侧)：实际只有 G-123~126 在底条
    # G-127~129 重定位为内部房间，G-130 为大房间
    "G-127":    {"zone":"G","floor":"1F","type":"room","px":2281,"py":1650},
    "G-128":    {"zone":"G","floor":"1F","type":"room","px":2455,"py":1650},
    "G-129":    {"zone":"G","floor":"1F","type":"room","px":2628,"py":1650},
    # G-130 = 大型内部房间（东北侧），坐标修正
    # 原像素 (2802,1820) 错误，修正为：
    "_fix_G-130": {"px": 2200, "py": 1480},

    # 1F 休息区（G区西南入口区域）
    "lounge_1F_G": {"zone":"G","floor":"1F","type":"lounge",
                    "name":"G-1F休息区","px":1750,"py":1520},
    # G区 1F 楼梯（平面图中可见2处）
    "stairs_G_1_1F": {"zone":"G","floor":"1F","type":"stairs","px":1940,"py":1820},
    "stairs_G_2_1F": {"zone":"G","floor":"1F","type":"stairs","px":2280,"py":1820},
    # G区 1F 走廊节点（内部）
    "corridor_inner_1F_G": {"zone":"G","floor":"1F","type":"corridor","px":2100,"py":1560},

    # ── G 区 2F 补充 ──────────────────────────────────────────────────────────
    # G-226 缺失
    "G-226":    {"zone":"G","floor":"2F","type":"room","px":2195,"py":1820},
    # G-232/233 上楼层延伸（目前只有2F，不存在3F+）
    "stairs_G_1_2F": {"zone":"G","floor":"2F","type":"stairs","px":1940,"py":1820},
    "stairs_G_2_2F": {"zone":"G","floor":"2F","type":"stairs","px":2280,"py":1820},
    "corridor_inner_2F_G": {"zone":"G","floor":"2F","type":"corridor","px":2100,"py":1560},
    "lounge_2F_G": {"zone":"G","floor":"2F","type":"lounge",
                    "name":"G-2F休息区","px":1750,"py":1520},

    # ── H 区 1F ──────────────────────────────────────────────────────────────
    # H-127~129 重定位为内部房间
    "H-127":    {"zone":"H","floor":"1F","type":"room","px":200,"py":1650},
    "H-128":    {"zone":"H","floor":"1F","type":"room","px":350,"py":1650},
    "H-129":    {"zone":"H","floor":"1F","type":"room","px":500,"py":1650},
    # H-130 修正为大型内部房间（原(651,1820)→修正）
    "_fix_H-130": {"px": 460, "py": 1480},
    # H区 卫生间
    "toilet_1F_H": {"zone":"H","floor":"1F","type":"toilet",
                    "name":"卫生间","px":200,"py":1480},
    # H区楼梯
    "stairs_H_1_1F": {"zone":"H","floor":"1F","type":"stairs","px":260,"py":1820},
    # H区走廊（内部）
    "corridor_inner_1F_H": {"zone":"H","floor":"1F","type":"corridor","px":390,"py":1560},

    # ── H 区 2F ──────────────────────────────────────────────────────────────
    # H-223 / H-224 缺失
    "H-223":    {"zone":"H","floor":"2F","type":"room","px":260,"py":1820},
    "H-224":    {"zone":"H","floor":"2F","type":"room","px":338,"py":1820},
    "H-226":    {"zone":"H","floor":"2F","type":"room","px":468,"py":1820},
    "stairs_H_1_2F": {"zone":"H","floor":"2F","type":"stairs","px":260,"py":1820},
    "corridor_inner_2F_H": {"zone":"H","floor":"2F","type":"corridor","px":390,"py":1560},
    "lounge_2F_H": {"zone":"H","floor":"2F","type":"lounge",
                    "name":"H-2F休息区","px":200,"py":1520},

    # ── B 区 1F ──────────────────────────────────────────────────────────────
    # B-135 修正为内部大房间（原(2256,110)→修正）
    "_fix_B-135": {"px": 2100, "py": 380},
    # B-139, B-140 修正为内部房间
    "_fix_B-139": {"px": 2540, "py": 380},
    "_fix_B-140": {"px": 2700, "py": 380},
    # B区 卫生间
    "toilet_1F_B": {"zone":"B","floor":"1F","type":"toilet",
                    "name":"卫生间","px":1820,"py":280},
    # B区 电梯厅
    "elevator_B_1F": {"zone":"B","floor":"1F","type":"elevator",
                      "name":"B区电梯厅","px":1960,"py":200},
    # B区走廊（内部）
    "corridor_inner_1F_B": {"zone":"B","floor":"1F","type":"corridor","px":2160,"py":260},

    # ── B 区 2F ──────────────────────────────────────────────────────────────
    "toilet_2F_B": {"zone":"B","floor":"2F","type":"toilet",
                    "name":"卫生间","px":1820,"py":280},
    "elevator_B_2F": {"zone":"B","floor":"2F","type":"elevator",
                      "name":"B区电梯厅","px":1960,"py":200},
    "corridor_inner_2F_B": {"zone":"B","floor":"2F","type":"corridor","px":2160,"py":260},

    # ── M 区 1F ──────────────────────────────────────────────────────────────
    # M-130 修正为内部大房间（原(615,100)→修正）
    "_fix_M-130": {"px": 620, "py": 380},
    # M-134, M-135 修正为内部房间
    "_fix_M-134": {"px": 810, "py": 380},
    "_fix_M-135": {"px": 900, "py": 380},
    # M区 电梯厅
    "elevator_M_1F": {"zone":"M","floor":"1F","type":"elevator",
                      "name":"M区电梯厅","px":490,"py":200},
    # M区走廊（内部）
    "corridor_inner_1F_M": {"zone":"M","floor":"1F","type":"corridor","px":555,"py":260},

    # ── M 区 2F ──────────────────────────────────────────────────────────────
    "elevator_M_2F": {"zone":"M","floor":"2F","type":"elevator",
                      "name":"M区电梯厅","px":490,"py":200},
    "corridor_inner_2F_M": {"zone":"M","floor":"2F","type":"corridor","px":555,"py":260},
}

# 补充跨楼层连通性（楼梯节点 3F+ 延伸，连接至周边高层区）
EXTRA_STAIRS_FLOORS = {
    "stairs_G_1": {"zone":"G","px":1940,"py":1820, "floors":["1F","2F"]},
    "stairs_G_2": {"zone":"G","px":2280,"py":1820, "floors":["1F","2F"]},
    "stairs_H_1": {"zone":"H","px":260, "py":1820, "floors":["1F","2F"]},
}


# ─── 主处理函数 ───────────────────────────────────────────────────────────────
def main():
    src = "E:/2025-2026-2/BIT-Nav-2026/data/wencui_building.json"
    dst = "E:/2025-2026-2/BIT-Nav-2026/data/wencui_building_v2.json"

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    nodes  = data["nodes"]
    edges  = data["edges"]
    fl_lay = data["floor_layouts"]

    # ── 1. 为所有现有节点添加 x_m / y_m ──────────────────────────────────────
    for nid, node in nodes.items():
        xm, ym = pix2m(node["x"], node["y"])
        node["x_m"] = xm
        node["y_m"] = ym

    # ── 2. 应用位置修正（_fix_ 前缀）────────────────────────────────────────
    fixes = {k[5:]: v for k, v in EXTRA_NODES.items() if k.startswith("_fix_")}
    for nid, fix in fixes.items():
        if nid in nodes:
            nodes[nid]["x"]   = fix["px"]
            nodes[nid]["y"]   = fix["py"]
            nodes[nid]["x_m"], nodes[nid]["y_m"] = pix2m(fix["px"], fix["py"])
            print(f"  [FIX] {nid}: → pixel({fix['px']},{fix['py']}) "
                  f"= ({nodes[nid]['x_m']}m, {nodes[nid]['y_m']}m)")
        else:
            print(f"  [WARN] _fix_ target {nid} not found in nodes")

    # ── 3. 添加新节点（非 _fix_ 前缀）────────────────────────────────────────
    new_edges = []
    for nid, nd in EXTRA_NODES.items():
        if nid.startswith("_fix_"):
            continue
        if nid in nodes:
            continue  # 已存在，跳过

        px, py = nd["px"], nd["py"]
        xm, ym = pix2m(px, py)
        nodes[nid] = {
            "id":    nid,
            "type":  nd.get("type", "room"),
            "floor": nd["floor"],
            "zone":  nd["zone"],
            "name":  nd.get("name", nid),
            "description": "",
            "x": px, "y": py,
            "x_m": xm, "y_m": ym,
        }

        # 自动连接至同区同楼层走廊节点
        corr_id = f"corridor_{nd['floor']}_{nd['zone']}"
        inner_corr = f"corridor_inner_{nd['floor']}_{nd['zone']}"
        for cid in [corr_id, inner_corr]:
            if cid in nodes:
                edge = [nid, cid]
                if edge not in edges and edge[::-1] not in edges:
                    new_edges.append(edge)
                break

        print(f"  [ADD] {nid} @ ({xm}m, {ym}m)  floor={nd['floor']} zone={nd['zone']}")

    edges.extend(new_edges)

    # ── 4. 添加区域元数据 ────────────────────────────────────────────────────
    data["coordinate_system"] = {
        "description": "本地平面坐标系，原点(0,0)=平面图左上角(建筑最北、最东端)",
        "origin_gps":  {"lat": LAT_MAX, "lon": LON_MAX},
        "x_axis":      "向右=向南(纬度减小)，单位: 米",
        "y_axis":      "向下=向西(经度减小)，单位: 米",
        "total_x_m":   round(TOTAL_NS, 1),
        "total_y_m":   round(TOTAL_EW, 1),
        "pixel_origin": {"x": PIX_X0, "y": PIX_Y0},
        "scale_x_m_per_px": round(SCALE_X, 6),
        "scale_y_m_per_px": round(SCALE_Y, 6),
    }

    data["zones"] = {z: zone_local_bounds(z) for z in ZONES_GPS}

    # ── 5. 更新 floor_layouts ────────────────────────────────────────────────
    for fl, layout in fl_lay.items():
        layout["image_width_px"]  = 3000
        layout["image_height_px"] = 2000
        layout["coord_origin_px"] = {"x": PIX_X0, "y": PIX_Y0}
        layout["scale_m_per_px"]  = round(SCALE_X, 6)

    # ── 6. 统计 & 写出 ────────────────────────────────────────────────────────
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 写出: {dst}")
    print(f"  节点总数: {len(nodes)}")
    print(f"  边总数:   {len(edges)}")
    print(f"  新增节点: {len([k for k in EXTRA_NODES if not k.startswith('_fix_')])}")
    print(f"  位置修正: {len(fixes)}")


if __name__ == "__main__":
    main()
