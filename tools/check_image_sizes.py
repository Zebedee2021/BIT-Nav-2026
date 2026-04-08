#!/usr/bin/env python3
"""检查楼层图尺寸"""
from PIL import Image
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("高清楼层图尺寸 (floorplans_hires):")
print("-" * 50)
hires_dir = os.path.join(base_dir, 'data', 'floorplans_hires')
for f in sorted(os.listdir(hires_dir)):
    if f.endswith('.jpg'):
        img = Image.open(os.path.join(hires_dir, f))
        print(f"  {f}: {img.size}")

print("\n统一坐标楼层图尺寸 (floorplans_unified):")
print("-" * 50)
unified_dir = os.path.join(base_dir, 'data', 'floorplans_unified')
for f in sorted(os.listdir(unified_dir)):
    if f.endswith('.jpg') and not f.endswith('_verify.jpg'):
        img = Image.open(os.path.join(unified_dir, f))
        print(f"  {f}: {img.size}")

print("\n对齐后楼层图尺寸 (floorplans_aligned):")
print("-" * 50)
aligned_dir = os.path.join(base_dir, 'data', 'floorplans_aligned')
for f in sorted(os.listdir(aligned_dir)):
    if f.endswith('.jpg'):
        img = Image.open(os.path.join(aligned_dir, f))
        print(f"  {f}: {img.size}")
