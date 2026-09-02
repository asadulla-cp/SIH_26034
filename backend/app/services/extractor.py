from __future__ import annotations

import re
from dataclasses import dataclass, field

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december"

STANDARD_UNITS = {
    "g", "gm", "gms", "gram", "grams", "kg", "kgs", "ml", "l", "ltr", "litre", "liter",
    "cm", "m", "mm", "pcs", "pc", "n", "no", "nos", "number", "units",
}


@dataclass
class FieldHit:
    key: str
    value: str | None
    confidence: float | None
    bbox: dict | None
    raw_matches: list[str] = field(default_factory=list)


FIELD_KEYS = [
    "product_name",
    "manufacturer",
    "address",
    "net_quantity",
    "unit",
    "mrp",
    "mfg_date",
    "consumer_care",
    "country_of_origin",
]


def _join(lines: list[dict]) -> str:
    return "\n".join(l.get("text", "") for l in lines)


def _best_line(lines: list[dict], pattern: re.Pattern) -> tuple[str | None, float | None, dict | None]:
    best = None
    for ln in lines:
        text = ln.get("text") or ""
        if pattern.search(text):
            conf = ln.get("confidence")
            if best is None or (conf or 0) > (best[1] or 0):
                best = (text, conf, ln.get("bbox"))
    return best if best else (None, None, None)


def _hint_fields(lines: list[dict]) -> dict[str, FieldHit]:
    out = {}
    for ln in lines:
        hint = ln.get("field_hint")
        if hint:
            out[hint] = FieldHit(hint, ln.get("text"), ln.get("confidence"), ln.get("bbox"), [ln.get("text")])
    return out


def extract_fields(lines: list[dict], image_quality: float) -> dict[str, FieldHit]:
    hinted = _hint_fields(lines)
    if hinted:
        for k in FIELD_KEYS:
            hinted.setdefault(k, FieldHit(k, None, None, None))
        # unit from net qty
        nq = hinted.get("net_quantity")
        if nq and nq.value and (not hinted.get("unit") or not hinted["unit"].value):
            u = _unit_from_qty(nq.value)
            hinted["unit"] = FieldHit("unit", u, nq.confidence, nq.bbox)
        return hinted

    text = _join(lines)
    hits: dict[str, FieldHit] = {}

    mrp_pat = re.compile(r"(mrp|maximum\s*retail\s*price).{0,40}|(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d{1,2})?", re.I)
    qty_pat = re.compile(r"(net\s*(qty|quantity|wt|weight|content)?|nett?).{0,24}(\d[\d.,]*)\s*([a-z]+)", re.I)
    date_pat = re.compile(rf"(mfg|mfd|pkd|packed|imported|pkg).{{0,16}}((?:{MONTHS})\s*\d{{4}}|\d{{1,2}}[/-]\d{{4}}|\d{{4}})", re.I)
    care_pat = re.compile(r"(consumer\s*care|customer\s*care|toll\s*free|care@|1800[\s-]?\d+|e-?mail)", re.I)
    mfg_pat = re.compile(r"(mfg(?:d)?\s*by|packed\s*by|imported\s*by|marketed\s*by|manufacturer)\s*[:\-]?\s*(.+)", re.I)
    origin_pat = re.compile(r"(country\s*of\s*origin|made\s*in)\s*[:\-]?\s*(.+)", re.I)
    addr_pat = re.compile(r"(address|plot|midc|industrial|pincode|\d{6})", re.I)
    name_pat = re.compile(r"(atta|oil|salt|coffee|pasta|wheat|rice|soap|tea|biscuit|namkeen)", re.I)

    t, c, b = _best_line(lines, mrp_pat)
    mrp_vals = re.findall(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", t or "", flags=re.I)
    hits["mrp"] = FieldHit("mrp", t, c, b, mrp_vals)

    t, c, b = _best_line(lines, qty_pat)
    hits["net_quantity"] = FieldHit("net_quantity", t, c, b)
    unit = _unit_from_qty(t or text)
    hits["unit"] = FieldHit("unit", unit, c, b)

    t, c, b = _best_line(lines, date_pat)
    hits["mfg_date"] = FieldHit("mfg_date", t, c, b)

    t, c, b = _best_line(lines, care_pat)
    if not t:
        # search full blob
        m = care_pat.search(text)
        t = m.group(0) if m else None
    hits["consumer_care"] = FieldHit("consumer_care", t, c, b)

    t, c, b = _best_line(lines, mfg_pat)
    hits["manufacturer"] = FieldHit("manufacturer", t, c, b)

    t, c, b = _best_line(lines, origin_pat)
    hits["country_of_origin"] = FieldHit("country_of_origin", t, c, b)

    t, c, b = _best_line(lines, addr_pat)
    hits["address"] = FieldHit("address", t, c, b)

    t, c, b = _best_line(lines, name_pat)
    if not t and lines:
        # first substantial line as weak product name
        for ln in lines:
            if len(ln.get("text") or "") > 4:
                t, c, b = ln["text"], ln.get("confidence"), ln.get("bbox")
                break
    hits["product_name"] = FieldHit("product_name", t, c, b)

    for k in FIELD_KEYS:
        hits.setdefault(k, FieldHit(k, None, None, None))
    return hits


def _unit_from_qty(s: str) -> str | None:
    m = re.search(r"(\d[\d.,]*)\s*([a-zA-Z]+)", s)
    if not m:
        return None
    return m.group(2).lower()


def looks_imported(lines: list[dict], hits: dict[str, FieldHit]) -> bool:
    blob = _join(lines).lower()
    mfg = (hits.get("manufacturer").value or "").lower() if hits.get("manufacturer") else ""
    return "imported" in blob or "imported" in mfg
