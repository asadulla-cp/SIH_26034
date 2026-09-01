"""
MetaLex Commodity Auto-Detector
Maps OCR-extracted text → commodity_category so the rule engine
exemption logic fires automatically without manual input.

Strategy: keyword scoring over all OCR text + extracted product name.
Returns the best-match category and a confidence score.
"""
import re
from typing import Optional

# ── Keyword maps ─────────────────────────────────────────────────────────────
# Each entry: category_key → list of trigger keywords/phrases (lower-case)
COMMODITY_KEYWORDS: dict[str, list[str]] = {
    # Schedule II commodities
    "tea": ["tea", "chai", "green tea", "black tea", "masala tea", "tata tea", "lipton", "red label"],
    "coffee": ["coffee", "instant coffee", "nescafe", "bru coffee", "espresso", "cappuccino"],
    "biscuits": ["biscuit", "biscuits", "cookies", "cream biscuit", "glucose biscuit", "marie"],
    "bread": ["bread", "white bread", "brown bread", "whole wheat bread", "loaf"],
    "butter": ["butter", "amul butter", "dairy butter", "white butter", "salted butter"],
    "cereals": ["cereal", "cereals", "cornflakes", "oats", "muesli", "porridge", "poha", "daliya",
                "corn flakes", "wheat flakes", "rice flakes", "pulses", "dal", "lentils", "rajma",
                "chana", "moong", "urad"],
    "edible_oil": ["oil", "edible oil", "sunflower oil", "mustard oil", "groundnut oil",
                   "coconut oil", "palm oil", "soybean oil", "refined oil", "vegetable oil",
                   "vanaspati", "ghee", "dalda"],
    "milk_powder": ["milk powder", "skimmed milk", "full cream milk powder", "instant milk",
                    "baby milk", "infant formula", "amul spray", "lactogen"],
    "baby_food": ["baby food", "infant food", "cerelac", "nestum", "farex", "weaning food"],
    "detergent": ["detergent", "washing powder", "surf", "ariel", "tide", "rin", "nirma",
                  "wheel", "dish wash", "vim", "henko", "liquid detergent", "fabric wash"],
    "atta": ["atta", "wheat flour", "maida", "besan", "rawa", "suji", "semolina",
             "whole wheat", "multigrain flour", "aashirvaad", "annapurna", "pillsbury"],
    "salt": ["salt", "iodised salt", "rock salt", "sea salt", "tata salt", "annapurna salt",
             "sendha namak", "black salt"],
    "soap": ["soap", "bar soap", "bathing soap", "lux", "dove", "lifebuoy", "hamam",
             "dettol soap", "pears", "rexona", "santoor", "toilet soap"],
    "soft_drink": ["soft drink", "cola", "pepsi", "coca cola", "coke", "sprite", "fanta",
                   "limca", "thums up", "maaza", "slice", "frooti", "soda", "aerated drink",
                   "carbonated", "energy drink", "red bull"],
    "mineral_water": ["mineral water", "drinking water", "packaged water", "bisleri", "kinley",
                      "aquafina", "himalayan water", "packaged drinking water", "still water"],
    "cement": ["cement", "opc cement", "ppc cement", "ultratech", "ambuja cement",
               "acc cement", "shree cement", "jk cement"],
    "paint": ["paint", "emulsion paint", "enamel paint", "berger", "asian paints",
              "nerolac", "dulux", "primer", "wall paint"],

    # Non-Schedule II but important for exemptions
    "bidi": ["bidi", "beedi", "beedis", "bidis", "tobacco bidi"],
    "incense_stick": ["agarbatti", "incense stick", "dhoop", "sambrani", "incense"],
    "pan_masala": ["pan masala", "gutkha", "gutka", "paan masala", "tobacco mix",
                   "khaini", "zarda", "rajnigandha", "vimal", "pass pass"],
    "food": ["snack", "chips", "namkeen", "biscuit", "chocolate", "candy", "toffee",
             "sweets", "mithai", "pickle", "sauce", "ketchup", "jam", "jelly",
             "butter", "cheese", "paneer", "curd", "yogurt", "dahi", "ice cream",
             "noodles", "pasta", "soup", "instant", "ready to eat", "ready-to-eat",
             "packaged food", "processed food", "spices", "masala", "condiment",
             "health drink", "protein powder", "nutrition", "supplement",
             "fruit juice", "nectar", "drink"],
    "medical_device": ["thermometer", "blood pressure", "bp monitor", "glucometer",
                       "pulse oximeter", "nebulizer", "hearing aid", "syringe",
                       "medical device", "diagnostic", "surgical"],
    "lpg_admin_price": ["lpg", "liquefied petroleum", "cooking gas", "14.2 kg", "5 kg cylinder",
                        "indane", "hp gas", "bharat gas"],
    "seed": ["seed", "seeds", "vegetable seed", "flower seed", "hybrid seed",
             "paddy seed", "wheat seed", "maize seed"],
    "cosmetics": ["shampoo", "conditioner", "face wash", "moisturizer", "lotion",
                  "cream", "face cream", "body lotion", "sunscreen", "talcum",
                  "hair oil", "face pack", "scrub", "toner", "serum", "makeup",
                  "lipstick", "foundation", "mascara", "perfume", "deodorant",
                  "aftershave", "gel", "hair gel", "hair cream", "vaseline",
                  "cold cream", "fairness cream", "anti-aging"],
    "detergent_liquid": ["liquid detergent", "fabric softener", "rinse aid"],
    "mineral_supplement": ["vitamins", "minerals", "ayurvedic", "herbal supplement",
                           "capsule", "tablet", "syrup"],
    "agricultural_produce": ["fertilizer", "pesticide", "herbicide", "fungicide",
                             "insecticide", "crop", "agriculture"],
}

# Schedule II commodities (for standard pack size check)
SCHEDULE_II_SET = {
    "tea", "coffee", "biscuits", "bread", "butter", "cereals",
    "edible_oil", "milk_powder", "baby_food", "detergent", "atta",
    "salt", "soap", "soft_drink", "mineral_water", "cement", "paint"
}

# Fourth Schedule commodities (unit-family overrides)
SCHEDULE_IV_SET = {
    "cosmetics", "soft_drink", "edible_oil", "lpg_admin_price"
}

# Third Schedule commodities (allow "when packed" qualifier)
SCHEDULE_III_SET = {"soap", "cosmetics"}


def detect_commodity_category(
    ocr_text: str,
    product_name: str = "",
    extra_hint: str = "",
) -> dict:
    """
    Detect the commodity category from OCR text.

    Returns:
        {
            "category": str,          # best match key
            "confidence": float,       # 0.0 – 1.0
            "is_schedule_ii": bool,
            "is_schedule_iv": bool,
            "is_schedule_iii": bool,
            "all_matches": list[dict], # top 3 candidates
            "method": str,             # how detection was done
        }
    """
    combined = " ".join([
        ocr_text or "",
        product_name or "",
        extra_hint or "",
    ]).lower()

    # Remove noise
    combined = re.sub(r"[^a-z0-9\s]", " ", combined)
    combined = re.sub(r"\s+", " ", combined).strip()

    scores: dict[str, int] = {}

    for category, keywords in COMMODITY_KEYWORDS.items():
        hit = 0
        for kw in keywords:
            kw_clean = re.sub(r"[^a-z0-9\s]", " ", kw)
            if re.search(r"\b" + re.escape(kw_clean) + r"\b", combined):
                # Longer/more specific keywords score higher
                weight = len(kw_clean.split())
                hit += weight
        if hit > 0:
            scores[category] = hit

    if not scores:
        return _unknown_result()

    # Sort by score descending
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]

    # Confidence: ratio of best score to sum of top-3 scores
    top_scores = [s for _, s in sorted_cats[:3]]
    confidence = round(best_score / max(sum(top_scores), 1), 2)
    confidence = min(confidence, 0.95)

    # Pan masala is high priority — override if detected
    if "pan_masala" in scores and scores["pan_masala"] > 0:
        best_cat = "pan_masala"
        confidence = 0.90

    return {
        "category": best_cat,
        "confidence": confidence,
        "is_schedule_ii": best_cat in SCHEDULE_II_SET,
        "is_schedule_iv": best_cat in SCHEDULE_IV_SET,
        "is_schedule_iii": best_cat in SCHEDULE_III_SET,
        "all_matches": [
            {"category": c, "score": s}
            for c, s in sorted_cats[:3]
        ],
        "method": "keyword_scoring",
    }


def _unknown_result() -> dict:
    return {
        "category": "unknown",
        "confidence": 0.0,
        "is_schedule_ii": False,
        "is_schedule_iv": False,
        "is_schedule_iii": False,
        "all_matches": [],
        "method": "no_match",
    }


def is_food_category(category: str) -> bool:
    food_cats = {
        "tea", "coffee", "biscuits", "bread", "butter", "cereals",
        "edible_oil", "milk_powder", "baby_food", "atta", "salt",
        "soft_drink", "mineral_water", "food", "snack"
    }
    return category in food_cats


def is_exempt_from_mrp(category: str) -> bool:
    return category in {"bidi", "lpg_admin_price"}


def is_exempt_from_date(category: str) -> bool:
    return category in {"bidi", "incense_stick", "lpg_admin_price", "seed"}
