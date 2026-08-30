import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

STATUS_COLORS = {
    "PASS": colors.HexColor("#1a7f37"),
    "FAIL": colors.HexColor("#c0392b"),
    "NEEDS_REVIEW": colors.HexColor("#b8860b"),
    "COMPLIANT": colors.HexColor("#1a7f37"),
    "NON_COMPLIANT": colors.HexColor("#c0392b"),
    "NEEDS_REVIEW_OVERALL": colors.HexColor("#b8860b"),
}


def generate_pdf_report(inspection: dict, fields: list, violations: list, image_path: str = None) -> str:
    out_path = os.path.join(REPORTS_DIR, f"{inspection['id']}.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12)
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    story = []
    story.append(Paragraph("MetaLex — Legal Metrology Compliance Inspection Report", title_style))
    if inspection.get("is_demo"):
        story.append(Paragraph("<b>DEMO DATA</b> — generated from a synthetic sample package for demonstration purposes.", small))
    story.append(Spacer(1, 8))

    meta_table = Table([
        ["Inspection ID", inspection["id"]],
        ["Product Name", inspection.get("product_name") or "—"],
        ["Timestamp (UTC)", str(inspection["created_at"])],
        ["Ruleset Version", inspection["ruleset_version"]],
        ["Overall Status", inspection["overall_status"]],
        ["Compliance Score", f"{inspection['compliance_score']} / 100"],
    ], colWidths=[150, 320])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    if image_path and os.path.exists(image_path):
        try:
            story.append(Paragraph("Package Image (Evidence)", h2))
            story.append(RLImage(image_path, width=140 * mm, height=140 * mm, kind="proportional"))
        except Exception:
            pass

    story.append(Paragraph("Extracted Declarations", h2))
    field_rows = [["Field", "Detected Value", "Confidence", "Status"]]
    status_by_field = {v["field"]: v["status"] for v in violations}
    for f in fields:
        status = status_by_field.get(f["field"], "—")
        conf = f"{f['confidence']*100:.0f}%" if f["value"] else "—"
        field_rows.append([f["field"].replace("_", " ").title(), f["value"] or "Missing", conf, status])
    ftable = Table(field_rows, colWidths=[110, 210, 70, 90])
    ftable.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
    ]))
    story.append(ftable)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Violations & Review Items", h2))
    problem_rows = [v for v in violations if v["status"] != "PASS"]
    if not problem_rows:
        story.append(Paragraph("No violations detected. All applicable declarations passed deterministic validation.", normal))
    else:
        vrows = [["Rule", "Field", "Severity", "Status", "Reason"]]
        for v in problem_rows:
            vrows.append([v["rule_id"], v["field"].replace("_", " ").title(), v["severity"], v["status"], v["reason"]])
        vtable = Table(vrows, colWidths=[60, 80, 55, 75, 210])
        vtable.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(vtable)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Note: Rule text used in this prototype is a simplified demonstration mapping and has not been "
        "certified against the official Legal Metrology (Packaged Commodities) Rules, 2011 Gazette text. "
        "Verify officially before any enforcement action.", small))

    doc.build(story)
    return out_path
