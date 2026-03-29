# 三层空间模型

项目构建了完整的三层空间模型，将物理空间、语义空间和行为空间统一为具身空间。

```mermaid
graph LR
    subgraph "物理空间 Physical"
        Coord["坐标 Geometry"]
        Build["建筑 Rooms"]
        Connect["连接 Corridors"]
    end
    subgraph "语义空间 Semantic"
        Name["名称 A栋"]
        Func["功能 教务处"]
        Room["空间 机房"]
    end
    subgraph "行为空间 Action"
        Turn["转向 左转"]
        Move["移动 上楼"]
        Arrive["到达"]
    end
    subgraph "统一具身空间"
        E["E = (Geometry, Topology, Semantics)"]
    end
    Coord --> E
    Build --> E
    Connect --> E
    Name --> E
    Func --> E
    Room --> E
    E --> Turn
    E --> Move
    E --> Arrive
```

## 空间模型详情

- [物理空间建模](physical.md) - 坐标、楼栋、路径的几何表示
- [语义空间建模](semantic.md) - 名称、功能、区域的语义表达
- [行为空间建模](action.md) - 转向、移动、到达的行为指令
- [统一具身空间](embodied.md) - E = (Geometry, Topology, Semantics)

## 数学表达

$$E = (Geometry, Topology, Semantics)$$

- **Geometry**：房间/坐标的空间几何
- **Topology**：楼层连接关系的拓扑结构
- **Semantics**：A 栋/教室/办公室的功能语义
