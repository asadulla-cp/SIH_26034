"""
MetaLex Legal Notice Generator
Generates official, court-ready Legal Notices under Section 18 of the Legal Metrology Act, 2009
with statutory penalty calculations, section references, violation breakdown, and 30-day response deadline.
"""
import io
import os
import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, red
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

# Palette
NAVY = HexColor("#0f172a")
PRIMARY = HexColor("#1e3a8a")
SECONDARY = HexColor("#334155")
DANGER = HexColor("#b91c1c")
LIGHT_BG = HexColor("#f8fafc")
BORDER = HexColor("#cbd5e1")

# Legal Metrology Act Statutory Penalty Schedule (1st Offence)
STATUTORY_PENALTIES = {
    "LM-PC-003": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(c)"},
    "LM-PC-004": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(e)"},
    "LM-PC-001": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(a)"},
    "LM-PC-002": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(b)"},
    "LM-PC-005": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(d)"},
    "LM-PC-006": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(d)"},
    "LM-PC-007": {"section": "Section 18(1) read with Section 36(1)", "penalty": 25000, "rule": "Rule 6(1)(g)"},
    "LM-PC-FS-001": {"section": "Section 36(1) read with Rule 32(2)", "penalty": 10000, "rule": "Rule 7 Table I"},
    "LM-PC-FS-002": {"section": "Section 36(1) read with Rule 32(2)", "penalty": 10000, "rule": "Rule 7 Table I"},
    "LM-PC-FS-003": {"section": "Section 36(1) read with Rule 32(2)", "penalty": 10000, "rule": "Rule 7 Table I"},
    "LM-PC-BC-001": {"section": "Section 18(2) read with Section 36(2)", "penalty": 50000, "rule": "Rule 18(2) & GS1 Directives"},
    "LM-PC-ANOM-001": {"section": "Section 18(2) read with Section 36(2)", "penalty": 50000, "rule": "Rule 18(2) Anti-Tampering"},
    "LM-PC-LANG-001": {"section": "Section 36(1) read with Rule 32", "penalty": 10000, "rule": "Rule 9(1)"},
}

DEFAULT_PENALTY = {"section": "Section 36(1)", "penalty": 10000, "rule": "Rule 32"}


def calculate_notice_penalties(violations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates itemized and aggregate statutory penalties for all violations.
    """
    itemized = []
    total = 0

    for v in violations:
        rule_id = v.get("rule_id", "")
        info = STATUTORY_PENALTIES.get(rule_id, DEFAULT_PENALTY)
        penalty_val = info["penalty"]
        total += penalty_val
        itemized.append({
            "rule_id": rule_id,
            "title": v.get("title", rule_id),
            "section": info["section"],
            "rule": info["rule"],
            "reason": v.get("reason", ""),
            "penalty": penalty_val,
            "penalty_formatted": f"₹{penalty_val:,}"
        })

    return {
        "total_penalty": total,
        "total_penalty_formatted": f"₹{total:,}",
        "itemized_violations": itemized,
        "count": len(itemized)
    }


def generate_legal_notice_pdf(
    inspection: Dict[str, Any],
    notice_id: str,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generates an official Legal Metrology Show Cause Notice in court-admissible PDF format.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    header_title = ParagraphStyle(
        "NoticeHeader", parent=styles["Title"],
        fontSize=13, leading=16, textColor=PRIMARY, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=2 * mm
    )
    header_sub = ParagraphStyle(
        "NoticeSub", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=SECONDARY, alignment=TA_CENTER,
        fontName="Helvetica", spaceAfter=4 * mm
    )
    section_heading = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        fontSize=11, leading=14, textColor=PRIMARY, fontName="Helvetica-Bold",
        spaceBefore=4 * mm, spaceAfter=2 * mm
    )
    body_text = ParagraphStyle(
        "BodyJustify", parent=styles["Normal"],
        fontSize=9.5, leading=13.5, textColor=NAVY, alignment=TA_JUSTIFY,
        fontName="Helvetica", spaceAfter=3 * mm
    )
    table_cell = ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontSize=8.5, leading=11, textColor=NAVY, fontName="Helvetica"
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold", parent=styles["Normal"],
        fontSize=8.5, leading=11, textColor=NAVY, fontName="Helvetica-Bold"
    )

    story = []

    # 1. Government Emblem / Directorate Header
    story.append(Paragraph("GOVERNMENT OF INDIA", header_title))
    story.append(Paragraph("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION", header_sub))
    story.append(Paragraph("DEPARTMENT OF CONSUMER AFFAIRS &middot; LEGAL METROLOGY DIVISION", header_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=4 * mm))

    # 2. Notice Identification & Date Banner
    today = datetime.datetime.now().strftime("%d-%B-%Y")
    deadline = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%d-%B-%Y")
    
    meta_table_data = [
        [
            Paragraph(f"<b>NOTICE NO:</b> {notice_id}", table_cell_bold),
            Paragraph(f"<b>DATE OF ISSUE:</b> {today}", ParagraphStyle("RightDate", parent=table_cell_bold, alignment=TA_RIGHT))
        ],
        [
            Paragraph(f"<b>INSPECTION REF:</b> {inspection.get('inspection_id', 'MLX-INSP')}", table_cell),
            Paragraph(f"<b>RESPONSE DEADLINE:</b> {deadline} (30 Days)", ParagraphStyle("RightDead", parent=table_cell_bold, textColor=DANGER, alignment=TA_RIGHT))
        ]
    ]
    meta_t = Table(meta_table_data, colWidths=[90 * mm, 84 * mm])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 4 * mm))

    # 3. Addressee (Manufacturer / Packer / Importer)
    mfg_name = "The Managing Director / Authorized Signatory"
    mfg_details = "Packer / Manufacturer of subject commodity"
    for f in inspection.get("fields", []):
        if f.get("field_name") == "manufacturer" and f.get("detected_value"):
            mfg_details = f.get("detected_value")
            break

    story.append(Paragraph("<b>TO:</b>", body_text))
    story.append(Paragraph(f"<b>{mfg_name}</b><br/>{mfg_details}", ParagraphStyle("MfgAddr", parent=body_text, leftIndent=10 * mm)))
    story.append(Spacer(1, 2 * mm))

    # 4. Subject & Legal Notice Title
    subject_box = [
        [Paragraph(
            "<b><u>SHOW CAUSE NOTICE UNDER SECTION 18 OF THE LEGAL METROLOGY ACT, 2009 READ WITH RULE 32 OF THE LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011</u></b>",
            ParagraphStyle("Subj", parent=body_text, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=PRIMARY)
        )]
    ]
    subj_t = Table(subject_box, colWidths=[174 * mm])
    subj_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, PRIMARY),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(subj_t)
    story.append(Spacer(1, 4 * mm))

    # 5. Formal Notice Body
    prod_name = inspection.get("product_name", "Packaged Commodity")
    location_str = ""
    if inspection.get("latitude") and inspection.get("longitude"):
        location_str = f" at GPS Coordinates ({inspection['latitude']:.4f}°N, {inspection['longitude']:.4f}°E)"

    body_para_1 = (
        f"WHEREAS, an official statutory inspection of the packaged commodity titled <b>'{prod_name}'</b> was conducted{location_str} "
        f"under the enforcement mandate of the Legal Metrology Act, 2009. Automated vision verification and optical inspection "
        f"of the packaging declarations have revealed prima facie contraventions of the mandatory Legal Metrology (Packaged Commodities) Rules, 2011."
    )
    story.append(Paragraph(body_para_1, body_text))

    # 6. Itemized Violations & Penalties Table
    penalties_data = calculate_notice_penalties(inspection.get("violations", []))
    
    story.append(Paragraph("<b>SPECIFICATION OF OFFENCES & STATUTORY PENALTIES:</b>", section_heading))

    viol_headers = [
        Paragraph("<b>#</b>", table_cell_bold),
        Paragraph("<b>Rule & Legal Provision</b>", table_cell_bold),
        Paragraph("<b>Nature of Violation</b>", table_cell_bold),
        Paragraph("<b>Statutory Section</b>", table_cell_bold),
        Paragraph("<b>Compounding Penalty</b>", table_cell_bold)
    ]
    
    viol_rows = [viol_headers]
    for idx, v in enumerate(penalties_data["itemized_violations"]):
        viol_rows.append([
            Paragraph(str(idx + 1), table_cell),
            Paragraph(f"<b>{v['rule_id']}</b><br/>{v['rule']}", table_cell),
            Paragraph(f"<b>{v['title']}</b><br/>{v['reason']}", table_cell),
            Paragraph(v["section"], table_cell),
            Paragraph(v["penalty_formatted"], ParagraphStyle("RightPen", parent=table_cell_bold, alignment=TA_RIGHT, textColor=DANGER))
        ])

    # Total row
    viol_rows.append([
        Paragraph("<b>TOTAL</b>", table_cell_bold),
        Paragraph("", table_cell),
        Paragraph(f"<b>Total Violations Detected: {penalties_data['count']}</b>", table_cell_bold),
        Paragraph("<b>Cumulative Fine:</b>", table_cell_bold),
        Paragraph(f"<b>{penalties_data['total_penalty_formatted']}</b>", ParagraphStyle("TotPen", parent=table_cell_bold, alignment=TA_RIGHT, textColor=DANGER, fontSize=9.5))
    ])

    v_table = Table(viol_rows, colWidths=[8 * mm, 38 * mm, 62 * mm, 38 * mm, 28 * mm])
    v_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("PADDING", (0, 0), (-1, -1), 3.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#f1f5f9")),
    ]))
    story.append(v_table)
    story.append(Spacer(1, 4 * mm))

    # 7. Directions & Legal Warning
    directions = (
        f"NOW THEREFORE, notice is hereby given requiring you to <b>SHOW CAUSE</b> in writing within <b>thirty (30) days</b> "
        f"of the receipt of this notice (i.e. on or before <b>{deadline}</b>) as to why legal proceedings under Section 36 of the "
        f"Legal Metrology Act, 2009 should not be initiated against you, or why the offence should not be compounded under Section 48 "
        f"upon payment of the statutory fine of <b>{penalties_data['total_penalty_formatted']}</b>.<br/><br/>"
        f"Please take notice that failure to submit a written explanation or rectify the non-compliant packaging within the stipulated "
        f"timeframe will result in prosecution before the competent Court of Metropolitan Magistrate without any further reference."
    )
    story.append(Paragraph(directions, body_text))
    story.append(Spacer(1, 6 * mm))

    # 8. Signature Block
    sig_data = [
        [
            Paragraph("<b>Digital Verification Stamp:</b><br/>MetaLex AI Enforcement Portal<br/>SHA-256 Audit Trail Logged", table_cell),
            Paragraph("<b>By Order of the Authorized Officer</b><br/>Legal Metrology Enforcement Directorate<br/>Department of Consumer Affairs, New Delhi", ParagraphStyle("SigRight", parent=table_cell, alignment=TA_RIGHT))
        ]
    ]
    sig_t = Table(sig_data, colWidths=[87 * mm, 87 * mm])
    sig_t.setStyle(TableStyle([
        ("PADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    
    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3 * mm),
        sig_t
    ]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
