# 系统架构总览

文萃楼具身导航项目采用五层架构设计，每一层都有明确的功能职责和技术实现。

## 五层系统架构

```mermaid
graph TB
    subgraph "感知层 Perception"
        GPS["GPS 室外定位"]
        IMU["IMU 惯性测量"]
        CAM["Camera 视觉"]
        WIFI["WiFi/蓝牙 辅助定位"]
    end
    subgraph "信号层 Signal"
        PE["位置估计"]
        KF["滤波器 Kalman/DSP"]
        SF["传感融合"]
    end
    subgraph "空间层 Space Model"
        MAP["校园地图"]
        BIM["BIM 模型"]
        TOPO["拓扑图"]
    end
    subgraph "智能层 AI"
        PATH["路径规划"]
        SEM["语义理解"]
        INTENT["意图解析"]
    end
    subgraph "行为层 Embodied Output"
        NAV["导航提示"]
        AR["AR 指引"]
    end
    GPS --> PE
    IMU --> PE
    CAM --> PE
    WIFI --> PE
    PE --> KF --> SF
    SF --> MAP --> BIM --> TOPO
    TOPO --> PATH --> SEM --> INTENT
    INTENT --> NAV --> AR
```

## 三层空间模型

项目采用了统一的具身空间概念，将物理空间、语义空间和行为空间有机整合：

```mermaid
graph LR
    subgraph "物理空间 Physical"
        COORD["坐标 Geometry"]
        BUILD["建筑 Rooms/Floors"]
        CONNECT["连接 Corridors/Stairs"]
    end
    subgraph "语义空间 Semantic"
        NAME["名称 A栋/机房"]
        FUNC["功能 教务处/办公室"]
    end
    subgraph "行为空间 Action"
        TURN["转向 Left/Right"]
        MOVE["移动 Up/Down"]
        ARRIVE["到达 Destination"]
    end
    subgraph "具身空间"
        E["E = (Geometry, Topology, Semantics)"]
    end
    COORD --> E
    BUILD --> E
    CONNECT --> E
    NAME --> E
    FUNC --> E
    E --> TURN
    E --> MOVE
    E --> ARRIVE
```

## 数学表达

具身空间采用统一的数学表达形式：

- **E = (Geometry, Topology, Semantics)**
- **Geometry**：房间、坐标等几何信息
- **Topology**：楼栋连接关系等拓扑信息
- **Semantics**：A 栋、教室、办公室等功能语义

## 技术路线

```mermaid
flowchart TD
    Start(["开始"]) --> SelectArea["选定最小区域 整理空间数据"]
    SelectArea --> BuildMap["建立房间/功能语义映射"]
    BuildMap --> PathAlgo["实现图搜索路径规划"]
    PathAlgo --> UI["设计可演示界面"]
    UI --> LLMEnhance["加入 LLM 增强解释能力"]
    LLMEnhance --> End(["完成"])
```

## 版本演进

```mermaid
graph LR
    V1["V1 教学演示版"] --> V2["V2 现场测试版"]
    V2 --> V3["V3 AI 增强版"]
    V3 --> V4["V4 轻量定位"]
    V4 --> V5["V5 数字孪生"]
```

| 版本 | 功能 |
|------|------|
| V1 | 手动选起点 + 输入终点 + 输出路径图 |
| V2 | 增加扫码定位 + 楼层切换 |
| V3 | 自然语言输入 + AI 问答 |
| V4 | 二维码起点 + IMU 步行更新 |
| V5 | Unity 接入 + 3D 漫游 |
