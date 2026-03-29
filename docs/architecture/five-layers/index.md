# 五层系统架构

项目采用分层架构设计，从底层感知到顶层行为输出，形成完整的系统闭环。

```mermaid
graph TB
    subgraph "感知层 Perception"
        GPS["GPS 室外定位"]
        IMU["IMU 惯性测量"]
        CAM["Camera 视觉"]
        WIFI["WiFi/蓝牙 辅助"]
    end
    subgraph "信号层 Signal"
        PE["位置估计"]
        KF["Kalman 滤波"]
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
    subgraph "行为层 Output"
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

## 各层详细文档

- [感知层 (Perception)](perception.md)
- [信号层 (Signal)](signal.md)
- [空间层 (Space Model)](space.md)
- [智能层 (AI)](ai.md)
- [行为层 (Embodied Output)](behavior.md)
