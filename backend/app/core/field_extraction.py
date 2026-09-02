"""
Structured field extraction from raw OCR words.

PACKAGE IMAGE -> OCR WORDS -> LINE GROUPING (spatial) -> FIELD CLASSIFICATION
(regex + keyword + spatial proximity) -> CANDIDATE RANKING -> ExtractedField per field.

No LLM is used. This is deterministic pattern matching + confidence scoring.
"""
import re
import sys, os
from typing import List, Dict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from backend.rules.validators.base import ExtractedField

CURRENCY_RE = re.compile(r"(₹|rs\.?|inr)\s*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE)
QTY_RE = re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(g|kg|ml|l|mg|gm|gms)\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b((0?[1-9]|1[0-2])[/\-\.]\d{4}|(\d{1,2})[/\-\.](0?[1-9]|1[0-2])[/\-\.]\d{2,4}"
    r"|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4})\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(\+?91[-\s]?)?[6-9]\d{9}\b|1800[-\s]?\d{3}[-\s]?\d{3,4}")
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

KEYWORDS = {
    "manufacturer": ["manufactured by", "marketed by", "packed by", "manufacturer", "packer", "mfg by", "mfd by"],
    "importer": ["imported by", "importer"],
    "address": ["address", "plot no", "sector", "industrial area", "road", "village", "district"],
    "consumer_care": ["consumer care", "customer care", "helpline", "toll free", "customer support", "care no"],
    "country_of_origin": ["country of origin", "made in", "product of"],
    "net_quantity": ["net qty", "net quantity", "net wt", "net weight", "contents"],
    "mrp": ["mrp", "maximum retail price", "m.r.p"],
    "mfg_date": ["mfg", "mfd", "pkd", "packed on", "manufacturing date", "date of mfg", "best before"],
    "product_name": [],  # inferred structurally (largest/topmost line), see heuristic below
}


def _group_words_into_lines(words: List[Dict], y_tolerance: int = 12) -> List[Dict]:
    """Groups OCR words with similar vertical position into lines, sorted left-to-right."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: w["box"]["y"])
    lines = []
    current_line = [sorted_words[0]]
    current_y = sorted_words[0]["box"]["y"]
    for w in sorted_words[1:]:
        if abs(w["box"]["y"] - current_y) <= y_tolerance:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_line = [w]
            current_y = w["box"]["y"]
    lines.append(current_line)

    line_objs = []
    for line in lines:
        line_sorted = sorted(line, key=lambda w: w["box"]["x"])
        text = " ".join(w["text"] for w in line_sorted)
        xs = [w["box"]["x"] for w in line_sorted]
        ys = [w["box"]["y"] for w in line_sorted]
        xe = [w["box"]["x"] + w["box"]["w"] for w in line_sorted]
        ye = [w["box"]["y"] + w["box"]["h"] for w in line_sorted]
        conf = sum(w["confidence"] for w in line_sorted) / len(line_sorted)
        line_objs.append({
            "text": text,
            "confidence": conf,
            "box": {"x": min(xs), "y": min(ys), "w": max(xe) - min(xs), "h": max(ye) - min(ys)},
            "words": line_sorted,
        })
    return line_objs


def _make_candidate(field: str, line: Dict, match_text: str, method: str, boost: float = 0.0) -> Dict:
    conf = min(1.0, max(0.0, line["confidence"] + boost))
    return {
        "field": field,
        "value": match_text.strip(),
        "confidence": round(conf, 3),
        "bounding_box": line["box"],
        "source_text": line["text"],
        "extraction_method": method,
    }


def extract_fields(words: List[Dict]) -> Dict[str, ExtractedField]:
    lines = _group_words_into_lines(words)
    candidates: Dict[str, List[Dict]] = {k: [] for k in KEYWORDS.keys()}

    for line in lines:
        text_low = line["text"].lower()

        # Regex-first fields (high precision patterns)
        cm = CURRENCY_RE.search(line["text"])
        if cm:
            candidates["mrp"].append(_make_candidate("mrp", line, cm.group(0), "regex:currency", boost=0.05))

        qm = QTY_RE.search(line["text"])
        if qm:
            candidates["net_quantity"].append(_make_candidate("net_quantity", line, qm.group(0), "regex:quantity", boost=0.05))

        dm = DATE_RE.search(line["text"])
        if dm and any(k in text_low for k in KEYWORDS["mfg_date"]):
            candidates["mfg_date"].append(_make_candidate("mfg_date", line, dm.group(0), "regex+keyword:date", boost=0.1))
        elif dm:
            candidates["mfg_date"].append(_make_candidate("mfg_date", line, dm.group(0), "regex:date"))

        pm = PHONE_RE.search(line["text"])
        em = EMAIL_RE.search(line["text"])
        if pm or em or any(k in text_low for k in KEYWORDS["consumer_care"]):
            val = (pm.group(0) if pm else None) or (em.group(0) if em else None) or line["text"]
            candidates["consumer_care"].append(_make_candidate("consumer_care", line, val, "regex+keyword:contact", boost=0.05))

        # Keyword-driven fields (spatial: value is same line after keyword, or next line)
        for field_name in ["manufacturer", "importer", "address", "country_of_origin"]:
            for kw in KEYWORDS[field_name]:
                if kw in text_low:
                    value = re.sub(re.escape(kw), "", line["text"], flags=re.IGNORECASE).strip(" :-")
                    if not value:
                        continue
                    candidates[field_name].append(_make_candidate(field_name, line, value, f"keyword:{kw}"))

    # merge importer candidates into manufacturer field (rule engine tracks "manufacturer" as the unified field)
    candidates["manufacturer"].extend(candidates.get("importer", []))

    # Product name heuristic: topmost, reasonably long alphabetic line, not matching other keyword fields
    used_texts = set()
    for f in ["manufacturer", "address", "consumer_care", "mrp", "net_quantity", "mfg_date", "country_of_origin"]:
        for c in candidates[f]:
            used_texts.add(c["source_text"])
    product_lines = [
        l for l in lines
        if l["text"] not in used_texts
        and len(l["text"]) >= 4
        and re.search(r"[A-Za-z]{3,}", l["text"])
        and not CURRENCY_RE.search(l["text"])
        and not DATE_RE.search(l["text"])
    ]
    if product_lines:
        top_line = sorted(product_lines, key=lambda l: l["box"]["y"])[0]
        candidates["product_name"].append(_make_candidate("product_name", top_line, top_line["text"], "spatial:topmost_line"))

    # Rank candidates per field, pick best, keep alternatives
    extracted: Dict[str, ExtractedField] = {}
    for field_name, cands in candidates.items():
        if field_name == "importer":
            continue
        if not cands:
            extracted[field_name] = ExtractedField(
                field=field_name, value=None, normalized_value=None, confidence=0.0,
                bounding_box=None, source_text=None, extraction_method="not_found",
            )
            continue
        ranked = sorted(cands, key=lambda c: c["confidence"], reverse=True)
        best = ranked[0]
        alternatives = [{"value": c["value"], "confidence": c["confidence"]} for c in ranked[1:4]]
        extracted[field_name] = ExtractedField(
            field=field_name,
            value=best["value"],
            normalized_value=normalize_value(field_name, best["value"]),
            confidence=best["confidence"],
            bounding_box=best["bounding_box"],
            source_text=best["source_text"],
            extraction_method=best["extraction_method"],
            alternatives=alternatives,
        )
    return extracted


def normalize_value(field_name: str, value: str) -> str:
    if value is None:
        return None
    v = value.strip()
    if field_name == "mrp":
        v = v.replace("Rs.", "₹").replace("rs.", "₹").replace("RS.", "₹").replace("INR", "₹")
        v = re.sub(r"\s+", "", v) if v.startswith("₹") else v
    if field_name == "net_quantity":
        v = v.lower().replace("gms", "g").replace("gm", "g")
    return v
