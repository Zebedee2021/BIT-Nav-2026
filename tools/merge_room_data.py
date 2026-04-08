"""
房间数据整合工具

将生成的房间数据整合到主项目文件 wencui_building.json 中

使用方法：
  python tools/merge_room_data.py [--source 源文件] [--target 目标文件]
  
示例：
  python tools/merge_room_data.py
  python tools/merge_room_data.py --source data/wencui_rooms_generated.json
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Set


class RoomDataMerger:
    """房间数据整合器"""
    
    def __init__(self, source_path: str = None, target_path: str = None):
        """
        初始化数据整合器
        
        Args:
            source_path: 源数据文件路径（生成的房间数据）
            target_path: 目标文件路径（主项目数据文件）
        """
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        if source_path is None:
            source_path = os.path.join(self.base_dir, 'data', 'wencui_rooms_generated.json')
        
        if target_path is None:
            target_path = os.path.join(self.base_dir, 'data', 'wencui_building.json')
        
        self.source_path = source_path
        self.target_path = target_path
        
        # 加载数据
        self.source_data = self._load_json(source_path)
        self.target_data = self._load_json(target_path)
        
        print(f"源数据: {source_path}")
        print(f"  - 节点数: {len(self.source_data.get('nodes', {}))}")
        print(f"目标数据: {target_path}")
        print(f"  - 节点数: {len(self.target_data.get('nodes', {}))}")
    
    def _load_json(self, path: str) -> dict:
        """加载JSON文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_json(self, path: str, data: dict):
        """保存JSON文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {path}")
    
    def analyze_zones(self) -> Dict[str, Set[str]]:
        """
        分析各区域在源数据和目标数据中的分布
        
        Returns:
            区域分布统计
        """
        source_zones = {}
        target_zones = {}
        
        # 统计源数据
        for node_id, node in self.source_data.get('nodes', {}).items():
            zone = node.get('zone', 'Unknown')
            if zone not in source_zones:
                source_zones[zone] = set()
            source_zones[zone].add(node_id)
        
        # 统计目标数据
        for node_id, node in self.target_data.get('nodes', {}).items():
            zone = node.get('zone', 'Unknown')
            if zone not in target_zones:
                target_zones[zone] = set()
            target_zones[zone].add(node_id)
        
        return {
            'source': source_zones,
            'target': target_zones
        }
    
    def print_zone_analysis(self):
        """打印区域分析结果"""
        analysis = self.analyze_zones()
        source_zones = analysis['source']
        target_zones = analysis['target']
        
        all_zones = set(source_zones.keys()) | set(target_zones.keys())
        
        print("\n" + "="*70)
        print("区域分布分析")
        print("="*70)
        print(f"{'区域':<6} {'源数据节点':<12} {'目标数据节点':<12} {'状态':<20}")
        print("-"*70)
        
        for zone in sorted(all_zones):
            source_count = len(source_zones.get(zone, set()))
            target_count = len(target_zones.get(zone, set()))
            
            if source_count > 0 and target_count == 0:
                status = "新增区域"
            elif source_count > 0 and target_count > 0:
                status = f"补充 {source_count} 个节点"
            else:
                status = "无变化"
            
            print(f"{zone:<6} {source_count:<12} {target_count:<12} {status:<20}")
        
        print("="*70)
    
    def merge_data(self, backup: bool = True) -> dict:
        """
        合并数据
        
        Args:
            backup: 是否创建备份
            
        Returns:
            合并后的数据
        """
        # 创建备份
        if backup:
            backup_path = self.target_path.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            self._save_json(backup_path, self.target_data)
            print(f"\n已创建备份: {backup_path}")
        
        # 合并节点
        merged_nodes = dict(self.target_data.get('nodes', {}))
        source_nodes = self.source_data.get('nodes', {})
        
        added_count = 0
        updated_count = 0
        
        for node_id, node in source_nodes.items():
            if node_id in merged_nodes:
                # 更新现有节点
                merged_nodes[node_id].update(node)
                updated_count += 1
            else:
                # 添加新节点
                merged_nodes[node_id] = node
                added_count += 1
        
        # 更新目标数据
        self.target_data['nodes'] = merged_nodes
        
        # 更新元数据
        if 'metadata' not in self.target_data:
            self.target_data['metadata'] = {}
        
        self.target_data['metadata']['last_updated'] = datetime.now().isoformat()
        self.target_data['metadata']['total_nodes'] = len(merged_nodes)
        
        print(f"\n合并完成:")
        print(f"  - 新增节点: {added_count}")
        print(f"  - 更新节点: {updated_count}")
        print(f"  - 总节点数: {len(merged_nodes)}")
        
        return self.target_data
    
    def save_merged_data(self, output_path: str = None):
        """
        保存合并后的数据
        
        Args:
            output_path: 输出路径，默认为目标文件路径
        """
        if output_path is None:
            output_path = self.target_path
        
        self._save_json(output_path, self.target_data)
    
    def export_by_zone(self, output_dir: str = None):
        """
        按区域导出数据
        
        Args:
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = os.path.join(self.base_dir, 'data', 'zones')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 按区域分组
        zone_groups = {}
        for node_id, node in self.target_data.get('nodes', {}).items():
            zone = node.get('zone', 'Unknown')
            if zone not in zone_groups:
                zone_groups[zone] = {}
            zone_groups[zone][node_id] = node
        
        # 导出每个区域
        for zone, nodes in zone_groups.items():
            output_path = os.path.join(output_dir, f'zone_{zone}_complete.json')
            
            zone_data = {
                "zone": zone,
                "building": self.target_data.get('building', {}),
                "node_count": len(nodes),
                "nodes": nodes
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(zone_data, f, ensure_ascii=False, indent=2)
            
            print(f"{zone}区数据已导出: {output_path} ({len(nodes)} 个节点)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='房间数据整合工具')
    parser.add_argument('--source', help='源数据文件路径')
    parser.add_argument('--target', help='目标文件路径')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--export-zones', action='store_true', help='按区域导出')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不保存')
    args = parser.parse_args()
    
    try:
        # 创建整合器
        merger = RoomDataMerger(args.source, args.target)
        
        # 分析区域分布
        merger.print_zone_analysis()
        
        if args.dry_run:
            print("\n[试运行模式] 数据未保存")
            return
        
        # 合并数据
        merger.merge_data(backup=not args.no_backup)
        
        # 保存合并结果
        merger.save_merged_data()
        
        # 按区域导出（可选）
        if args.export_zones:
            print("\n正在按区域导出数据...")
            merger.export_by_zone()
        
        print("\n数据整合完成!")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
