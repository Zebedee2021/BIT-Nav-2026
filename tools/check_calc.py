#!/usr/bin/env python3
"""检查坐标计算 - 修正版"""

# A-301 坐标
ux, uy = 729, 157
origin_ux, origin_uy = 164, 563
img_w, img_h = 2235, 3614
center_x, center_y = img_w/2, img_h/2
scale = 15

print(f'图片尺寸: {img_w} x {img_h}')
print(f'图片中心: ({center_x}, {center_y})')
print()

# 计算
dx = ux - origin_ux
dy = uy - origin_uy
print(f'A-301: ux={ux}, uy={uy}')
print(f'圆楼:  ux={origin_ux}, uy={origin_uy}')
print(f'dx = {ux} - {origin_ux} = {dx} (东)')
print(f'dy = {uy} - {origin_uy} = {dy} (南为负=北)')
print()

# 修正：south_m = dy / scale (不是 -dy/scale)
# 因为 uy 向南增加，所以 dy 正 = 南，dy 负 = 北
east_m = dx / scale
south_m = dy / scale  # 修正：dy 正 = 南，dy 负 = 北
print(f'east_m = {dx} / {scale} = {east_m:.1f}m (东)')
print(f'south_m = {dy} / {scale} = {south_m:.1f}m (负=北)')
print()

px = center_x + east_m * scale
py = center_y - south_m * scale  # south_m 负 -> py 大 -> 下方
print(f'px = {center_x} + {east_m:.1f} * {scale} = {px:.1f}')
print(f'py = {center_y} - ({south_m:.1f}) * {scale} = {py:.1f}')
print()

print(f'水平位置: {px/img_w*100:.1f}% ({"左" if px < center_x else "右"})')
print(f'垂直位置: {py/img_h*100:.1f}% ({"上" if py < center_y else "下"})')
print()

# 验证
if south_m < 0:
    print(f'south_m={south_m:.1f} < 0，表示在圆楼北边')
    print(f'py={py:.1f} > center_y={center_y}，应该在图片下方 ✓')
else:
    print(f'south_m={south_m:.1f} > 0，表示在圆楼南边')
    print(f'py={py:.1f} < center_y={center_y}，应该在图片上方')
