"""
room_verifier.py — 房间位置校对工具
左边选房间，右边图片圈出位置，支持人工确认/纠正
"""
import json, math
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageTk

# ── 路径 ──────────────────────────────────────────────────────
BASE     = Path("E:/2025-2026-2/BIT-Nav-2026")
SRC_JSON = BASE / "data/wencui_building_v7.json"
PLAN_DIR = BASE / "data/floorplans_hires"  # 使用高清楼层图

# ── 坐标变换常量 ───────────────────────────────────────────────
# unified 坐标系：5px/m，原点 (164, 610)，尺寸 745x1304
# hires 坐标系：15px/m，原点 (492, 1830)，尺寸 2235x3913 (增加了 20m south 边距)
# 比例：hires = unified * 3
# 注意：hires 图在底部增加了 300px (20m) 的白色边距，原点保持不变
# 原点来自 unified_params.json

UNIFIED_SCALE = 0.2   # m/px (unified)
UNIFIED_PX_PER_M = 5  # px/m (unified)
HIRES_PX_PER_M = 15   # px/m (hires)
SCALE_RATIO = HIRES_PX_PER_M / UNIFIED_PX_PER_M  # 3

# unified 原点（来自 unified_params.json）
UNIFIED_ORIGIN_X = 164  # hall_pixel.x
UNIFIED_ORIGIN_Y = 610  # hall_pixel.y

# hires 原点（按比例计算）
HIRES_ORIGIN_X = UNIFIED_ORIGIN_X * SCALE_RATIO  # 492
HIRES_ORIGIN_Y = UNIFIED_ORIGIN_Y * SCALE_RATIO  # 1830

def meters_to_hires_px(east_m, south_m, img_w, img_h):
    """
    米制坐标 -> hires 像素坐标
    east_m: 东为正（米）
    south_m: 南为正（米）
    """
    # 米 -> hires 像素（使用 hires 原点）
    px = HIRES_ORIGIN_X + east_m * HIRES_PX_PER_M
    py = HIRES_ORIGIN_Y + south_m * HIRES_PX_PER_M
    
    return round(px), round(py)

def hires_px_to_meters(px, py, img_w, img_h):
    """
    hires 像素坐标 -> 米制坐标
    """
    east_m = (px - HIRES_ORIGIN_X) / HIRES_PX_PER_M
    south_m = (py - HIRES_ORIGIN_Y) / HIRES_PX_PER_M
    
    return round(east_m, 2), round(south_m, 2)

# ── 状态颜色 ───────────────────────────────────────────────────
STATUS_COLORS = {
    "verified_ok":      "#4CAF50",   # 绿 — 人工确认正确
    "verified_fixed":   "#2196F3",   # 蓝 — 人工纠正
    "ocr_conf":         "#FF9800",   # 橙 — OCR 确认（待校对）
    "predicted":        "#9E9E9E",   # 灰 — 仅预测
    "no_pos":           "#F44336",   # 红 — 无坐标
}

def node_status(v):
    if v.get("verified_ok"):
        return "verified_ok"
    if v.get("verified_fixed"):
        return "verified_fixed"
    if "ocr_conf" in v:
        return "ocr_conf"
    if v.get("ux") is not None:
        return "predicted"
    return "no_pos"

class RoomVerifier(Tk):
    def __init__(self):
        super().__init__()
        self.title("文萃楼房间位置校对工具")
        self.geometry("1400x860")
        self.resizable(True, True)

        with open(SRC_JSON, encoding="utf-8") as f:
            self.data = json.load(f)
        self.nodes = self.data["nodes"]

        # 状态
        self.current_nid    = None
        self.floor_img_orig = None   # 原始 PIL 图（全尺寸）
        self.photo          = None
        self.base_scale     = 1.0    # 适配 canvas 的基础缩放
        self.zoom_factor    = 1.0    # 用户滚轮缩放倍数
        self.view_center    = (0.0, 0.0)  # 当前视图中心在原始图像中的坐标
        self.placing_mode   = False  # 等待用户点击纠正位置
        self._drag_start    = None   # 拖拽起点

        self._build_ui()
        self._populate_list()

    # ── UI 构建 ────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── 左侧面板 ──
        left = Frame(self, width=280, bg="#F5F5F5")
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)
        left.grid_propagate(False)

        Label(left, text="筛选", bg="#F5F5F5", font=("微软雅黑", 10)).pack(anchor="w", padx=6, pady=(6,0))

        filter_frame = Frame(left, bg="#F5F5F5")
        filter_frame.pack(fill="x", padx=6)

        Label(filter_frame, text="楼区:", bg="#F5F5F5").grid(row=0, column=0, sticky="w")
        self.zone_var = StringVar(value="全部")
        zones = ["全部"] + sorted({v.get("zone","?") for v in self.nodes.values() if v.get("zone")})
        self.zone_cb = ttk.Combobox(filter_frame, textvariable=self.zone_var,
                                    values=zones, width=6, state="readonly")
        self.zone_cb.grid(row=0, column=1, sticky="w", padx=4)
        self.zone_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_list())

        Label(filter_frame, text="楼层:", bg="#F5F5F5").grid(row=0, column=2, sticky="w")
        self.floor_var = StringVar(value="全部")
        floors = ["全部"] + [f"{n}F" for n in range(1,11)]
        self.floor_cb = ttk.Combobox(filter_frame, textvariable=self.floor_var,
                                     values=floors, width=5, state="readonly")
        self.floor_cb.grid(row=0, column=3, sticky="w")
        self.floor_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_list())

        Label(filter_frame, text="状态:", bg="#F5F5F5").grid(row=1, column=0, sticky="w", pady=2)
        self.status_var = StringVar(value="全部")
        statuses = ["全部", "待校对(OCR)", "已确认", "已纠正", "仅预测", "无坐标"]
        self.status_cb = ttk.Combobox(filter_frame, textvariable=self.status_var,
                                      values=statuses, width=10, state="readonly")
        self.status_cb.grid(row=1, column=1, columnspan=3, sticky="w", padx=4)
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_list())

        Label(filter_frame, text="搜索:", bg="#F5F5F5").grid(row=2, column=0, sticky="w")
        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *a: self._populate_list())
        Entry(filter_frame, textvariable=self.search_var, width=18).grid(
            row=2, column=1, columnspan=3, sticky="w", padx=4, pady=2)

        # 列表
        list_frame = Frame(left)
        list_frame.pack(fill="both", expand=True, padx=6, pady=4)
        sb = Scrollbar(list_frame)
        sb.pack(side="right", fill="y")
        self.listbox = Listbox(list_frame, yscrollcommand=sb.set,
                               font=("Consolas", 10), activestyle="dotbox",
                               selectbackground="#1976D2", selectforeground="white")
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # 图例
        legend = Frame(left, bg="#F5F5F5")
        legend.pack(fill="x", padx=6, pady=4)
        for text, color in [("✓ 已确认正确","#4CAF50"),("✎ 已纠正","#2196F3"),
                             ("○ OCR待校对","#FF9800"),("· 仅预测","#9E9E9E"),("✗ 无坐标","#F44336")]:
            f = Frame(legend, bg="#F5F5F5")
            f.pack(anchor="w")
            Label(f, text="■", fg=color, bg="#F5F5F5", font=("Arial",10)).pack(side="left")
            Label(f, text=text, bg="#F5F5F5", font=("微软雅黑",9)).pack(side="left")

        self.count_label = Label(left, text="", bg="#F5F5F5", font=("微软雅黑", 9), fg="#555")
        self.count_label.pack(padx=6, pady=2)

        # ── 右侧面板 ──
        right = Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # 信息栏
        info_frame = Frame(right, bg="#ECEFF1", height=60)
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0,4))
        info_frame.grid_propagate(False)
        self.info_var = StringVar(value="← 请从左侧选择一个房间")
        Label(info_frame, textvariable=self.info_var, bg="#ECEFF1",
              font=("微软雅黑", 11), justify="left", anchor="w").pack(
              fill="both", expand=True, padx=10)

        # Canvas（显示平面图）
        self.canvas = Canvas(right, bg="#333", cursor="crosshair")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>",    self._on_canvas_resize)
        # 鼠标事件绑定
        self.canvas.bind("<Button-1>",     self._on_canvas_click)
        self.canvas.bind("<ButtonPress-2>",   self._on_drag_start)  # 中键拖动
        self.canvas.bind("<B2-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonPress-3>",   self._on_drag_start)  # 右键拖动
        self.canvas.bind("<B3-Motion>",       self._on_drag)
        self.canvas.bind("<MouseWheel>",   self._on_mousewheel)   # Windows
        self.canvas.bind("<Button-4>",     self._on_mousewheel)   # Linux scroll up
        self.canvas.bind("<Button-5>",     self._on_mousewheel)   # Linux scroll down
        
        # 手型拖动模式（Ctrl+左键拖动）
        self.canvas.bind("<Control-ButtonPress-1>", self._on_hand_drag_start)
        self.canvas.bind("<Control-B1-Motion>",     self._on_hand_drag)
        self.canvas.bind("<Control-ButtonRelease-1>", self._on_hand_drag_end)

        # 按钮栏
        btn_frame = Frame(right, bg="#ECEFF1", height=52)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(4,0))
        btn_frame.grid_propagate(False)

        self.btn_ok = Button(btn_frame, text="✓ 位置正确", bg="#4CAF50", fg="white",
                             font=("微软雅黑",11,"bold"), width=12,
                             command=self._mark_ok, state=DISABLED)
        self.btn_ok.pack(side="left", padx=8, pady=8)

        self.btn_fix = Button(btn_frame, text="✎ 点击纠正位置", bg="#2196F3", fg="white",
                              font=("微软雅黑",11,"bold"), width=14,
                              command=self._start_fix, state=DISABLED)
        self.btn_fix.pack(side="left", padx=4, pady=8)

        self.btn_cancel = Button(btn_frame, text="取消纠正", bg="#9E9E9E", fg="white",
                                 font=("微软雅黑",10), width=8,
                                 command=self._cancel_fix, state=DISABLED)
        self.btn_cancel.pack(side="left", padx=4, pady=8)

        self.btn_wrong = Button(btn_frame, text="✗ 标记无法确定", bg="#F44336", fg="white",
                                font=("微软雅黑",10), width=12,
                                command=self._mark_uncertain, state=DISABLED)
        self.btn_wrong.pack(side="left", padx=4, pady=8)

        self.btn_save = Button(btn_frame, text="💾 保存", bg="#607D8B", fg="white",
                               font=("微软雅黑",11,"bold"), width=8,
                               command=self._save)
        self.btn_save.pack(side="right", padx=8, pady=8)

        self.btn_prev = Button(btn_frame, text="◀ 上一个", font=("微软雅黑",10),
                               width=8, command=self._prev_room)
        self.btn_prev.pack(side="right", padx=2, pady=8)

        self.btn_next = Button(btn_frame, text="▶ 下一个", font=("微软雅黑",10),
                               width=8, command=self._next_room)
        self.btn_next.pack(side="right", padx=2, pady=8)

        # 栅格显示/隐藏按钮
        self._show_grid = False
        self.btn_grid = Button(btn_frame, text="📐 栅格:关", bg="#9E9E9E", fg="white",
                               font=("微软雅黑",10,"bold"), width=10,
                               command=self._toggle_grid)
        self.btn_grid.pack(side="right", padx=4, pady=8)

        # 放大到房间按钮
        self.btn_zoom_room = Button(btn_frame, text="🔍 放大到房间", bg="#9C27B0", fg="white",
                                    font=("微软雅黑",10,"bold"), width=12,
                                    command=self._zoom_to_room)
        self.btn_zoom_room.pack(side="right", padx=4, pady=8)

        # 手型拖动按钮
        self.btn_hand = Button(btn_frame, text="✋ 手型拖动", bg="#FF9800", fg="white",
                               font=("微软雅黑",10,"bold"), width=10,
                               command=self._toggle_hand_mode)
        self.btn_hand.pack(side="right", padx=8, pady=8)

        self.status_bar = Label(right, text="就绪 | 提示：Ctrl+左键拖动地图，滚轮缩放", bg="#78909C", fg="white",
                                font=("微软雅黑",9), anchor="w")
        self.status_bar.grid(row=3, column=0, sticky="ew")

    # ── 列表填充 ───────────────────────────────────────────────
    def _populate_list(self):
        zone_f  = self.zone_var.get()
        floor_f = self.floor_var.get()
        stat_f  = self.status_var.get()
        search  = self.search_var.get().strip().upper()

        status_map = {
            "待校对(OCR)": "ocr_conf",
            "已确认":      "verified_ok",
            "已纠正":      "verified_fixed",
            "仅预测":      "predicted",
            "无坐标":      "no_pos",
        }

        self.filtered_ids = []
        for nid, v in sorted(self.nodes.items()):
            if v.get("type") not in ("room", None) and v.get("type") != "room":
                if "corridor" in nid or "hall" in nid:
                    continue
            if zone_f  != "全部" and v.get("zone") != zone_f:   continue
            if floor_f != "全部" and v.get("floor") != floor_f: continue
            st = node_status(v)
            if stat_f != "全部" and st != status_map.get(stat_f, stat_f): continue
            if search and search not in nid.upper():              continue
            self.filtered_ids.append(nid)

        self.listbox.delete(0, END)
        color_map = {
            "verified_ok":    "#4CAF50",
            "verified_fixed": "#2196F3",
            "ocr_conf":       "#FF9800",
            "predicted":      "#9E9E9E",
            "no_pos":         "#F44336",
        }
        prefix_map = {
            "verified_ok": "✓ ", "verified_fixed": "✎ ",
            "ocr_conf": "○ ", "predicted": "· ", "no_pos": "✗ ",
        }
        for nid in self.filtered_ids:
            st = node_status(self.nodes[nid])
            self.listbox.insert(END, f"{prefix_map[st]}{nid}")
            self.listbox.itemconfig(END, fg=color_map[st])

        self.count_label.config(text=f"共 {len(self.filtered_ids)} 条")

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        nid = self.filtered_ids[sel[0]]
        self._load_room(nid)

    def _prev_room(self):
        if not self.filtered_ids or self.current_nid is None:
            return
        idx = self.filtered_ids.index(self.current_nid) if self.current_nid in self.filtered_ids else -1
        if idx > 0:
            self._select_by_index(idx - 1)

    def _next_room(self):
        if not self.filtered_ids or self.current_nid is None:
            return
        idx = self.filtered_ids.index(self.current_nid) if self.current_nid in self.filtered_ids else -1
        if idx < len(self.filtered_ids) - 1:
            self._select_by_index(idx + 1)

    def _select_by_index(self, idx):
        self.listbox.selection_clear(0, END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self._load_room(self.filtered_ids[idx])

    # ── 加载房间 ───────────────────────────────────────────────
    def _load_room(self, nid):
        self._cancel_fix()
        self.current_nid = nid
        v = self.nodes[nid]

        floor = v.get("floor", "3F")
        img_path = PLAN_DIR / f"{floor}_hires.jpg"  # 高清楼层图命名格式
        if not img_path.exists():
            self.status_bar.config(text=f"图片不存在: {img_path}")
            return

        self.floor_img_orig = Image.open(img_path).convert("RGB")
        iw, ih = self.floor_img_orig.size

        # 初始化视图：先显示整张图，以图片中心为视图中心
        self.zoom_factor = 1.0
        
        if v.get("east_m") is not None and v.get("south_m") is not None:
            # 使用 east_m/south_m 直接计算像素位置作为视图中心
            cx, cy = meters_to_hires_px(v["east_m"], v["south_m"], iw, ih)
            self.view_center = (float(cx), float(cy))
        else:
            self.view_center = (iw / 2.0, ih / 2.0)

        # 信息栏
        st = node_status(v)
        st_text = {"verified_ok":"已确认正确","verified_fixed":"已纠正",
                   "ocr_conf":"OCR待校对","predicted":"仅预测","no_pos":"无坐标"}.get(st, st)
        east  = v.get("east_m", "?")
        south = v.get("south_m", "?")
        raw   = v.get("ocr_raw", "")
        conf  = v.get("ocr_conf", "")
        raw_info = f"  ocr: {raw!r} ({conf})" if raw else ""
        self.info_var.set(
            f"房间: {nid}  楼层: {floor}  状态: {st_text}  "
            f"east={east}m  south={south}m{raw_info}"
        )

        # 启用按钮
        for btn in (self.btn_ok, self.btn_fix, self.btn_wrong):
            btn.config(state=NORMAL)

        self._render_image()

    def _canvas_to_orig(self, cx, cy):
        """Canvas 像素坐标 → 原始图像像素坐标"""
        total = self.base_scale * self.zoom_factor
        cw = self.canvas.winfo_width() or 900
        ch = self.canvas.winfo_height() or 700
        pan_x = cw / 2 - self.view_center[0] * total
        pan_y = ch / 2 - self.view_center[1] * total
        return (cx - pan_x) / total, (cy - pan_y) / total

    def _render_image(self):
        if not self.floor_img_orig or not self.current_nid:
            return
        v = self.nodes[self.current_nid]

        cw = self.canvas.winfo_width()  or 900
        ch = self.canvas.winfo_height() or 700
        iw, ih = self.floor_img_orig.size

        # 基础缩放（适配 canvas）
        self.base_scale = min(cw / iw, ch / ih)
        total = self.base_scale * self.zoom_factor

        # 图像在 canvas 上的左上角偏移
        pan_x = cw / 2 - self.view_center[0] * total
        pan_y = ch / 2 - self.view_center[1] * total

        # 计算可见区域（裁剪原始图的哪个部分）
        src_x0 = max(0, -pan_x / total)
        src_y0 = max(0, -pan_y / total)
        src_x1 = min(iw, (cw - pan_x) / total)
        src_y1 = min(ih, (ch - pan_y) / total)
        if src_x1 <= src_x0 or src_y1 <= src_y0:
            return

        # 先在原图上画圈（确保标记在裁剪前绘制）
        img_with_mark = self.floor_img_orig.copy()
        draw = ImageDraw.Draw(img_with_mark)
        
        # 绘制坐标轴和栅格（如果启用）
        if getattr(self, '_show_grid', False):
            self._draw_grid(draw, iw, ih)
        
        if v.get("east_m") is not None and v.get("south_m") is not None:
            ox, oy = meters_to_hires_px(v["east_m"], v["south_m"], iw, ih)
            st = node_status(v)
            color = {"verified_ok":"#4CAF50","verified_fixed":"#2196F3",
                     "ocr_conf":"#FF6600","predicted":"#AAAAAA","no_pos":"#FF0000"}.get(st,"red")
            # 圆圈半径随 zoom 稍微变大，但不超过固定上限
            r = max(20, min(55, round(55 / self.zoom_factor)))
            lw = max(3, min(8, round(8 / self.zoom_factor)))
            draw.ellipse([ox-r, oy-r, ox+r, oy+r], outline=color, width=lw)
            arm = round(r * 1.5)
            draw.line([ox-arm, oy, ox+arm, oy], fill=color, width=lw)
            draw.line([ox, oy-arm, ox, oy+arm], fill=color, width=lw)

        # 裁剪可见区域（从带标记的图）
        region = img_with_mark.crop((int(src_x0), int(src_y0),
                                     math.ceil(src_x1), math.ceil(src_y1)))

        # 缩放到屏幕像素
        dst_w = round((src_x1 - src_x0) * total)
        dst_h = round((src_y1 - src_y0) * total)
        if dst_w < 1 or dst_h < 1:
            return
        resample = Image.NEAREST if total > 3 else Image.LANCZOS
        region_scaled = region.resize((dst_w, dst_h), resample)

        self.photo = ImageTk.PhotoImage(region_scaled)
        self.canvas.delete("all")
        dst_x = round(pan_x + src_x0 * total)
        dst_y = round(pan_y + src_y0 * total)
        self.canvas.create_image(dst_x, dst_y, anchor="nw", image=self.photo)

        # 提示文字
        if self.placing_mode:
            self.canvas.create_text(cw//2, 24, text="请点击正确位置  |  滚轮放大后再点",
                                    fill="yellow", font=("微软雅黑",13,"bold"))
        # 缩放比例提示
        zoom_pct = round(self.zoom_factor * 100)
        self.canvas.create_text(cw - 6, ch - 6, anchor="se",
                                text=f"缩放: {zoom_pct}%  (滚轮缩放 / 右键拖动)",
                                fill="#AAAAAA", font=("微软雅黑", 9))

        self.status_bar.config(
            text=f"{self.current_nid}  |  {v.get('floor','?')}  |  {node_status(v)}"
        )

    def _on_canvas_resize(self, event):
        self._render_image()

    def _on_mousewheel(self, event):
        """滚轮缩放，以鼠标位置为中心"""
        if event.num == 4:      # Linux scroll up
            delta = 1
        elif event.num == 5:    # Linux scroll down
            delta = -1
        else:                   # Windows
            delta = 1 if event.delta > 0 else -1

        factor = 1.25 if delta > 0 else 1 / 1.25
        new_zoom = max(0.5, min(16.0, self.zoom_factor * factor))

        cw = self.canvas.winfo_width() or 900
        ch = self.canvas.winfo_height() or 700

        # 鼠标在原始图上的坐标（保持不动）
        orig_x, orig_y = self._canvas_to_orig(event.x, event.y)

        self.zoom_factor = new_zoom
        total = self.base_scale * new_zoom
        # 新 view_center 使 orig_x/y 仍映射到 event.x/y
        self.view_center = (
            orig_x - (event.x - cw / 2) / total,
            orig_y - (event.y - ch / 2) / total,
        )
        self._render_image()

    def _on_drag_start(self, event):
        """右键/中键拖动开始"""
        self._drag_start = (event.x, event.y, *self.view_center)
        self.canvas.config(cursor="fleur")

    def _on_drag(self, event):
        """右键/中键拖动平移"""
        if not self._drag_start:
            return
        sx, sy, vcx, vcy = self._drag_start
        total = self.base_scale * self.zoom_factor
        self.view_center = (
            vcx - (event.x - sx) / total,
            vcy - (event.y - sy) / total,
        )
        self._render_image()
        if not self.placing_mode:
            self.canvas.config(cursor="fleur")

    # ── 手型拖动模式（Ctrl+左键）────────────────────────────────
    def _on_hand_drag_start(self, event):
        """手型拖动开始 - Ctrl+左键"""
        self._hand_drag_start = (event.x, event.y, *self.view_center)
        self.canvas.config(cursor="hand2")  # 手型光标
        self.status_bar.config(text="手型拖动模式 - 拖动地图到合适位置")

    def _on_hand_drag(self, event):
        """手型拖动中"""
        if not getattr(self, '_hand_drag_start', None):
            return
        sx, sy, vcx, vcy = self._hand_drag_start
        total = self.base_scale * self.zoom_factor
        self.view_center = (
            vcx - (event.x - sx) / total,
            vcy - (event.y - sy) / total,
        )
        self._render_image()

    def _on_hand_drag_end(self, event):
        """手型拖动结束"""
        self._hand_drag_start = None
        self.canvas.config(cursor="crosshair")
        self.status_bar.config(text="就绪 | 提示：Ctrl+左键拖动地图，滚轮缩放")

    def _draw_grid(self, draw, img_w, img_h):
        """绘制坐标轴和栅格"""
        # 原点像素坐标
        origin_x = HIRES_ORIGIN_X
        origin_y = HIRES_ORIGIN_Y
        
        # 颜色定义
        axis_color = "#FF0000"  # 红色 - X轴（东向）
        axis_color_y = "#0000FF"  # 蓝色 - Y轴（南向）
        grid_color = "#CCCCCC"  # 浅灰 - 栅格
        grid_color_bold = "#888888"  # 深灰 - 每100m栅格
        
        # 线宽
        axis_width = 3
        grid_width = 1
        grid_bold_width = 2
        
        # 绘制坐标轴（十字线）
        draw.line([(0, origin_y), (img_w, origin_y)], fill=axis_color, width=axis_width)
        draw.line([(origin_x, 0), (origin_x, img_h)], fill=axis_color_y, width=axis_width)
        
        # 绘制原点标记
        r = 10
        draw.ellipse([(origin_x-r, origin_y-r), (origin_x+r, origin_y+r)], 
                     outline="#000000", width=3)
        
        # 栅格间隔：20m = 300px
        grid_spacing_m = 20
        grid_spacing_px = grid_spacing_m * HIRES_PX_PER_M
        
        # 绘制垂直栅格线（X方向，每20m）
        x = origin_x
        while x < img_w:
            x += grid_spacing_px
            if x < img_w:
                draw.line([(x, 0), (x, img_h)], fill=grid_color, width=grid_width)
        x = origin_x
        while x > 0:
            x -= grid_spacing_px
            if x > 0:
                draw.line([(x, 0), (x, img_h)], fill=grid_color, width=grid_width)
        
        # 绘制水平栅格线（Y方向，每20m）
        y = origin_y
        while y < img_h:
            y += grid_spacing_px
            if y < img_h:
                draw.line([(0, y), (img_w, y)], fill=grid_color, width=grid_width)
        y = origin_y
        while y > 0:
            y -= grid_spacing_px
            if y > 0:
                draw.line([(0, y), (img_w, y)], fill=grid_color, width=grid_width)
        
        # 每100m加粗栅格线
        bold_spacing_m = 100
        bold_spacing_px = bold_spacing_m * HIRES_PX_PER_M
        
        # 垂直加粗线
        x = origin_x
        while x < img_w:
            x += bold_spacing_px
            if x < img_w:
                draw.line([(x, 0), (x, img_h)], fill=grid_color_bold, width=grid_bold_width)
        x = origin_x
        while x > 0:
            x -= bold_spacing_px
            if x > 0:
                draw.line([(x, 0), (x, img_h)], fill=grid_color_bold, width=grid_bold_width)
        
        # 水平加粗线
        y = origin_y
        while y < img_h:
            y += bold_spacing_px
            if y < img_h:
                draw.line([(0, y), (img_w, y)], fill=grid_color_bold, width=grid_bold_width)
        y = origin_y
        while y > 0:
            y -= bold_spacing_px
            if y > 0:
                draw.line([(0, y), (img_w, y)], fill=grid_color_bold, width=grid_bold_width)

    def _toggle_grid(self):
        """切换栅格显示/隐藏"""
        self._show_grid = not getattr(self, '_show_grid', False)
        if self._show_grid:
            self.btn_grid.config(bg="#4CAF50", text="📐 栅格:开")
        else:
            self.btn_grid.config(bg="#9E9E9E", text="📐 栅格:关")
        self._render_image()

    def _zoom_to_room(self):
        """放大到房间位置，确保房间不在边缘"""
        if not self.current_nid or not self.floor_img_orig:
            return
        v = self.nodes[self.current_nid]
        if v.get("east_m") is None or v.get("south_m") is None:
            return
        
        iw, ih = self.floor_img_orig.size
        cx, cy = meters_to_hires_px(v["east_m"], v["south_m"], iw, ih)
        
        # 边界检查：确保房间不在图的边缘（留出 20% 边距）
        margin_x = iw * 0.2
        margin_y = ih * 0.2
        
        # 如果房间靠近边缘，调整视图中心向图中心方向偏移
        if cx < margin_x:
            cx = margin_x
        elif cx > iw - margin_x:
            cx = iw - margin_x
            
        if cy < margin_y:
            cy = margin_y
        elif cy > ih - margin_y:
            cy = ih - margin_y
        
        # 设置视图中心
        self.view_center = (float(cx), float(cy))
        # 放大到 300%（避免放大过度导致视野太小）
        self.zoom_factor = 3.0
        
        self._render_image()
        self.status_bar.config(text=f"已放大到 {self.current_nid} 位置")

    def _toggle_hand_mode(self):
        """切换手型拖动模式"""
        if getattr(self, '_hand_mode', False):
            # 关闭手型模式
            self._hand_mode = False
            self.btn_hand.config(bg="#FF9800", text="✋ 手型拖动")
            self.canvas.config(cursor="crosshair")
            self.status_bar.config(text="就绪 | 提示：Ctrl+左键拖动地图，滚轮缩放")
        else:
            # 开启手型模式
            self._hand_mode = True
            self.btn_hand.config(bg="#4CAF50", text="✋ 拖动中...")
            self.canvas.config(cursor="hand2")
            self.status_bar.config(text="手型模式：左键拖动地图，点击按钮退出")

    # ── 点击事件 ───────────────────────────────────────────────
    def _on_canvas_click(self, event):
        self._drag_start = None
        self.canvas.config(cursor="tcross" if self.placing_mode else "crosshair")
        if not self.placing_mode or not self.current_nid:
            return
        cx, cy = self._canvas_to_orig(event.x, event.y)
        if cx < 0 or cy < 0:
            return
        
        # 获取图片尺寸
        iw, ih = self.floor_img_orig.size
        
        # 像素坐标 -> 米制坐标
        ox, oy = round(cx), round(cy)
        east_m, south_m = hires_px_to_meters(ox, oy, iw, ih)

        v = self.nodes[self.current_nid]
        v.update({
            "x": ox, "y": oy,
            "east_m": east_m,
            "south_m": south_m,
            "verified_fixed": True,
            "verified_ok": False,
        })
        v.pop("ocr_conf", None)
        v.pop("ocr_raw", None)

        self.placing_mode = False
        self.btn_cancel.config(state=DISABLED)
        self.canvas.config(cursor="crosshair")

        self.info_var.set(
            f"房间: {self.current_nid}  ✎ 已纠正  east={east_m}m  south={south_m}m"
        )
        self._render_image()
        self._populate_list()
        self._save_silent()
        self.status_bar.config(text=f"✎ {self.current_nid} 已纠正位置并保存")

    # ── 操作按钮 ───────────────────────────────────────────────
    def _mark_ok(self):
        if not self.current_nid:
            return
        v = self.nodes[self.current_nid]
        v["verified_ok"] = True
        v.pop("verified_fixed", None)
        self._render_image()
        self._populate_list()
        self._save_silent()
        self.status_bar.config(text=f"✓ {self.current_nid} 已确认正确")
        self._next_room()

    def _start_fix(self):
        if not self.current_nid:
            return
        self.placing_mode = True
        self.btn_cancel.config(state=NORMAL)
        self.canvas.config(cursor="tcross")
        self._render_image()
        self.status_bar.config(text="请在图上点击正确的房间位置...")

    def _cancel_fix(self):
        self.placing_mode = False
        self._drag_start  = None
        self.btn_cancel.config(state=DISABLED)
        self.canvas.config(cursor="crosshair")
        if self.current_nid:
            self._render_image()

    def _mark_uncertain(self):
        if not self.current_nid:
            return
        v = self.nodes[self.current_nid]
        v["uncertain"] = True
        v.pop("verified_ok", None)
        v.pop("verified_fixed", None)
        self._populate_list()
        self._save_silent()
        self.status_bar.config(text=f"? {self.current_nid} 已标记为无法确定")
        self._next_room()

    def _save_silent(self):
        with open(SRC_JSON, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _save(self):
        self._save_silent()
        messagebox.showinfo("保存", f"已保存到\n{SRC_JSON}")
        self.status_bar.config(text="💾 已保存")

if __name__ == "__main__":
    app = RoomVerifier()
    app.mainloop()
