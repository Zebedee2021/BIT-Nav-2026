# BIT-Nav-2026 | 文萃楼智能导航系统

北京理工大学良乡校区文萃楼具身空间导航原型系统。

基于 Streamlit 构建的 Web 演示平台，实现了从自然语言输入到路径规划、楼层图可视化的完整导航流程。

## 功能特性

- **A\* 路径规划** — 基于拓扑图的最短路径搜索，支持跨楼层导航
- **自然语言输入** — 语义理解模块，支持 "东门"、"教务办公室"、"A102" 等多种输入方式
- **楼层图可视化** — 在楼层平面图上叠加导航路径，起点/终点/中间节点清晰标注
- **多楼层顺序显示** — 跨楼层路径按楼层分段展示，楼梯/电梯过渡指示
- **方位导航** — 指南针模拟 + 东南西北/前后左右双模式方位指引
- **系统托盘管理** — Windows 托盘程序，一键启动/停止服务，快速打开页面
- **完整建筑数据** — 10 层楼、110+ 节点、A/B 双区结构化数据

## 项目结构

```
BIT-Nav-2026/
├── app.py                          # Streamlit 主程序
├── requirements.txt                # Python 依赖
├── launcher/                       # 系统托盘启动器
│   ├── BIT-Nav-Tray.ps1           # PowerShell 托盘程序
│   ├── start-service.ps1          # 服务启动脚本
│   ├── BIT-Nav-Launcher.vbs       # VBS 启动器
│   └── 启动托盘.bat                # 批处理启动文件
├── data/
│   ├── wencui_building.json        # 建筑拓扑数据（节点/边/坐标）
│   ├── wencui_building_aligned.json # 校准后的建筑数据
│   ├── semantic_mapping.json       # 语义映射配置
│   ├── floorplans/                 # 楼层平面图（原始）
│   ├── floorplans_aligned/         # 校准后的楼层图
│   └── floorplans_standardized/    # 标准化后的楼层图
├── src/
│   ├── pathfinding.py              # A* 路径规划算法
│   ├── semantic_mapper.py          # 自然语言语义映射
│   ├── floorplan_visualizer.py     # 楼层图可视化
│   ├── orientation_navigator.py    # 方位导航模块
│   ├── compass_widget.py           # 指南针组件
│   ├── llm_navigator.py            # LLM 导航接口
│   ├── align_floorplans.py         # 楼层图校准工具
│   ├── standardize_floorplans.py   # 楼层图标准化工具
│   ├── room_label_detector.py      # 房间标签检测器
│   └── test_navigation.py          # 导航测试脚本
├── docs/                           # 项目文档（MkDocs）
│   ├── architecture/               # 架构文档
│   ├── building/                   # 建筑数据文档
│   ├── implementation/             # 实现文档
│   ├── overview/                   # 项目概览
│   └── teaching/                   # 教学文档
├── tools/                          # 辅助工具
│   ├── annotate_floorplan.py       # 楼层图标注工具
│   └── generate_building_graph.py  # 建筑图生成工具
├── skills/                         # Qoder Skills
│   └── powershell-gui-open-url/    # PowerShell GUI 打开 URL
└── wencui/                         # 官方平台截图参考
```

## 快速开始

### 环境要求

- Python 3.10+
- Windows（中文字体依赖 SimHei）

### 安装与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Web 界面
streamlit run app.py
```

浏览器访问 http://localhost:8501

### 系统托盘启动（推荐）

Windows 用户可以使用系统托盘程序管理导航服务：

```bash
# 方式1：双击运行
launcher\启动托盘.bat

# 方式2：PowerShell 直接运行
powershell -ExecutionPolicy Bypass -File launcher\BIT-Nav-Tray.ps1
```

托盘功能：
- **Start Service** — 启动 Streamlit 服务（自动检测可用端口）
- **Stop Service** — 停止服务
- **Open Page** — 打开浏览器访问导航页面
- **双击托盘图标** — 快速打开页面

### 使用方式

1. 左侧边栏选择 **起点**（手动选择 或 自然语言输入，如 "东门"、"A102"）
2. 选择 **目标**（如 "教务办公室"、"D402"、"报告厅"）
3. 点击 **开始导航**
4. 查看分楼层路径图 + 导航指令

## 建筑数据

文萃楼 10 层建筑拓扑模型，逻辑坐标空间 200x200：

| 楼层 | 定位 | 主要设施 |
|------|------|----------|
| 1F | 入口层 | 东/西门入口、阶梯教室、多媒体教室、服务中心 |
| 2F | 教学区 | A/B 区普通教室 |
| 3F | 实验区 | 生物/化学/物理/电子实验室 |
| 4F | 办公区 | 教务办公室、会议室、教师办公室 |
| 5F | 研究区 | 教研室、研究生工作室 |
| 6F | 研讨区 | 研讨室、小型会议室 |
| 7F | 信息技术区 | 计算机机房、多媒体实训室 |
| 8F | 学生活动区 | 学生活动室、自习室 |
| 9F | 行政管理区 | 院长办公室、学工办公室 |
| 10F | 综合服务区 | 大会议室、报告厅、多功能厅 |

每层标准配置：主走廊 + A/B 区走廊 + A/B 楼梯间 + A/B 电梯 + 房间节点

## 技术架构

```
用户输入 → 语义映射(SemanticMapper) → 节点ID
                                        ↓
起点/终点 → A*路径规划(AStarPathfinder) → 路径节点序列
                                        ↓
路径序列 → 楼层分段(split_path_by_floor) → 分层可视化
         → 导航指令(NavigationGuide)     → 文字引导
         → 方位导航(OrientationNavigator) → 方向指引
```

## 文档

完整文档请访问：
- 在线文档：https://zebedee2021.github.io/BIT-Nav-2026/
- 本地文档：`docs/` 目录（MkDocs 构建）

## 课程信息

北京理工大学 2025-2026 学年第二学期教学项目

---

*教学演示版 v1.1*
