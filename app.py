"""
文萃楼具身导航系统 - Streamlit Web应用
整合路径规划、语义映射、楼层图可视化、方位导航
"""

import streamlit as st
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
matplotlib.rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
import sys
import os
import json
from io import BytesIO

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pathfinding import BuildingGraph, AStarPathfinder, NavigationGuide
from semantic_mapper import SemanticMapper
from floorplan_visualizer import FloorplanVisualizer
from orientation_navigator import OrientationNavigator, RegionalAdapter
from compass_widget import create_compass_image
from llm_navigator import LLMNavigationService

# 页面配置
st.set_page_config(
    page_title="文萃楼具身导航系统",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_system():
    """加载导航系统组件 - 使用V7数据（修正楼层结构）"""
    base_dir = os.path.dirname(__file__)
    
    # 加载建筑图（使用V7数据 - 修正B/M/G为2层，A为3-7层）
    building_file = os.path.join(base_dir, 'data', 'wencui_building_v7.json')
    if not os.path.exists(building_file):
        # 如果V7文件不存在，使用V6文件
        building_file = os.path.join(base_dir, 'data', 'wencui_building_v6.json')
    
    with open(building_file, 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    # 统计数据源
    total_nodes = len(building_data.get('nodes', {}))
    ocr_nodes = sum(1 for n in building_data.get('nodes', {}).values() 
                   if n.get('type') == 'room' and 'ocr_conf' in n)
    predicted_nodes = sum(1 for n in building_data.get('nodes', {}).values() 
                         if n.get('type') == 'room' and n.get('predicted'))
    
    print(f"[导航系统] 加载建筑数据: {building_file}")
    print(f"[导航系统] 总节点: {total_nodes}, OCR识别: {ocr_nodes}, 算法预测: {predicted_nodes}")
    
    graph = BuildingGraph(building_data)
    
    # 加载语义映射
    with open(os.path.join(base_dir, 'data', 'semantic_mapping.json'), 'r', encoding='utf-8') as f:
        semantic_data = json.load(f)
    semantic_mapper = SemanticMapper(semantic_data, building_data.get("nodes", {}))
    
    # 初始化路径规划器
    pathfinder = AStarPathfinder(graph)
    guide = NavigationGuide(graph)
    
    # 初始化楼层图可视化器（使用统一坐标系的高清楼层图）
    visualizer = FloorplanVisualizer(
        os.path.join(base_dir, 'data', 'floorplans_unified', 'unified_params.json'),
        building_data_path=building_file,
        use_aligned=True,
        align_params_path=os.path.join(base_dir, 'data', 'floorplans_aligned', 'align_params.json')
    )
    
    # 初始化方位导航器（使用高清楼层图朝向：上南下北、左西右东）
    orientation_navigator = OrientationNavigator(
        pixel_to_meter=0.0667,  # 15px/m 的倒数，约 0.0667 米/像素
        floorplan_orientation='hires'  # 高清楼层图朝向
    )
    regional_adapter = RegionalAdapter(region="universal")
    
    # 初始化 LLM 导航服务
    llm_service = LLMNavigationService()
    
    return graph, semantic_mapper, pathfinder, guide, visualizer, orientation_navigator, regional_adapter, llm_service

def draw_floor_plan(graph, floor, highlight_nodes=None):
    """绘制楼层平面图"""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 获取该楼层的所有节点
    floor_nodes = [n for n in graph.nodes.values() if n.floor == floor]
    
    # 绘制节点
    for node in floor_nodes:
        color = 'lightgray'
        size = 100
        
        if highlight_nodes and node.id in highlight_nodes:
            color = 'red'
            size = 300
        elif node.type == 'entrance':
            color = 'green'
            size = 200
        elif node.type == 'room':
            color = 'blue'
            size = 150
        elif node.type == 'stairs':
            color = 'orange'
            size = 150
        elif node.type == 'elevator':
            color = 'purple'
            size = 150
        
        ax.scatter(node.x, node.y, c=color, s=size, alpha=0.7, edgecolors='black')
        ax.annotate(node.name, (node.x, node.y), fontsize=8, ha='center', va='bottom')
    
    # 绘制边
    for edge in graph.edges:
        node1 = graph.get_node(edge[0])
        node2 = graph.get_node(edge[1])
        if node1 and node2 and node1.floor == floor and node2.floor == floor:
            ax.plot([node1.x, node2.x], [node1.y, node2.y], 'gray', alpha=0.3, linewidth=1)
    
    # 高亮路径
    if highlight_nodes:
        for i in range(len(highlight_nodes) - 1):
            node1 = graph.get_node(highlight_nodes[i])
            node2 = graph.get_node(highlight_nodes[i + 1])
            if node1 and node2 and node1.floor == floor and node2.floor == floor:
                ax.plot([node1.x, node2.x], [node1.y, node2.y], 'r-', linewidth=3, alpha=0.8)
    
    ax.set_title(f'{floor} 平面图', fontsize=14)
    ax.set_xlabel('X坐标')
    ax.set_ylabel('Y坐标')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    return fig

def split_path_by_floor(path, graph):
    """将路径按楼层分段，合并纯中转层（只有楼梯/电梯节点的楼层）"""
    
    if not path:
        return []
    
    # 第一步：按楼层切分
    raw_segments = []
    current_floor = graph.get_node(path[0]).floor
    current_segment = [path[0]]
    
    for node_id in path[1:]:
        node = graph.get_node(node_id)
        if node.floor == current_floor:
            current_segment.append(node_id)
        else:
            raw_segments.append((current_floor, current_segment))
            current_floor = node.floor
            current_segment = [node_id]
    
    if current_segment:
        raw_segments.append((current_floor, current_segment))
    
    if len(raw_segments) <= 1:
        return raw_segments
    
    # 第二步：合并纯中转层（只含楼梯/电梯节点的楼层跳过，不单独显示）
    merged = []
    for floor, nodes in raw_segments:
        is_transit_only = all(
            graph.get_node(n).type in ('stairs', 'elevator')
            for n in nodes
        )
        if is_transit_only and merged:
            # 纯中转层跳过，过渡指示器会覆盖
            continue
        else:
            merged.append((floor, nodes))
    
    return merged if merged else raw_segments


def main():
    # 标题
    st.markdown('<p class="main-header">🧭 文萃楼具身导航系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">基于具身智能理论的室内导航系统 | 北京理工大学良乡校区</p>', unsafe_allow_html=True)
    
    # 加载系统
    try:
        graph, semantic_mapper, pathfinder, guide, visualizer, orientation_navigator, regional_adapter, llm_service = load_system()
    except Exception as e:
        st.error(f"系统加载失败: {e}")
        return
    
    # 侧边栏 - 导航设置
    st.sidebar.header("🎯 导航设置")
    
    # 获取可选节点（仅房间和入口，排除走廊/楼梯/电梯等内部节点）
    selectable_nodes = [n for n in graph.nodes.values() if n.type in ('room', 'entrance')]
    
    # 构建三级索引: zone -> floor -> [(node_id, display_name)]
    from collections import defaultdict
    zone_floor_rooms = defaultdict(lambda: defaultdict(list))
    for n in selectable_nodes:
        zone_floor_rooms[n.zone][n.floor].append((n.id, n.name))
    # 排序：各层房间按 id 排序
    for zone in zone_floor_rooms:
        for floor in zone_floor_rooms[zone]:
            zone_floor_rooms[zone][floor].sort(key=lambda x: x[0])
    
    # 分区排序：A-M 字母序，CIRCULAR 放最后
    ZONE_ORDER = [z for z in "ABCDEFGHIJKLM"] + ["CIRCULAR"]
    available_zones = [z for z in ZONE_ORDER if z in zone_floor_rooms]
    
    # 分区显示名
    ZONE_DISPLAY = {z: f"{z}区" for z in "ABCDEFGHIJKLM"}
    ZONE_DISPLAY["CIRCULAR"] = "圆楼"
    
    def cascading_room_selector(key_prefix, label):
        """三级联动选择器：分区 → 楼层 → 房间，返回选中的 node_id"""
        st.sidebar.subheader(label)
        
        # 第一级：选分区
        zone = st.sidebar.selectbox(
            "分区:",
            options=available_zones,
            format_func=lambda z: ZONE_DISPLAY.get(z, z),
            key=f"{key_prefix}_zone"
        )
        
        # 第二级：选楼层（仅该分区有效楼层）
        floors_in_zone = sorted(
            zone_floor_rooms[zone].keys(),
            key=lambda f: int(f.replace('F', ''))
        )
        floor = st.sidebar.selectbox(
            "楼层:",
            options=floors_in_zone,
            key=f"{key_prefix}_floor"
        )
        
        # 第三级：选房间（仅该分区+楼层的房间）
        rooms = zone_floor_rooms[zone][floor]
        room_id_to_name = {r[0]: r[1] for r in rooms}
        node_id = st.sidebar.selectbox(
            "房间:",
            options=[r[0] for r in rooms],
            format_func=lambda x: room_id_to_name[x],
            key=f"{key_prefix}_room"
        )
        return node_id
    
    # 起点选择
    start_node_id = cascading_room_selector("start", "📍 起点")
    
    # 显示起点位置地图（当选择起点后）
    if start_node_id and visualizer:
        start_node = graph.get_node(start_node_id)
        if start_node:
            st.markdown("---")
            col_map, col_info = st.columns([2, 1])
            
            with col_map:
                st.subheader(f"📍 起点位置: {start_node.name}")
                # 获取起点坐标（优先使用 ux/uy）
                ux = start_node.ux if start_node.ux != 0.0 else start_node.x
                uy = start_node.uy if start_node.uy != 0.0 else start_node.y
                
                # 创建带标记的楼层图
                fig = visualizer.create_matplotlib_visualization(
                    start_node.floor,
                    path_nodes=[(ux, uy)],
                    title=f"{start_node.floor} - {start_node.name}",
                    highlight_node=(ux, uy)
                )
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)
            
            with col_info:
                st.markdown("**起点信息**")
                st.markdown(f"- **名称**: {start_node.name}")
                st.markdown(f"- **楼层**: {start_node.floor}")
                st.markdown(f"- **区域**: {start_node.zone}")
                if start_node.description:
                    st.markdown(f"- **描述**: {start_node.description}")
                
                # 显示坐标
                st.caption(f"坐标: ux={ux:.0f}, uy={uy:.0f}")
    
    # 终点选择
    target_node_id = cascading_room_selector("end", "🎯 终点")
    
    # 语义搜索
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 语义搜索")
    semantic_query = st.sidebar.text_input("输入目的地描述:", placeholder="例如：教务办公室、A区教室")
    
    if semantic_query and st.sidebar.button("🔎 语义解析"):
        results = semantic_mapper.find_location(semantic_query)
        if results:
            st.sidebar.success(f"找到 {len(results)} 个匹配")
            for r in results[:3]:
                st.sidebar.caption(f"- {r['name']} ({r['floor']}): {r['description']}")
            if results:
                target_node_id = results[0]['id']
                st.sidebar.info(f"已选择: {results[0]['name']}")
        else:
            st.sidebar.warning("未找到匹配位置")
    
    # LLM 智能导航
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI 智能导航")
    
    # 检查 LLM 是否可用
    if llm_service.is_available():
        st.sidebar.caption("✅ AI 助手已就绪")
        
        llm_query = st.sidebar.text_input(
            "用自然语言描述目的地:",
            placeholder="例如：我要去教务处、A区4楼的教室"
        )
        
        if llm_query and st.sidebar.button("🧠 AI 解析"):
            with st.sidebar.spinner("AI 思考中..."):
                # 获取建筑节点数据
                building_nodes = {}
                for node_id, node in graph.nodes.items():
                    building_nodes[node_id] = {
                        "name": node.name,
                        "floor": node.floor,
                        "description": node.description,
                        "type": node.type
                    }
                
                # 调用 LLM 解析
                matched_node_id = llm_service.find_destination(llm_query, building_nodes)
                
                if matched_node_id:
                    node = graph.get_node(matched_node_id)
                    st.sidebar.success(f"🎯 AI 识别: {node.name}")
                    st.sidebar.caption(f"楼层: {node.floor}")
                    target_node_id = matched_node_id
                else:
                    st.sidebar.warning("AI 无法确定目的地，请尝试更具体的描述")
    else:
        st.sidebar.caption("⚠️ AI 助手未配置")
        st.sidebar.info("设置 DASHSCOPE_API_KEY 环境变量以启用 AI 功能")
    
    # 方位导航设置
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧭 方位导航设置")
    
    region = st.sidebar.radio(
        "方位表示偏好:",
        ["universal", "north", "south"],
        format_func=lambda x: {"universal": "🌍 通用模式", "north": "🧭 北方模式（东南西北为主）", "south": "👋 南方模式（前后左右为主）"}[x],
        index=0
    )
    # 重新创建 RegionalAdapter 以应用新的地域设置
    regional_adapter = RegionalAdapter(region)
    
    user_heading = st.sidebar.slider("当前朝向（0°=北）:", 0, 360, 0, 15)
    if orientation_navigator:
        orientation_navigator.set_user_heading(user_heading)
    
    # 显示指南针
    if orientation_navigator:
        compass_img = create_compass_image(user_heading)
        if compass_img:
            st.sidebar.image(compass_img, caption=f"当前朝向: {user_heading}°", use_container_width=True)
    
    # 楼层图预览
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 楼层预览")
    preview_floor = st.sidebar.selectbox("选择楼层:", ["1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"])
    
    floor_info = visualizer.get_floorplan_info(preview_floor) if visualizer else None
    if floor_info:
        st.sidebar.caption(f"{floor_info['name']}")
        st.sidebar.caption(f"📝 {floor_info['description']}")
        
        # 显示缩略图（优先使用官方楼层图）
        _floorplans_dir = os.path.join(os.path.dirname(__file__), "data", "floorplans")
        _official_img = os.path.join(_floorplans_dir, f"{preview_floor}_official.jpg")
        _sample_img   = os.path.join(_floorplans_dir, f"{preview_floor}.png")
        if os.path.exists(_official_img):
            st.sidebar.image(_official_img, caption=f"{preview_floor} 官方平面图", use_container_width=True)
        elif os.path.exists(_sample_img):
            st.sidebar.image(_sample_img, use_container_width=True)
        else:
            thumbnail_url = visualizer.get_floor_thumbnail(preview_floor)
            if thumbnail_url:
                st.sidebar.image(thumbnail_url, use_container_width=True)
    
    # 开始导航按钮
    st.sidebar.markdown("---")
    start_navigation = st.sidebar.button("🚀 开始导航", type="primary")
    
    # 主内容区
    if start_navigation and start_node_id and target_node_id:
        # 执行路径规划
        path = pathfinder.find_path(start_node_id, target_node_id)
        
        if path:
            # 生成导航指令
            instructions = guide.generate_instructions(path)
            
            # 显示导航结果（统一步骤流：图+行动+方位+语音）
            st.success(f"✅ 路径规划成功！共 {len(instructions)} 个步骤")
            
            # LLM 优化导航描述
            if llm_service.is_available():
                with st.expander("🤖 AI 导航指引（点击查看）"):
                    natural_desc = llm_service.generate_natural_description(instructions)
                    st.markdown(f"**{natural_desc}**")
            
            # 路径概要
            start_node = graph.get_node(start_node_id)
            end_node = graph.get_node(target_node_id)
            st.markdown(f"**{start_node.name}** ({start_node.floor}) → **{end_node.name}** ({end_node.floor})")
            st.markdown("---")
            
            # 生成统一步骤数据 (使用统一校正图坐标 ux/uy)
            path_coords = []
            path_names = []
            for node_id in path:
                node = graph.get_node(node_id)
                if node:
                    # 优先使用统一校正图坐标，如果没有则使用原始坐标
                    ux = node.ux if node.ux != 0.0 else node.x
                    uy = node.uy if node.uy != 0.0 else node.y
                    path_coords.append((ux, uy))
                    path_names.append(node.name)
            
            orientation_instructions = orientation_navigator.generate_path_directions(
                path_coords, path_names
            ) if orientation_navigator else []
            
            # 统一步骤流：每步显示 图+行动+方位+语音
            for i, inst in enumerate(instructions):
                from_node = graph.get_node(inst['from_node'])
                to_node = graph.get_node(inst['to_node'])
                step_floor = from_node.floor
                
                # 语音文本
                voice_parts = [f"步骤{i+1}：{inst['instruction']}"]
                if i < len(orientation_instructions):
                    ori = orientation_instructions[i]
                    voice_parts.append(ori['text_full'])
                voice_text = "，".join(voice_parts)
                
                # 判断是否楼层过渡
                is_transition = from_node.floor != to_node.floor
                transition_icon = "🛗" if to_node.type == 'elevator' else "🪜" if to_node.type == 'stairs' else "🔄"
                
                with st.expander(
                    f"{'📌' if not is_transition else transition_icon} 步骤 {i+1}: {inst['from_name']} → {inst['to_name']}", 
                    expanded=(i == 0)
                ):
                    # 两栏布局：左图右文字
                    col_img, col_text = st.columns([1.5, 1])
                    
                    with col_img:
                        # 该步骤的微路径图
                        step_coords = path_coords[i:i+2] if i < len(path_coords)-1 else [path_coords[i], path_coords[i]]
                        if len(step_coords) >= 2 and visualizer:
                            fig_step = visualizer.create_matplotlib_visualization(
                                step_floor,
                                step_coords,
                                title=f"{step_floor}: {inst['from_name']} → {inst['to_name']}"
                            )
                            buf = BytesIO()
                            fig_step.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                            buf.seek(0)
                            
                            # 显示图片
                            st.image(buf, use_container_width=True)
                            plt.close(fig_step)
                    
                    with col_text:
                        # 行动指引
                        st.markdown(f"**🎯 {inst['instruction']}**")
                        
                        # 方位指引（如果有）
                        if i < len(orientation_instructions):
                            ori = orientation_instructions[i]
                            formatted = regional_adapter.format_instruction(ori)
                            st.markdown(f"**🧭 {formatted}**")
                            st.caption(f"方位:{ori['direction']['cardinal']} |相对:{ori['direction']['relative']} |距离:{ori['direction']['distance']:.1f}米")
                        
                        # 楼层过渡提示
                        if is_transition:
                            if to_node.type == 'elevator':
                                st.info(f"🛗 乘坐电梯: {from_node.floor} → {to_node.floor}")
                            elif to_node.type == 'stairs':
                                st.info(f"🪜 通过楼梯: {from_node.floor} → {to_node.floor}")
                        
                        # 语音播放按钮
                        voice_html = f"""
                        <button onclick="speak('{voice_text.replace("'", "\\'")}')" 
                                style="background:#4CAF50;color:white;border:none;padding:10px 20px;border-radius:4px;cursor:pointer;margin-top:10px;width:100%;font-size:14px;">
                            🔊 播放语音引导
                        </button>
                        <script>
                            function speak(text) {{
                                if ('speechSynthesis' in window) {{
                                    const utterance = new SpeechSynthesisUtterance(text);
                                    utterance.lang = 'zh-CN';
                                    utterance.rate = 0.9;
                                    speechSynthesis.speak(utterance);
                                }} else {{
                                    alert('您的浏览器不支持语音播放');
                                }}
                            }}
                        </script>
                        """
                        st.components.v1.html(voice_html, height=55)
            
            # 显示完整路径节点
            with st.expander("👁️ 查看完整路径节点"):
                path_str = " → ".join([graph.get_node(n).name for n in path])
                st.code(path_str, language="")
        
        else:
            st.error("❌ 无法找到有效路径，请检查起点和终点是否正确")
    
    else:
        # 显示使用说明
        st.info("👈 请在左侧选择起点和目标位置，然后点击「开始导航」")
        
        # 建筑概况
        st.markdown("---")
        st.subheader("🏛️ 文萃楼建筑概况")
        st.markdown("""
        文萃楼是北京理工大学良乡校区的大型教学科研综合楼，采用 **U 形布局**，
        由 **13 个分区（A–M）** 和一座 **圆形报告厅** 组成。
        
        - **角楼**（L/J/C/E）：1F–10F，各含独立楼梯、电梯厅
        - **主楼与连接区**（A/B/M/I/K/F/D）：1F–7F
        - **裙房**（G/H）：1F–2F
        - **总房间数**：约 1200+ 间，房间命名格式 `{分区}-{楼层}{序号}`（如 A-405、L-201）
        """)
        
        # 显示项目信息
        st.markdown("---")
        st.subheader("📖 系统说明")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🏗️ 空间模型**
            - 13分区U形楼宇群
            - 基于官方3D平台数据
            - 支持10层多楼层导航
            """)
        
        with col2:
            st.markdown("""
            **🧭 方位导航**
            - 8方位识别系统
            - 地域适配（南/北方）
            - 语音引导功能
            """)
        
        with col3:
            st.markdown("""
            **🗣️ 语义理解**
            - 自然语言输入
            - 模糊匹配搜索
            - 智能位置推荐
            """)
        
        st.markdown("---")
        st.caption("© 2025 北京理工大学 具身智能教学项目")

if __name__ == "__main__":
    main()
