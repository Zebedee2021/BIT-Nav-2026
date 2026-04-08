"""Debug J zone OCR - shows raw detections in the north strip"""
import numpy as np
from PIL import Image
import easyocr
import re

print('Init EasyOCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

# J zone: unified (0,0,590,270) -> orig (76, 456, 695, 1819)
# But J zone nodes at x=76-661, y=503-1819 in original
ROOM_PATTERN = re.compile(r"^([A-M])-?(\d{3,4})$", re.IGNORECASE)

for floor in ['1F', '2F', '3F']:
    print(f'\n=== {floor} (J zone region orig: x=76-695, y=456-1819) ===')
    img = Image.open(f'data/floorplans/{floor}_official.jpg').convert('RGB')

    # Try the full J zone strip
    crop = img.crop((76, 456, 695, 1819))
    img_np = np.array(crop)
    results = reader.readtext(img_np, detail=1, paragraph=False)

    # Filter for room-like labels
    room_results = []
    all_results = []
    for b, text, conf in results:
        cx = sum(p[0] for p in b)/4
        cy = sum(p[1] for p in b)/4
        all_results.append((conf, text, cx, cy))
        if conf > 0.25 and re.match(r"[A-MJ1-9][-]?\d{2,4}", text.strip(), re.IGNORECASE):
            room_results.append((conf, text, cx, cy))

    print(f'  Total detections: {len(results)}, room-like: {len(room_results)}')
    print('  Room-like labels (conf > 0.25):')
    for conf, text, cx, cy in sorted(room_results, key=lambda x:-x[0])[:30]:
        print(f'    conf={conf:.2f} text={repr(text)} at local({cx:.0f},{cy:.0f}) orig({cx+76:.0f},{cy+456:.0f})')
