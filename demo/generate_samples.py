#!/usr/bin/env python3
"""Generate synthetic Indian packaged-commodity labels and ground-truth fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "images"
W, H = 720, 1040


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_label(lines: list[dict], banner: str, product: str, accent: tuple) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, H), (248, 246, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 118], fill=accent)
    d.text((36, 28), banner, fill=(255, 255, 255), font=font(22, True))
    d.text((36, 62), product, fill=(255, 248, 220), font=font(28, True))
    d.rectangle([24, 140, W - 24, H - 36], outline=(40, 48, 64), width=3)
    d.text((36, 156), "STATUTORY DECLARATIONS (SAMPLE PACK)", fill=(90, 70, 40), font=font(13, True))

    boxes = {}
    y = 200
    for item in lines:
        key = item["key"]
        label = item["label"]
        value = item["value"]
        if not item.get("show", True):
            continue
        d.text((44, y), label, fill=(90, 90, 90), font=font(13))
        vy = y + 22
        d.text((44, vy), value, fill=(20, 24, 32), font=font(18, True))
        bbox = d.textbbox((44, vy), value, font=font(18, True))
        boxes[key] = {
            "x": bbox[0] / W,
            "y": bbox[1] / H,
            "w": (bbox[2] - bbox[0]) / W,
            "h": (bbox[3] - bbox[1]) / H,
            "text": value,
        }
        y += 78
        d.line([(44, y - 18), (W - 48, y - 18)], fill=(220, 214, 200), width=1)
    d.text((36, H - 28), "DEMO / SAMPLE DATA — not a real commercial package", fill=(140, 120, 90), font=font(12))
    return img, boxes


def blur_degrade(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.GaussianBlur(2.4))
    img = ImageEnhance.Contrast(img).enhance(0.55)
    img = ImageEnhance.Brightness(img).enhance(1.15)
    return img


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    samples = []

    def add(sample_id, title, scenario, banner, product, accent, lines, degrade=False, extra=None):
        img, boxes = draw_label(lines, banner, product, accent)
        if degrade:
            img = blur_degrade(img)
        path = IMG_DIR / f"{sample_id}.png"
        img.save(path)
        fields = {ln["key"]: ln["value"] if ln.get("show", True) else None for ln in lines}
        ocr_lines = []
        for k, b in boxes.items():
            ocr_lines.append({
                "text": b["text"],
                "confidence": 0.41 if degrade and k == "mrp" else (0.48 if degrade else 0.93),
                "bbox": {kk: b[kk] for kk in ("x", "y", "w", "h")},
                "field_hint": k,
            })
        rec = {
            "id": sample_id,
            "title": title,
            "scenario": scenario,
            "demo": True,
            "image": f"demo/images/{sample_id}.png",
            "fields": fields,
            "imported": any("Imported" in (ln.get("value") or "") for ln in lines),
            "ocr_lines": ocr_lines,
            "image_quality": 0.32 if degrade else 0.91,
            "notes": extra or "",
        }
        if degrade:
            rec["fields"]["mrp"] = "₹I99"
            rec["ambiguous"] = True
        samples.append(rec)

    common_ok = [
        {"key": "product_name", "label": "NAME OF COMMODITY", "value": "Whole Wheat Atta"},
        {"key": "manufacturer", "label": "MFG BY / PACKED BY", "value": "Kisan Harvest Foods Pvt Ltd"},
        {"key": "address", "label": "ADDRESS", "value": "Plot 14, MIDC, Nashik, Maharashtra 422010"},
        {"key": "net_quantity", "label": "NET QUANTITY", "value": "5 kg"},
        {"key": "unit", "label": "UNIT", "value": "kg"},
        {"key": "mrp", "label": "MRP (INCL. OF ALL TAXES)", "value": "₹249.00"},
        {"key": "mfg_date", "label": "PKD", "value": "PKD: Jul 2026"},
        {"key": "consumer_care", "label": "CONSUMER CARE", "value": "Care: 1800-208-1234 | care@kisanharvest.in"},
        {"key": "country_of_origin", "label": "COUNTRY OF ORIGIN", "value": "India"},
    ]

    add(
        "sample-compliant",
        "Fully compliant atta pack",
        "All commonly mapped declarations present",
        "META LEX  ·  SAMPLE PACK 01",
        "KISAN HARVEST ATTA",
        (46, 92, 58),
        common_ok,
    )

    missing_mrp = [dict(x) for x in common_ok]
    for ln in missing_mrp:
        if ln["key"] == "mrp":
            ln["show"] = False
        if ln["key"] == "product_name":
            ln["value"] = "Refined Sunflower Oil"
        if ln["key"] == "net_quantity":
            ln["value"] = "1 L"
        if ln["key"] == "unit":
            ln["value"] = "L"
    add(
        "sample-missing-mrp",
        "Missing MRP",
        "Net quantity present; MRP not printed",
        "META LEX  ·  SAMPLE PACK 02",
        "GOLD DROP OIL",
        (176, 92, 32),
        missing_mrp,
    )

    missing_care = [dict(x) for x in common_ok]
    for ln in missing_care:
        if ln["key"] == "consumer_care":
            ln["show"] = False
        if ln["key"] == "product_name":
            ln["value"] = "Iodised Crystal Salt"
        if ln["key"] == "net_quantity":
            ln["value"] = "1 kg"
    add(
        "sample-missing-care",
        "Missing consumer care",
        "Consumer care / complaint contact omitted",
        "META LEX  ·  SAMPLE PACK 03",
        "SAGAR SALT",
        (36, 80, 140),
        missing_care,
    )

    poor = [dict(x) for x in common_ok]
    for ln in poor:
        if ln["key"] == "mrp":
            ln["value"] = "MRP Rs I99 incl. taxes"
        if ln["key"] == "product_name":
            ln["value"] = "Instant Coffee Mix"
        if ln["key"] == "net_quantity":
            ln["value"] = "200 g"
        if ln["key"] == "unit":
            ln["value"] = "g"
    add(
        "sample-poor-ocr",
        "Poor OCR / ambiguous MRP",
        "Low contrast label; MRP may read as I99 instead of 199",
        "META LEX  ·  SAMPLE PACK 04",
        "AROMA BREW",
        (70, 70, 90),
        poor,
        degrade=True,
        extra="Low OCR confidence must yield NEEDS REVIEW, not automatic FAIL.",
    )

    multi = [
        {"key": "product_name", "label": "NAME OF COMMODITY", "value": "Imported Pasta"},
        {"key": "manufacturer", "label": "IMPORTED BY", "value": "Blue Bay Traders"},
        {"key": "address", "label": "ADDRESS", "value": "Mumbai"},
        {"key": "net_quantity", "label": "NET QUANTITY", "value": "500", "show": True},
        {"key": "unit", "label": "UNIT", "value": None, "show": False},
        {"key": "mrp", "label": "MRP", "value": None, "show": False},
        {"key": "mfg_date", "label": "DATE", "value": None, "show": False},
        {"key": "consumer_care", "label": "CONSUMER CARE", "value": None, "show": False},
        {"key": "country_of_origin", "label": "COUNTRY OF ORIGIN", "value": None, "show": False},
    ]
    add(
        "sample-multi-fail",
        "Multiple violations (imported)",
        "Incomplete address, missing MRP, date, care, origin, unit on imported pasta",
        "META LEX  ·  SAMPLE PACK 05",
        "NAPOLI PASTA",
        (120, 40, 48),
        multi,
        extra="Imported indicator without country of origin.",
    )

    (ROOT / "samples.json").write_text(json.dumps(samples, indent=2), encoding="utf-8")
    print(f"Wrote {len(samples)} samples to {IMG_DIR}")


if __name__ == "__main__":
    main()
