"""
楼层平面图坐标标注工具

使用方法:
  python tools/annotate_floorplan.py [楼层] [--load 已有JSON]

功能:
  - 打开官方楼层图，点击记录像素坐标
  - 左键点击: 标注一个节点 (弹出输入框填写 ID)
  - 右键点击: 删除最近一个标注
  - 按 S: 保存当前标注到 JSON 文件
  - 按 Q: 退出
  - 支持加载已有标注数据叠加显示
"""

import json
import os
import sys
import argparse
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import RadioButtons, TextBox
from PIL import Image
import numpy as np


# 节点类型颜色映射
TYPE_COLORS = {
    'room': '#FF4444',
    'corridor': '#44FF44',
    'stairs': '#4444FF',
    'elevator': '#FF44FF',
    'entrance': '#FFAA00',
    'circular_hall': '#00CCCC',
    'restroom': '#888888',
}

TYPE_LABELS = {
    'room': '房间',
    'corridor': '走廊',
    'stairs': '楼梯',
    'elevator': '电梯',
    'entrance': '入口',
    'circular_hall': '圆楼',
    'restroom': '卫生间',
}


class FloorplanAnnotator:
    """楼层平面图标注器"""

    def __init__(self, floor: str, image_path: str, load_path: str = None):
        self.floor = floor
        self.image_path = image_path
        self.nodes = []  # 已标注的节点列表
        self.current_type = 'room'  # 当前标注类型
        self.current_zone = 'L'  # 当前分区

        # 加载图片
        self.img = Image.open(image_path)
        self.img_array = np.array(self.img)
        self.img_width, self.img_height = self.img.size
        print(f"图片尺寸: {self.img_width} x {self.img_height}")

        # 加载已有数据
        if load_path and os.path.exists(load_path):
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.nodes = data.get('nodes', [])
            print(f"已加载 {len(self.nodes)} 个节点")

        # 输出文件路径
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'annotations')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_path = os.path.join(self.output_dir, f'{floor}_nodes.json')

    def run(self):
        """启动交互式标注"""
        fig, ax = plt.subplots(1, 1, figsize=(16, 11))
        ax.imshow(self.img_array)
        ax.set_title(f'文萃楼 {self.floor} 标注工具  |  '
                     f'左键=标注  右键=撤销  S=保存  Q=退出',
                     fontsize=12)
        ax.axis('off')

        # 绘制已有节点
        self._draw_existing_nodes(ax)

        # 侧边栏 - 类型选择
        ax_radio = plt.axes([0.02, 0.4, 0.10, 0.25])
        radio_labels = list(TYPE_LABELS.values())
        radio = RadioButtons(ax_radio, radio_labels)
        radio_keys = list(TYPE_LABELS.keys())

        def on_type_change(label):
            idx = radio_labels.index(label)
            self.current_type = radio_keys[idx]
            print(f"当前类型: {self.current_type}")

        radio.on_clicked(on_type_change)

        # 侧边栏 - 分区输入
        ax_zone_label = plt.axes([0.02, 0.35, 0.10, 0.03])
        ax_zone_label.text(0.5, 0.5, '分区:', ha='center', va='center', fontsize=10)
        ax_zone_label.axis('off')
        ax_zone = plt.axes([0.02, 0.31, 0.10, 0.04])
        zone_box = TextBox(ax_zone, '', initial=self.current_zone)

        def on_zone_change(text):
            self.current_zone = text.strip().upper()
            print(f"当前分区: {self.current_zone}")

        zone_box.on_submit(on_zone_change)

        # 状态文本
        ax_status = plt.axes([0.02, 0.02, 0.96, 0.04])
        ax_status.axis('off')
        status_text = ax_status.text(0.5, 0.5, f'已标注: {len(self.nodes)} 个节点  |  类型: {self.current_type}  |  分区: {self.current_zone}',
                                     ha='center', va='center', fontsize=11,
                                     bbox=dict(boxstyle='round', facecolor='lightyellow'))

        def update_status():
            status_text.set_text(
                f'已标注: {len(self.nodes)} 个节点  |  类型: {self.current_type}  |  分区: {self.current_zone}'
            )
            fig.canvas.draw_idle()

        def on_click(event):
            if event.inaxes != ax:
                return

            x, y = int(event.xdata), int(event.ydata)

            if event.button == 1:  # 左键 - 标注
                # 弹出输入框获取 ID
                node_id = input(f"  输入节点 ID (类型={self.current_type}, 分区={self.current_zone}, 坐标=({x},{y})): ").strip()
                if not node_id:
                    print("  已取消")
                    return

                node = {
                    'id': node_id,
                    'type': self.current_type,
                    'floor': self.floor,
                    'zone': self.current_zone,
                    'x': x,
                    'y': y,
                }

                # 如果是房间，默认 name = id
                if self.current_type == 'room':
                    node['name'] = node_id
                    node['description'] = ''
                else:
                    node['name'] = node_id
                    node['description'] = ''

                self.nodes.append(node)
                print(f"  + 已标注: {node_id} @ ({x}, {y})")

                # 绘制节点
                color = TYPE_COLORS.get(self.current_type, '#FFFFFF')
                ax.plot(x, y, 'o', color=color, markersize=8, markeredgecolor='white', markeredgewidth=1.5)
                ax.annotate(node_id, (x, y), textcoords='offset points',
                           xytext=(5, 5), fontsize=7, color=color,
                           fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
                update_status()

            elif event.button == 3:  # 右键 - 撤销
                if self.nodes:
                    removed = self.nodes.pop()
                    print(f"  - 已撤销: {removed['id']}")
                    # 重绘
                    ax.clear()
                    ax.imshow(self.img_array)
                    ax.set_title(f'文萃楼 {self.floor} 标注工具', fontsize=12)
                    ax.axis('off')
                    self._draw_existing_nodes(ax)
                    update_status()

        def on_key(event):
            if event.key == 's':
                self.save()
                print(f"  已保存到 {self.output_path}")
            elif event.key == 'q':
                self.save()
                plt.close()

        fig.canvas.mpl_connect('button_press_event', on_click)
        fig.canvas.mpl_connect('key_press_event', on_key)

        plt.tight_layout()
        plt.show()

    def _draw_existing_nodes(self, ax):
        """绘制已有节点"""
        for node in self.nodes:
            x, y = node['x'], node['y']
            color = TYPE_COLORS.get(node['type'], '#FFFFFF')
            ax.plot(x, y, 'o', color=color, markersize=6,
                   markeredgecolor='white', markeredgewidth=1)
            ax.annotate(node['id'], (x, y), textcoords='offset points',
                       xytext=(5, 5), fontsize=6, color=color,
                       bbox=dict(boxstyle='round,pad=0.1', facecolor='white', alpha=0.7))

    def save(self):
        """保存标注数据"""
        data = {
            'floor': self.floor,
            'image': os.path.basename(self.image_path),
            'image_size': {'width': self.img_width, 'height': self.img_height},
            'node_count': len(self.nodes),
            'nodes': self.nodes,
        }
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(self.nodes)} 个节点到 {self.output_path}")


def main():
    parser = argparse.ArgumentParser(description='楼层平面图坐标标注工具')
    parser.add_argument('floor', nargs='?', default='2F', help='楼层标识 (如 2F, 4F)')
    parser.add_argument('--load', help='加载已有标注 JSON 文件')
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(__file__))
    image_path = os.path.join(base_dir, 'data', 'floorplans', f'{args.floor}_official.jpg')

    if not os.path.exists(image_path):
        print(f"错误: 找不到楼层图 {image_path}")
        sys.exit(1)

    # 默认加载路径
    load_path = args.load
    if not load_path:
        default_load = os.path.join(base_dir, 'data', 'annotations', f'{args.floor}_nodes.json')
        if os.path.exists(default_load):
            load_path = default_load

    annotator = FloorplanAnnotator(args.floor, image_path, load_path)
    annotator.run()


if __name__ == '__main__':
    main()
