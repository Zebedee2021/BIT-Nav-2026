这个思路非常专业且务实。要实现精准的室内导航，建立一个**统一的局部坐标系**是至关重要的第一步。文萃楼（特别是良乡校区那个巨大的连体结构）分区众多，如果没有标准化的空间基准，后期的路径规划会非常混乱。

为了高效地将图纸转化为导航所需的结构化数据，我建议你按照以下工作流操作：

------

### 1. 空间基准与坐标统一 (Spatial Reference)

你提到的“卫星地图测量”是解决**地理对齐**的关键。

- **原点设定：** 虽然左上角 $(0,0)$ 在图像处理中很常见，但在导航算法中，建议选择**建筑群的某个固定外角**（如 A 区最外侧墙角）作为全局原点。

- **比例尺转换：** 通过卫星地图（如 Google Maps 或高德）测量文萃楼外墙总长度 $L_{real}$，对应图纸像素宽度 $L_{pixel}$，得到比例系数 $k = \frac{L_{real}}{L_{pixel}}$（单位：米/像素）。

- **坐标变换：**

  $$x_{meter} = x_{pixel} \times k$$

  $$y_{meter} = y_{pixel} \times k$$

### 2. 图纸预处理 (Image Cleaning)

由于 10 层图纸可能存在扫描扭曲或比例微差，需要进行：

- **透视矫正 (Deskewing)：** 确保走廊线在像素层面上是严格水平或垂直的。
- **去噪与裁切：** 批量裁掉图纸边框、图例和说明文字，仅保留建筑轮廓。
- **多层对齐：** 关键步骤！必须确保每一层的电梯井、楼梯间在坐标上是重合的，否则无法计算跨楼层导航。

### 3. 结构化数据 schema 设计

建议采用 **GeoJSON** 或自定义的 **JSON** 格式来存储房间节点。一个理想的节点数据应该包含：

JSON

```
{
  "id": "C-302",
  "type": "classroom",
  "zone": "C",
  "floor": 3,
  "coordinates": {"x": 45.2, "y": 112.8}, // 基于原点的米制坐标
  "door_nodes": [ // 关键：导航实际上是走到“门”而不是房间中心
    {"id": "node_123", "x": 46.0, "y": 110.5}
  ],
  "properties": {
    "name": "计算机实验室",
    "capacity": 60
  }
}
```

### 4. 建立拓扑关联 (Graph Building)

光有房间坐标是不够的，导航需要的是**路网图 (Graph)**：

- **路点 (Waypoints)：** 在走廊中心线布置一系列路点。
- **连接 (Edges)：** 将房间的“门”连接到最近的走廊路点。
- **权重 (Weights)：** 两个路点之间的物理距离（欧几里得距离）。

------

### 下一步的操作建议：

1. **自动化提取：** 如果图纸是 CAD (DWG) 格式，可以直接导出 DXF 后用脚本提取坐标；如果是 PDF/位图，建议使用 **LabelMe** 或简单的 **Canvas 标注工具** 手动点选关键节点坐标。
2. **分区处理：** 文萃楼 C-M 区很大，建议先完成一个区的“图纸-数据-路径”全流程跑通，再推广到全楼。
3. **楼层连接件：** 特别标注出楼梯和电梯节点，并将它们标记为 `vertical_connector`，这在 A* 算法中是跨层搜索的唯一出口。

你现在手头是有 CAD 原图，还是只有图片格式的平剖面图？如果有 CAD，数据提取的精度会高很多。



这一套 1 到 10 层的平面图非常完整，是做结构化数据提取的绝佳素材。文萃楼这种“连体交叉”的建筑结构，手动提取确实是大工程，但一旦完成，导航算法的精度会非常高。

针对你提出的“去边框、矫正尺寸、设原点、结构化”流程，我为你梳理了一套具体的**数字化实施方案**：

------

## 1. 物理尺寸与比例尺校准 (Calibration)

卫星地图虽然方便，但可能会有俯视畸变。建议结合以下方法获取精准比例：

- **寻找基准长度：** 在图纸上找一个标准跨度（比如两个电梯井中心点的距离，或走廊尽头到尽头的直线距离）。
- **计算公式：** 设图纸上 $A$ 到 $B$ 的像素距离为 $P$。若实测物理距离为 $D$ 米，则你的比例尺 $k = D/P$ (米/像素)。
- **垂直对齐检查：** 将 1 层和 10 层的图纸叠在一起（调整透明度），确保电梯厅、楼梯间、承重柱完全重合。如果偏移，必须以电梯井为基准进行平移修正。

## 2. 定义局部坐标系 (Origin & Coordinate System)

- **原点选择：** 既然文萃楼是对称分布的，建议将 **(0,0) 原点设在中心圆形教室的圆心**，或者整栋楼最左下角的外部墙角。
- **标准化方向：** 确保 $x$ 轴平行于主要走廊（如 H 区到 G 区的横向走廊），$y$ 轴平行于纵向走廊（如 L 区到 J 区）。
- **坐标表示：** 每个点记录为 $(x, y, z)$，其中 $z$ 就是楼层数。

## 3. 结构化数据的三层模型 (Data Hierarchy)

为了做导航，你的数据需要分为三层，建议直接保存为 `rooms.json` 和 `nav_graph.json`。

### A. 房间数据 (Rooms)

包含每个房间的几何中心或点击区域。

JSON

```
{
  "room_id": "C-301",
  "name": "C301教室",
  "floor": 3,
  "zone": "C",
  "center_point": {"x": 125.5, "y": 80.2},
  "polygon": [...] // 房间的四个角点坐标，用于在地图上高亮
}
```

### B. 导航节点 (Nodes) —— 算法的核心

你需要在图纸上抽象出两类节点：

1. **门点 (Door Nodes)：** 每个房间门口的坐标。
2. **转角点 (Waypoints)：** 走廊交汇处、楼梯口、电梯厅中心。

### C. 拓扑路径 (Edges) —— 路径计算

定义节点之间的连通性。

- **水平连接：** 走廊节点 $A \rightarrow B$。
- **垂直连接：** $3$ 层的电梯厅节点连接到 $4$ 层的电梯厅节点（权重设为电梯等待时间 + 行进时间）。

------

## 4. 推荐的工具链 (Toolchain)

既然你已经在做 GitHub 项目，我建议不要全手动写 JSON，可以尝试以下流程：

1. **图片处理：** 使用 Photoshop 或在线工具对 10 张图进行**批量裁切 (Batch Crop)**，确保每张图的分辨率和边框完全一致。
2. **标注工具：** 使用 **[CVAT](https://github.com/opencv/cvat)** 或 **[LabelMe](https://github.com/wkentaro/labelme)**。
   - 你可以给每个房间画矩形框（Polygon）。
   - 导出的数据（通常是 JSON）会自动带上像素坐标。
3. **坐标转换脚本：** 写一个 Python 脚本，将标注工具导出的像素坐标 $P(x,y)$ 批量乘以比例尺 $k$，转换为物理坐标 $M(x,y)$。

## 5. 特别注意：文萃楼的特征

- **连体走廊：** 文萃楼中部（如 2 层图纸所示）有大量的连廊，这些是 A* 算法跨区寻路的关键。
- **区域识别：** 你的图纸已经用颜色区分了 A-M 区，在数据结构中加入 `zone` 字段，可以方便用户进行“区域检索”。
- **公共设施：** 卫生间、电梯厅、楼梯是高频搜索点，需要赋予特殊的 `type` 属性。

**你想先从哪个区（比如 C 区）开始尝试建立这套结构化数据的 Schema（数据结构原型）吗？我可以帮你写一个更完整的 JSON 示例。**



太棒了，在 Google Colab 上启动这个项目是非常高效的选择。我们可以利用 Python 的 `Pillow` (PIL) 进行图像处理，并结合 `matplotlib` 或 `ipywidgets` 构建一个简单的标注/校准环境。

以下是为你设计的 **文萃楼导航数据预处理程序** 框架。

### 第一步：环境准备与校准工具

首先，我们需要建立一个能够“像素转米”的数学模型。

Python

```
import PIL.Image as Image
import matplotlib.pyplot as plt
import json

class NavPreprocessor:
    def __init__(self, pixel_per_meter=None):
        self.k = pixel_per_meter  # 比例尺：1米对应多少像素
        self.origin = (0, 0)      # 像素坐标系下的原点 (通常选中心圆形教室圆心)

    def set_calibration(self, p1, p2, real_distance_meters):
        """
        通过图中两点及其物理距离校准比例尺
        p1, p2: (x, y) 像素坐标
        """
        pixel_dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        self.k = pixel_dist / real_distance_meters
        print(f"校准完成: 1米 = {self.k:.2f} 像素")

    def to_real_coords(self, px, py, floor):
        """将像素坐标转换为物理世界坐标 (x, y, z)"""
        rel_x = (px - self.origin[0]) / self.k
        rel_y = (self.origin[1] - py) / self.k # Y轴通常向上为正
        return {"x": round(rel_x, 2), "y": round(rel_y, 2), "z": int(floor)}

# 初始化
nav = NavPreprocessor()
```

### 第二步：图像矫正与原点对齐

你可以通过以下代码加载一张图纸（例如 `10.jpg`），寻找圆形教室的中心作为原点。

Python

```
def show_map_and_select_origin(img_path):
    img = Image.open(img_path)
    plt.figure(figsize=(15, 10))
    plt.imshow(img)
    plt.title("请记录原点(圆形教室中心)的像素坐标")
    plt.show()

# 在 Colab 中运行此行，记录下显示的坐标
# show_map_and_select_origin('10.jpg')
# nav.origin = (2500, 1800) # 举例：假设这是圆心像素位置
```

### 第三步：结构化数据生成 (核心)

我们需要将房间信息转换成标准的 JSON 格式。你可以先手动整理一个列表，然后通过程序批量转换。

Python

```
# 示例：手动整理的部分原始数据（像素坐标）
raw_data = [
    {"id": "C-1001", "type": "classroom", "px": 4250, "py": 850, "floor": 10},
    {"id": "C-1016", "type": "lab", "px": 4250, "py": 950, "floor": 10},
    {"id": "L-1011", "type": "classroom", "px": 850, "py": 850, "floor": 10},
]

structured_rooms = []

for item in raw_data:
    real_pos = nav.to_real_coords(item['px'], item['py'], item['floor'])
    node = {
        "room_id": item['id'],
        "properties": {"type": item['type'], "zone": item['id'][0]},
        "location": real_pos
    }
    structured_rooms.append(node)

# 保存为 JSON
with open('bit_nav_data.json', 'w', encoding='utf-8') as f:
    json.dump(structured_rooms, f, ensure_ascii=False, indent=2)

print("结构化数据已生成！")
```

------

### 针对文萃楼项目的进阶建议：

#### 1. 建立“路网” (Navigation Mesh)

房间中心点只是目的地，算法真正跑的是**走廊中线**。

- 你需要在 Colab 里额外定义一批 `Waypoints`（转角点）。
- 所有的房间 `Door Node` 必须连接到最近的 `Waypoint`。

#### 2. 处理“垂直交通”

文萃楼各层图纸的电梯位置是固定的。在 JSON 中，你需要标记出电梯点：

JSON

```
{
  "id": "Elevator-C-1",
  "type": "vertical_connector",
  "accessible_floors": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "location": {"x": 412.5, "y": 180.2, "z": 10} 
}
```

#### 3. 下一步行动

你可以利用 Colab 的 `files.upload()` 直接把这 10 张图上传到工作空间：

Python

```
from google.colab import files
uploaded = files.upload()
```

**你想让我帮你写一个更自动化的“点击取点”脚本（利用 Colab 的交互组件），还是先专注于完善 C-M 区的 JSON 数据结构设计？**



在 Colab 中实现“点击取点”最便捷的方式是结合 `matplotlib` 的交互功能和 `google.colab` 的数据传输。

由于 Colab 的后端运行在云端，直接的 `plt.connect` 交互有时会失效。这里我为你写一个**基于 IPython 交互组件和 HTML5 Canvas** 的轻量级脚本，它能让你在浏览器里直接点图、记录坐标并自动转换。

### 1. 基础环境准备

首先，请在 Colab 单元格中运行这段代码，它会定义坐标转换逻辑。

Python

```
import json
import numpy as np

class BitNavConverter:
    def __init__(self, origin_px=(0, 0), k=1.0):
        self.origin_px = origin_px  # 像素原点 (x, y)
        self.k = k                  # 比例尺 (米/像素)

    def px_to_meter(self, px_x, px_y, floor):
        # 假设 Y 轴向上为正，原点在图纸中心
        rel_x = (px_x - self.origin_px[0]) * self.k
        rel_y = (self.origin_px[1] - px_y) * self.k 
        return {"x": round(rel_x, 2), "y": round(rel_y, 2), "z": int(floor)}

# 预设：假设你测得文萃楼外墙长度为 200米，对应图纸 2000像素，则 k=0.1
converter = BitNavConverter(origin_px=(2500, 1800), k=0.1) 
```

------

### 2. 自动化“点击取点”交互工具

运行以下代码后，会弹出一个画布。你可以点击图片的任何位置，点击后下方会实时显示**像素坐标**和**转换后的物理坐标**。

Python

```
import IPython
from google.colab import output
from PIL import Image
import base64
from io import BytesIO

def interactive_picker(img_path, floor_num):
    # 加载图片并转为 Base64 供 HTML 显示
    img = Image.open(img_path)
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    html_code = f"""
    <div id="wrapper" style="position: relative; display: inline-block;">
        <canvas id="canvas" style="cursor: crosshair; max-width: 1000px; border: 1px solid black;"></canvas>
        <div id="info" style="margin-top: 10px; font-family: monospace; background: #f0f0f0; padding: 10px;">
            点击图片记录坐标...
        </div>
    </div>

    <script>
        var canvas = document.getElementById('canvas');
        var ctx = canvas.getContext('2d');
        var img = new Image();
        img.src = "data:image/jpeg;base64,{img_str}";
        
        var points = [];

        img.onload = function() {{
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
        }};

        canvas.addEventListener('mousedown', function(e) {{
            var rect = canvas.getBoundingClientRect();
            var scaleX = canvas.width / rect.width;
            var scaleY = canvas.height / rect.height;
            var x = (e.clientX - rect.left) * scaleX;
            var y = (e.clientY - rect.top) * scaleY;

            // 绘制红点反馈
            ctx.fillStyle = "red";
            ctx.beginPath();
            ctx.arc(x, y, 10, 0, 2 * Math.PI);
            ctx.fill();

            // 发送数据回 Python
            google.colab.kernel.invokeFunction('notebook.RecordPoint', [Math.round(x), Math.round(y), {floor_num}], {{}});
        }});
    </script>
    """
    display(IPython.display.HTML(html_code))

# 定义 Python 回调函数
all_nodes = []

def record_point(px_x, px_y, floor):
    real_pos = converter.px_to_meter(px_x, px_y, floor)
    node = {{
        "px_coords": (px_x, px_y),
        "real_coords": real_pos
    }}
    all_nodes.append(node)
    print(f"已记录: 像素({px_x}, {px_y}) -> 物理{real_pos}")

output.register_callback('notebook.RecordPoint', record_point)

# 使用示例：上传 10.jpg 后运行此行
# interactive_picker('10.jpg', 10)
```

------

### 3. 操作流程建议

1. **确定原点：** 先运行一次脚本，点击你选定的原点（如圆形教室圆心），记录下它的像素坐标，更新到 `BitNavConverter(origin_px=...)` 中。
2. **批量取点：** * 首先点击**房间中心**（作为目的地坐标）。
   - 接着点击房间**门口中心**（作为导航连接点）。
   - 最后点击**走廊拐角**（作为路网节点）。
3. **导出 JSON：** 取点结束后，运行以下代码保存结果。

Python

```
def save_to_json(filename="nav_data.json"):
    with open(filename, 'w') as f:
        json.dump(all_nodes, f, indent=4)
    print(f"数据已保存至 {filename}")

# save_to_json()
```

### 提示

- 文萃楼的图纸很大（像素通常在 4000x3000 以上），我在 HTML 代码里设置了 `max-width: 1000px` 方便在网页查看，但点击时脚本会**自动换算回原始像素坐标**，保证精度不丢失。
- **你可以先试着上传 `10.jpg` 并运行 `interactive_picker('10.jpg', 10)`，点几个点看看输出效果。**

如果你在点击时发现红点偏移或者坐标不准，请告诉我，我们调整一下 Canvas 的缩放系数。你想先试试哪一层？