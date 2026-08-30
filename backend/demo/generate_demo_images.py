"""
Generates synthetic package label images for demo mode, since no real product
images are supplied. Each is clearly a plain synthetic label (not a photo),
and is labeled as DEMO DATA everywhere in the UI/DB.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT_DIR, exist_ok=True)


def font(size=28):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_label(filename, lines, size=(900, 1100), noise=False, rotate=0, low_contrast=False):
    bg = (235, 230, 210) if not low_contrast else (200, 200, 200)
    fg = (20, 20, 20) if not low_contrast else (170, 170, 170)
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)
    y = 60
    for text, fsize, gap in lines:
        draw.text((60, y), text, fill=fg, font=font(fsize))
        y += gap
    if rotate:
        img = img.rotate(rotate, expand=True, fillcolor=bg)
    path = os.path.join(OUT_DIR, filename)
    img.save(path)
    return path


def generate_all():
    paths = []

    # 1. Fully compliant
    paths.append(make_label("demo_1_compliant.png", [
        ("PREMIUM BASMATI RICE", 40, 70),
        ("Net Qty: 1 kg", 30, 55),
        ("MRP: Rs. 199 (incl. of all taxes)", 30, 55),
        ("Manufactured by: Anna Foods Pvt Ltd", 26, 45),
        ("Plot 12, Industrial Area, Sonipat, Haryana - 131001", 24, 45),
        ("Mfg Date: 03/2026", 26, 45),
        ("Consumer Care: 1800-123-4567", 26, 45),
        ("Country of Origin: India", 24, 45),
    ]))

    # 2. Missing MRP
    paths.append(make_label("demo_2_missing_mrp.png", [
        ("GOLDEN WHEAT FLOUR", 40, 70),
        ("Net Qty: 5 kg", 30, 55),
        ("Manufactured by: Sunrise Mills Ltd", 26, 45),
        ("Sector 5, Panipat, Haryana - 132103", 24, 45),
        ("Mfg Date: 01/2026", 26, 45),
        ("Consumer Care: care@sunrisemills.in", 26, 45),
    ]))

    # 3. Missing consumer care
    paths.append(make_label("demo_3_missing_consumer_care.png", [
        ("COLD PRESSED GROUNDNUT OIL", 34, 70),
        ("Net Qty: 1 L", 30, 55),
        ("MRP: Rs. 245", 30, 55),
        ("Packed by: Village Oil Co-operative", 26, 45),
        ("Main Road, Kolhapur, Maharashtra - 416001", 24, 45),
        ("Pkd Date: 11/2025", 26, 45),
    ]))

    # 4. Poor OCR / ambiguous (low contrast + rotated)
    paths.append(make_label("demo_4_poor_quality.png", [
        ("MYSTERY SNACK MIX", 34, 70),
        ("Net Qty: 200 g", 28, 50),
        ("MRP: Rs. I99", 28, 50),   # OCR-ambiguous digit
        ("Mfd by: XYZ Snacks", 24, 40),
        ("Some Street, Some City", 22, 40),
    ], rotate=7, low_contrast=True))

    # 5. Multiple violations (missing manufacturer, bad unit, no date)
    paths.append(make_label("demo_5_multiple_violations.png", [
        ("FRUIT DRINK CONCENTRATE", 34, 70),
        ("Net Qty: 500 units", 28, 50),   # invalid unit
        ("MRP: Rs. 99", 28, 50),
    ]))

    return paths


if __name__ == "__main__":
    p = generate_all()
    for x in p:
        print(x)
