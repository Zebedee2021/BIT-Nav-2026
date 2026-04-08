"""
导航案例生成器 - 上南下北显示
用途: 生成 start->end 的逐层路径地图
运行: python tools/gen_nav_case.py C-101 H-233
"""

import json, heapq, math, sys
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# ─── 坐标变换常量（与原始采集脚本一致）───
CROP   = (76, 100, 2841, 1820)   # 原图裁剪区域
CROP_W = CROP[2] - CROP[0]       # 2765
CROP_H = CROP[3] - CROP[1]       # 1720
OUT_W  = 745    # 统一坐标系宽（ux范围）
OUT_H  = 1205   # 统一坐标系高（uy范围）
SCALE  = 2      # 输出图放大倍数
DW, DH = OUT_W * SCALE, OUT_H * SCALE

FLOORPLAN_DIR = "data/floorplans"
FLOORPLAN_SUFFIX = "_official.jpg"

# ─── 上南下北显示变换 ───
# 背景: img.transpose(ROTATE_270)
# 节点: px = (OUT_W-1-ux)*SCALE, py = (OUT_H-1-uy)*SCALE
def to_px(ux, uy):
    return (int((OUT_W - 1 - ux) * SCALE), int((OUT_H - 1 - uy) * SCALE))

# ─── 加载数据 ───
with open("data/wencui_building_v6.json", encoding="utf-8") as f:
    raw = json.load(f)

nodes = raw["nodes"]
edges = raw["edges"]

FLOOR_CHANGE_PENALTY = 400   # 每次上/下一层的惩罚（坐标单位）

def floor_num(fl):
    try: return int(fl.replace("F",""))
    except: return 0

nb = defaultdict(list)
for e in edges:
    a, b = e[0], e[1]
    na, nb_ = nodes.get(a, {}), nodes.get(b, {})
    dux = na.get("ux", 0) - nb_.get("ux", 0)
    duy = na.get("uy", 0) - nb_.get("uy", 0)
    dist = math.sqrt(dux*dux + duy*duy) + 1
    # 跨层惩罚：每层加 FLOOR_CHANGE_PENALTY
    fa = floor_num(na.get("floor", "1F"))
    fb = floor_num(nb_.get("floor", "1F"))
    dist += abs(fa - fb) * FLOOR_CHANGE_PENALTY
    nb[a].append((b, dist))
    nb[b].append((a, dist))

# ─── A* 路径规划 ───
def heuristic(a, b):
    na, nb_ = nodes.get(a, {}), nodes.get(b, {})
    dux = na.get("ux", 0) - nb_.get("ux", 0)
    duy = na.get("uy", 0) - nb_.get("uy", 0)
    return math.sqrt(dux*dux + duy*duy)

def astar(start, end):
    if start not in nodes or end not in nodes:
        return None
    open_set = [(0, start)]
    came_from = {}
    g_score = defaultdict(lambda: float("inf"))
    g_score[start] = 0
    visited = set()
    while open_set:
        _, cur = heapq.heappop(open_set)
        if cur in visited:
            continue
        visited.add(cur)
        if cur == end:
            path = []
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            path.append(start)
            return list(reversed(path))
        for nxt, w in nb[cur]:
            if nxt in visited:
                continue
            # 跳过不可导航节点
            if nodes.get(nxt, {}).get("navigable") == False:
                continue
            tentative = g_score[cur] + w
            if tentative < g_score[nxt]:
                g_score[nxt] = tentative
                came_from[nxt] = cur
                f = tentative + heuristic(nxt, end)
                heapq.heappush(open_set, (f, nxt))
    return None

# ─── 绘制单层地图 ───
def draw_floor(floor, path_nodes, start_id, end_id, out_path, step_from, step_to):
    img_path = f"{FLOORPLAN_DIR}/{floor}{FLOORPLAN_SUFFIX}"
    try:
        img = Image.open(img_path).convert("RGB")
    except:
        img = Image.new("RGB", (CROP_W, CROP_H), (240, 240, 240))

    # 裁剪+旋转270°→上南下北
    try:
        cropped = img.crop(CROP)
        bg = cropped.transpose(Image.ROTATE_90).resize((DW, DH), Image.LANCZOS)
    except:
        bg = Image.new("RGB", (DW, DH), (240, 240, 240))

    draw = ImageDraw.Draw(bg)

    try:
        font_big  = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
        font_mid  = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
        font_sm   = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
    except:
        font_big = font_mid = font_sm = ImageFont.load_default()

    # ── 路径线 ──
    pts = []
    for nid in path_nodes:
        n = nodes.get(nid, {})
        ux, uy = n.get("ux", 0), n.get("uy", 0)
        pts.append(to_px(ux, uy))

    if len(pts) >= 2:
        # 按节点类型选线色
        for i in range(len(pts)-1):
            nid_a = path_nodes[i]
            nid_b = path_nodes[i+1]
            fl_a = nodes.get(nid_a, {}).get("floor", "")
            fl_b = nodes.get(nid_b, {}).get("floor", "")
            if fl_a == fl_b:
                color = (30, 120, 220)   # 蓝色：同层
            else:
                color = (200, 80, 20)    # 橙色：跨层（不应出现在单层图）
            draw.line([pts[i], pts[i+1]], fill=color, width=5)

    # ── 路径节点圆点 ──
    for i, nid in enumerate(path_nodes):
        n = nodes.get(nid, {})
        px, py = to_px(n.get("ux", 0), n.get("uy", 0))
        r = 7
        ntype = n.get("type", "")
        if "stair" in nid or "elevator" in nid:
            clr = (220, 140, 0)    # 橙：楼梯/电梯
            r = 9
        elif "corridor" in nid or "hall" in nid:
            clr = (60, 160, 60)    # 绿：走廊
            r = 6
        else:
            clr = (30, 120, 220)   # 蓝：房间
        draw.ellipse([px-r, py-r, px+r, py+r], fill=clr, outline="white", width=2)

    # ── 起点/终点标记 ──
    for nid, label, color in [(start_id, "起", (220,50,50)), (end_id, "终", (140,0,200))]:
        n = nodes.get(nid, {})
        if n.get("floor") != floor:
            continue
        px, py = to_px(n.get("ux", 0), n.get("uy", 0))
        r = 14
        draw.ellipse([px-r, py-r, px+r, py+r], fill=color, outline="white", width=3)
        draw.text((px, py), label, fill="white", font=font_big, anchor="mm")

    # ── 楼梯/电梯节点注释 ──
    for nid in path_nodes:
        n = nodes.get(nid, {})
        if n.get("floor") != floor:
            continue
        if "stair" in nid or "elevator" in nid:
            px, py = to_px(n.get("ux", 0), n.get("uy", 0))
            tag = "电梯" if "elevator" in nid else "楼梯"
            draw.text((px+12, py-6), tag, fill=(180, 100, 0), font=font_sm)

    # ── 步骤序号标注在走廊节点旁 ──
    step = step_from
    for nid in path_nodes:
        n = nodes.get(nid, {})
        if n.get("floor") != floor:
            continue
        if "corridor" in nid or "stair" in nid or "elevator" in nid:
            px, py = to_px(n.get("ux", 0), n.get("uy", 0))
            draw.text((px+10, py+4), str(step), fill=(80,80,80), font=font_sm)
            step += 1

    # ── 标题栏 ──
    title = f"{floor}  步骤 {step_from}-{step_to}"
    draw.rectangle([0, 0, DW, 36], fill=(30, 60, 120))
    draw.text((DW//2, 18), title, fill="white", font=font_big, anchor="mm")

    # ── 图例 ──
    legend_x, legend_y = 10, DH - 70
    draw.rectangle([legend_x-4, legend_y-4, legend_x+160, legend_y+62],
                   fill=(255,255,255,200), outline=(180,180,180))
    items = [
        ((220,50,50),  "起点"),
        ((140,0,200),  "终点"),
        ((30,120,220), "路径/房间"),
        ((60,160,60),  "走廊节点"),
        ((220,140,0),  "楼梯/电梯"),
    ]
    for i, (c, txt) in enumerate(items):
        y = legend_y + i*12
        draw.ellipse([legend_x, y, legend_x+10, y+10], fill=c)
        draw.text((legend_x+14, y), txt, fill=(40,40,40), font=font_sm)

    bg.save(out_path, quality=92)
    print(f"  保存: {out_path}")
    return bg

# ─── 主流程 ───
def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "C-101"
    end   = sys.argv[2] if len(sys.argv) > 2 else "H-233"

    print(f"\n=== 导航: {start} -> {end} ===")

    if start not in nodes:
        print(f"错误: 起点 {start} 不在数据中"); return
    if end not in nodes:
        print(f"错误: 终点 {end} 不在数据中"); return

    path = astar(start, end)
    if not path:
        print("无法找到路径！"); return

    print(f"路径共 {len(path)} 个节点")

    # 计算总距离
    total_dist = 0
    for i in range(len(path)-1):
        na = nodes.get(path[i], {})
        nb_ = nodes.get(path[i+1], {})
        dux = na.get("ux",0) - nb_.get("ux",0)
        duy = na.get("uy",0) - nb_.get("uy",0)
        total_dist += math.sqrt(dux*dux + duy*duy)
    print(f"路径长度（坐标单位）: {total_dist:.0f}")

    # 打印路径摘要
    print("\n路径节点:")
    cur_floor = None
    for i, nid in enumerate(path):
        fl = nodes.get(nid, {}).get("floor", "?")
        marker = f"[{fl}]" if fl != cur_floor else "      "
        if fl != cur_floor:
            cur_floor = fl
        print(f"  {i+1:3d}. {marker} {nid}")

    # 按楼层分组
    floors_order = []
    floor_nodes = defaultdict(list)
    for nid in path:
        fl = nodes.get(nid, {}).get("floor", "?")
        if not floors_order or floors_order[-1] != fl:
            floors_order.append(fl)
        floor_nodes[fl].append(nid)

    print(f"\n经过楼层: {floors_order}")

    # 生成每层地图
    print("\n生成路径地图:")
    step = 1
    imgs = []
    for fl in floors_order:
        fn = floor_nodes[fl]
        step_end = step + len(fn) - 1
        out = f"data/nav_{fl}_v3.jpg"
        img = draw_floor(fl, fn, start, end, out, step, step_end)
        imgs.append(img)
        step = step_end + 1

    # 生成拼接总览图
    if imgs:
        total_w = sum(im.width for im in imgs) + 10 * (len(imgs)-1)
        total_h = max(im.height for im in imgs)
        overview = Image.new("RGB", (total_w, total_h), (200, 200, 200))
        x = 0
        for im in imgs:
            overview.paste(im, (x, 0))
            x += im.width + 10
        overview.save("data/nav_overview_v3.jpg", quality=90)
        print(f"  保存总览: data/nav_overview_v3.jpg")

    print("\n完成!")

if __name__ == "__main__":
    main()
