"""
Script to generate test package label images for MetaLex demo.
Creates sample product labels with realistic declarations, fonts, and bounding regions.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_label(filename, lines, bg_color=(248, 249, 250), border_color=(40, 50, 70), blur=False):
    width, height = 900, 1100
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([20, 20, width - 20, height - 20], outline=border_color, width=4)
    draw.rectangle([28, 28, width - 28, height - 28], outline=border_color, width=1)

    # Draw header banner
    draw.rectangle([30, 30, width - 30, 140], fill=(26, 35, 126))
    
    y = 60
    # Header title
    draw.text((width // 2, y), lines[0], fill=(255, 255, 255), anchor="mm")

    y = 180
    for line in lines[1:]:
        if not line:
            y += 24
            continue
        
        # Check if header
        if line.startswith("##"):
            draw.text((50, y), line.replace("##", "").strip(), fill=(26, 35, 126))
            y += 35
        elif ":" in line:
            parts = line.split(":", 1)
            draw.text((60, y), parts[0] + ":", fill=(10, 15, 30))
            draw.text((280, y), parts[1].strip(), fill=(30, 40, 60))
            y += 40
        else:
            draw.text((60, y), line, fill=(50, 60, 80))
            y += 35

    # Footer banner
    draw.rectangle([30, height - 100, width - 30, height - 30], fill=(240, 242, 245), outline=(200, 205, 215))
    draw.text((width // 2, height - 65), "LEGAL METROLOGY COMPLIANT PACKAGING", fill=(100, 110, 130), anchor="mm")

    # Save
    out_path = os.path.join(OUTPUT_DIR, filename)
    
    if blur:
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        cv_img = cv2.GaussianBlur(cv_img, (15, 15), 0)
        cv2.imwrite(out_path, cv_img)
    else:
        img.save(out_path)
    
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    # Sample 1: Fully Compliant Premium Tea
    create_label("01_compliant_tea.jpg", [
        "TATA PREMIUM TEA",
        "## MANDATORY DECLARATIONS",
        "Common Name: Tea",
        "Net Quantity: 500 g",
        "MRP: ₹199 (Inclusive of all taxes)",
        "Mfg Date: 08/2026",
        "Manufactured By: Tata Consumer Products Ltd",
        "Address: 1, Bishop Lefroy Road, Kolkata, WB 700020",
        "Consumer Care: 1800-209-8787 / care@tataconsumer.com",
        "Country of Origin: India",
    ])

    # Sample 2: Non-compliant (Missing MRP)
    create_label("02_missing_mrp_noodles.jpg", [
        "QUICKBITE INSTANT NOODLES",
        "## PACKAGED FOOD DECLARATION",
        "Common Name: Instant Noodles",
        "Net Quantity: 70 g",
        "Mfg Date: 07/2026",
        "Manufactured By: QuickBite Foods Pvt Ltd",
        "Address: Sector 62, Noida, Uttar Pradesh 201301",
        "Consumer Care: support@quickbite.in",
        "Country of Origin: India",
    ])

    # Sample 3: Non-compliant (Missing Consumer Care & Address)
    create_label("03_missing_consumer_care_detergent.jpg", [
        "FRESHWASH DETERGENT POWDER",
        "## PRODUCT DECLARATION",
        "Common Name: Detergent",
        "Net Quantity: 1 kg",
        "MRP: ₹89 (Incl. of all taxes)",
        "Mfg Date: 08/2026",
        "Manufactured By: CleanCorp Ltd",
        "Country of Origin: India",
    ])

    # Sample 4: Blurry / Ambiguous Package
    create_label("04_blurry_package.jpg", [
        "GLOWFIT PROTEIN BAR",
        "## NUTRITION PACK",
        "Net Quantity: 60g",
        "MRP: ₹199",
        "Mfg Date: 06/2026",
        "Manufactured By: GlowFit Nutrition Ltd",
        "Consumer Care: 1800-100-9876",
        "Country of Origin: India",
    ], blur=True)
