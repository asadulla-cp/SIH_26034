"""
MetaLex PDF Report Generator
Generates professional compliance inspection reports using ReportLab.
"""
import io
import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, red, green, orange
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie


# Colors
PRIMARY = HexColor("#1a237e")
SECONDARY = HexColor("#283593")
ACCENT = HexColor("#00c853")
DANGER = HexColor("#d50000")
WARNING = HexColor("#ff6d00")
LIGHT_BG = HexColor("#f5f5f5")
BORDER = HexColor("#e0e0e0")


def generate_report(inspection_data: dict, output_path: str | None = None) -> bytes:
    """
    Generate a professional PDF compliance report.

    inspection_data: {
        inspection_id, product_name, created_at,
        overall_status, compliance_score,
        fields: [{field_name, field_label, value, confidence, status}],
        violations: [{rule_id, title, field, severity, detected_value, expected_requirement, reason}],
        image_path, is_demo, rule_set_version, disclaimer
    }
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=22, textColor=PRIMARY, spaceAfter=4 * mm,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#666666"), spaceAfter=6 * mm,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        fontSize=14, textColor=PRIMARY, spaceBefore=8 * mm, spaceAfter=4 * mm,
        fontName="Helvetica-Bold",
    )
    normal_style = ParagraphStyle(
        "ReportNormal", parent=styles["Normal"],
        fontSize=9, spaceAfter=2 * mm, leading=13,
    )
    small_style = ParagraphStyle(
        "ReportSmall", parent=styles["Normal"],
        fontSize=7, textColor=HexColor("#999999"),
    )

    elements = []

    # ── Header ──
    elements.append(Paragraph("⚖️ MetaLex Compliance Report", title_style))

    insp_id = inspection_data.get("inspection_id", "N/A")
    product = inspection_data.get("product_name", "Unknown Product")
    created = inspection_data.get("created_at", datetime.datetime.now().isoformat())
    status = inspection_data.get("overall_status", "PENDING")
    score = inspection_data.get("compliance_score", 0)
    is_demo = inspection_data.get("is_demo", False)

    elements.append(Paragraph(
        f"Inspection ID: <b>{insp_id}</b> &nbsp;|&nbsp; "
        f"Product: <b>{product}</b> &nbsp;|&nbsp; "
        f"Date: <b>{created[:19] if isinstance(created, str) else str(created)[:19]}</b>",
        subtitle_style
    ))

    if is_demo:
        elements.append(Paragraph(
            "⚠️ <b>DEMO DATA</b> — This report was generated from demonstration data.",
            ParagraphStyle("DemoWarning", parent=normal_style, textColor=WARNING, fontSize=10)
        ))
        elements.append(Spacer(1, 3 * mm))

    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    elements.append(Spacer(1, 4 * mm))

    # ── Overall Assessment ──
    elements.append(Paragraph("Overall Assessment", heading_style))

    status_color = ACCENT if status == "COMPLIANT" else (DANGER if status == "NON_COMPLIANT" else WARNING)
    status_text = status.replace("_", " ")

    assessment_data = [
        ["Status", "Compliance Score", "Rule Set Version"],
        [
            Paragraph(f'<font color="{status_color.hexval()}" size="14"><b>{status_text}</b></font>', normal_style),
            Paragraph(f'<font size="14"><b>{score}/100</b></font>', normal_style),
            Paragraph(f'{inspection_data.get("rule_set_version", "1.0.0")}', normal_style),
        ]
    ]
    assessment_table = Table(assessment_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    assessment_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    elements.append(assessment_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Extracted Declarations ──
    elements.append(Paragraph("Extracted Declarations", heading_style))

    fields = inspection_data.get("fields", [])
    if fields:
        field_header = ["Field", "Detected Value", "Confidence", "Status"]
        field_rows = [field_header]

        for f in fields:
            field_label = f.get("field_label", f.get("field_name", ""))
            value = f.get("value") or f.get("detected_value") or "Not detected"
            conf = f.get("confidence", 0)
            fstatus = f.get("status", "PENDING")

            conf_str = f"{conf:.0%}" if conf > 0 else "—"
            status_icon = "✓" if fstatus == "PASS" else ("✗" if fstatus == "FAIL" else "⚠")
            s_color = "#00c853" if fstatus == "PASS" else ("#d50000" if fstatus == "FAIL" else "#ff6d00")

            field_rows.append([
                Paragraph(field_label, normal_style),
                Paragraph(str(value)[:60], normal_style),
                Paragraph(conf_str, normal_style),
                Paragraph(f'<font color="{s_color}"><b>{status_icon} {fstatus}</b></font>', normal_style),
            ])

        field_table = Table(field_rows, colWidths=[40 * mm, 65 * mm, 30 * mm, 40 * mm])
        field_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ]))
        elements.append(field_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Violations ──
    violations = inspection_data.get("violations", [])
    if violations:
        elements.append(Paragraph(f"Violations ({len(violations)})", heading_style))

        for i, v in enumerate(violations, 1):
            sev = v.get("severity", "high")
            sev_color = "#d50000" if sev == "high" else ("#ff6d00" if sev == "medium" else "#ffd600")
            elements.append(Paragraph(
                f'<font color="{sev_color}"><b>❌ {v.get("title", "Violation")}</b></font> '
                f'<font size="7" color="#999">[{v.get("rule_id", "")} | Severity: {sev.upper()}]</font>',
                normal_style,
            ))
            elements.append(Paragraph(
                f'<b>Detected:</b> {v.get("detected_value", "Missing")} &nbsp;&nbsp;'
                f'<b>Expected:</b> {v.get("expected_requirement", "N/A")}',
                normal_style,
            ))
            elements.append(Paragraph(
                f'<b>Reason:</b> {v.get("reason", "")}',
                normal_style,
            ))
            if v.get("is_prototype_rule"):
                elements.append(Paragraph(
                    '<font color="#999" size="7">Prototype validation rule — requires official legal verification.</font>',
                    small_style,
                ))
            elements.append(Spacer(1, 3 * mm))

    # ── Disclaimer ──
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elements.append(Spacer(1, 3 * mm))

    disclaimer = inspection_data.get("disclaimer", "")
    if disclaimer:
        elements.append(Paragraph(
            f'<font size="7" color="#999"><b>Disclaimer:</b> {disclaimer}</font>',
            small_style,
        ))
    elements.append(Paragraph(
        f'<font size="7" color="#999">Generated by MetaLex v1.0 | '
        f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | '
        f'Smart India Hackathon 2026 Prototype</font>',
        small_style,
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
