"""Debug OCR on I zone region"""
import numpy as np
from PIL import Image
import easyocr

print('Init EasyOCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

# I zone orig box (603, 249, 970, 803) - maps to unified (440,230,680,390)
# Also try 3F which has valid x=710-870, y=338-741
for floor in ['1F', '3F']:
    print(f'\n=== {floor} ===')
    img = Image.open(f'data/floorplans/{floor}_official.jpg').convert('RGB')
    # Try both: the reverse-transformed box and a wider box
    for box_name, box in [
        ('I zone box', (603, 249, 970, 803)),
        ('wider box', (500, 200, 1100, 900)),
    ]:
        crop = img.crop(box)
        img_np = np.array(crop)
        results = reader.readtext(img_np, detail=1, paragraph=False)
        print(f'  {box_name} {box}: {len(results)} raw results')
        # Show all results with reasonable confidence
        for b, text, conf in sorted(results, key=lambda x: -x[2])[:20]:
            cx = sum(p[0] for p in b) / 4
            cy = sum(p[1] for p in b) / 4
            # Filter for potentially room-like labels
            if conf > 0.25:
                print(f'    conf={conf:.2f} text={repr(text)} at ({cx:.0f},{cy:.0f})')
