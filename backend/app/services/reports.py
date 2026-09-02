from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import REPORT_DIR
from ..models import Inspection, Report
from .pipeline import serialize_inspection


NAVY = colors.HexColor("#12203A")
GOLD = colors.HexColor("#C9A227")
FAIL = colors.HexColor("#B42318")
OK = colors.HexColor("#067647")
REV = colors.HexColor("#B54708")


def generate_pdf(insp: Inspection) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{insp.id}.pdf"
    data = serialize_inspection(insp)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Heading1"], textColor=NAVY, fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=12, spaceBefore=10)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#444"))

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    story = []
    story.append(Paragraph("MetaLex — Packaged Commodity Inspection Report", title))
    story.append(Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011 — prototype rule pack (not official gazette text).", small))
    story.append(Spacer(1, 8))

    meta = [
        ["Inspection ID", data["id"], "Date/Time (UTC)", data["created_at"]],
        ["Overall status", data["overall_status"].replace("_", " "), "Score", f"{data['compliance_score']} / 100"],
        ["Product", data["product_name"] or "—", "Violations", str(data["violation_count"])],
        ["Pipeline", data["pipeline_mode"], "Image quality", f"{data['image_quality']:.2f}"],
        ["Officer", data["officer_name"] or "Demo officer", "Demo sample", data["demo_sample_id"] or "—"],
    ]
    t = Table(meta, colWidths=[32 * mm, 55 * mm, 38 * mm, 55 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EEF2F7")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    img_path = insp.image_path
    if img_path and Path(img_path).exists():
        story.append(Paragraph("Evidence image", h2))
        story.append(RLImage(img_path, width=85 * mm, height=110 * mm))

    story.append(Paragraph("Extracted declarations", h2))
    rows = [["Field", "Value", "Confidence", "Status"]]
    for f in data["fields"]:
        conf = "—" if f["confidence"] is None else f"{round(f['confidence'] * 100)}%"
        rows.append([f["field_key"], (f["value"] or "Missing")[:80], conf, f["status"]])
    ft = Table(rows, colWidths=[40 * mm, 80 * mm, 28 * mm, 32 * mm])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(ft)

    story.append(Paragraph("Violations / review items", h2))
    if not data["violations"]:
        story.append(Paragraph("No violations recorded by the prototype rule engine.", body))
    else:
        for v in data["violations"]:
            ev = v["evidence"]
            ev_txt = "Bounding box on image." if "bbox" in ev else ev.get("note", "")
            story.append(Paragraph(
                f"<b>{v['rule_id']} v{v['rule_version']}</b> [{v['severity']}/{v['status']}] "
                f"Field: {v['field']}<br/>Detected: {v['detected_value'] or 'Missing'}<br/>"
                f"Expected: {v['expected']}<br/>Reason: {v['reason']}<br/>Evidence: {ev_txt}",
                body,
            ))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}. Deterministic rules decide compliance; OCR/extraction never votes on legality. Prototype mapping only.",
        small,
    ))
    doc.build(story)
    return path


def ensure_report(db, insp: Inspection) -> Report:
    existing = insp.reports[-1] if insp.reports else None
    if existing and Path(existing.pdf_path).exists():
        return existing
    path = generate_pdf(insp)
    rec = Report(inspection_id=insp.id, pdf_path=str(path))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
