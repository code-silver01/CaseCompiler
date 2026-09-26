"""
PDF Generator for CaseCompiler.
Converts the structured 11-section case file into a professional, court-ready,
and lawyer-ready PDF document using ReportLab.
"""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas:
    """Canvas that performs a two-pass calculation to draw 'Page X of Y' in footer."""
    pass


def _fmt_currency(amt: Any) -> str:
    if amt is None:
        return "Amount unknown"
    try:
        val = float(amt)
        return f"Rs. {val:,.2f}"
    except (ValueError, TypeError):
        return f"Rs. {amt}"


def generate_case_pdf(case_file: dict[str, Any]) -> bytes:
    """
    Generate a complete, professionally formatted PDF from the compiled case file dict.
    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    base_styles = getSampleStyleSheet()

    # Custom styles
    c_primary = colors.HexColor("#0F172A")    # Navy 900
    c_gold = colors.HexColor("#B45309")       # Amber/Gold 700
    c_slate_dark = colors.HexColor("#334155") # Slate 700
    c_slate_light = colors.HexColor("#F8FAFC")# Slate 50
    c_border = colors.HexColor("#CBD5E1")     # Slate 300

    title_style = ParagraphStyle(
        "DocTitle",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "SectionHeader",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SubSectionHeader",
        parent=base_styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=c_slate_dark,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )

    italic_style = ParagraphStyle(
        "BodyItalic",
        parent=body_style,
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=base_styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#475569"),
    )

    badge_high = ParagraphStyle(
        "BadgeHigh",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#DC2626"),
    )
    badge_med = ParagraphStyle(
        "BadgeMed",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#D97706"),
    )
    badge_low = ParagraphStyle(
        "BadgeLow",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#059669"),
    )

    elements = []

    # ---------------------------------------------------------
    # Header & Meta
    # ---------------------------------------------------------
    meta = case_file.get("meta", {})
    elements.append(Paragraph("LEGAL INTAKE BRIEF & CASE FILE", title_style))
    elements.append(
        Paragraph(
            "Prepared by CaseCompiler AI | Structured for Legal Practitioner Review",
            subtitle_style,
        )
    )

    # Metadata table
    session_id = meta.get("session_id", "N/A")
    compiled_at = meta.get("compiled_at", "")[:19].replace("T", " ")
    s1 = case_file.get("section_1_executive_summary", {})
    triage_level = s1.get("triage_level", "UNKNOWN")
    triage_score = s1.get("triage_score", 0)

    meta_data = [
        [
            Paragraph("<b>Matter / Session ID:</b>", body_style),
            Paragraph(f"<font face='Courier'>{session_id}</font>", body_style),
            Paragraph("<b>Compiled Date:</b>", body_style),
            Paragraph(compiled_at, body_style),
        ],
        [
            Paragraph("<b>Urgency Triage:</b>", body_style),
            Paragraph(f"<b>{triage_level}</b> (Score: {triage_score}/100)", badge_high if triage_level == "HIGH" else (badge_med if triage_level == "MEDIUM" else badge_low)),
            Paragraph("<b>Jurisdiction / Model:</b>", body_style),
            Paragraph(f"Karnataka / {meta.get('model_used', 'Gemini')}", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[120, 160, 110, 130])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_slate_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    # Disclaimer box
    disclaimer_text = meta.get(
        "disclaimer",
        "WARNING: This document is produced by an AI case organisation tool for the purpose of helping a qualified legal practitioner review a client matter. Nothing in this document constitutes legal advice.",
    )
    disc_table = Table([[Paragraph(f"<b>CONFIDENTIAL LEGAL REVIEW DRAFT:</b> {disclaimer_text}", disclaimer_style)]], colWidths=[520])
    disc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F59E0B")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(disc_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 1: Executive Summary
    # ---------------------------------------------------------
    elements.append(Paragraph("1. Executive Summary", h1_style))
    elements.append(Paragraph(s1.get("summary_note", "No summary available."), body_style))
    elements.append(Spacer(1, 6))

    reasons = s1.get("triage_reasons", [])
    if reasons:
        elements.append(Paragraph("<b>Triage Evaluation Factors:</b>", h2_style))
        for r in reasons:
            elements.append(Paragraph(f"• {r}", body_style))
        elements.append(Spacer(1, 6))

    # Counts grid
    counts_data = [
        [
            Paragraph("<b>Parties:</b>", body_style), Paragraph(str(s1.get("parties_count", 0)), body_style),
            Paragraph("<b>Events:</b>", body_style), Paragraph(str(s1.get("events_count", 0)), body_style),
            Paragraph("<b>Claims:</b>", body_style), Paragraph(str(s1.get("claims_count", 0)), body_style),
            Paragraph("<b>Evidence:</b>", body_style), Paragraph(str(s1.get("evidence_count", 0)), body_style),
        ]
    ]
    counts_table = Table(counts_data, colWidths=[65, 65, 65, 65, 65, 65, 65, 65])
    counts_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_slate_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    elements.append(counts_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 2: Parties
    # ---------------------------------------------------------
    s2 = case_file.get("section_2_parties", {})
    parties = s2.get("parties", [])
    elements.append(Paragraph("2. Parties", h1_style))
    if not parties:
        elements.append(Paragraph("No parties identified.", italic_style))
    else:
        p_rows = [["Name", "Role", "Contact / Details", "Confidence"]]
        for p in parties:
            p_rows.append([
                Paragraph(f"<b>{p.get('name', 'Unknown')}</b>", body_style),
                Paragraph(p.get("role", "N/A").title(), body_style),
                Paragraph(p.get("contact") or p.get("address") or "Not provided", body_style),
                Paragraph(str(p.get("confidence", "medium")).upper(), body_style),
            ])
        p_table = Table(p_rows, colWidths=[140, 100, 200, 80])
        p_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(p_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 3: Chronology (Timeline)
    # ---------------------------------------------------------
    s3 = case_file.get("section_3_chronology", {})
    events = s3.get("events", [])
    elements.append(Paragraph("3. Chronology of Events", h1_style))
    if not events:
        elements.append(Paragraph("No chronological events identified.", italic_style))
    else:
        e_rows = [["Date", "Description", "Source", "Confidence"]]
        for e in events:
            date_str = e.get("date_parsed") or e.get("date_raw") or "Unknown"
            src = e.get("source", {}).get("type", "statement").replace("_", " ").title()
            e_rows.append([
                Paragraph(f"<b>{date_str}</b>", body_style),
                Paragraph(e.get("description", ""), body_style),
                Paragraph(src, body_style),
                Paragraph(str(e.get("confidence", "medium")).upper(), body_style),
            ])
        e_table = Table(e_rows, colWidths=[100, 260, 80, 80])
        e_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(e_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 6: Claims & Legal Assertions
    # ---------------------------------------------------------
    s6 = case_file.get("section_6_claims", {})
    claims = s6.get("claims", [])
    elements.append(Paragraph("4. Claims & Legal Assertions", h1_style))
    if not claims:
        elements.append(Paragraph("No specific legal claims identified.", italic_style))
    else:
        for i, c in enumerate(claims, 1):
            basis = c.get("legal_basis_mentioned") or "General tenancy statute"
            conf = str(c.get("confidence", "medium")).upper()
            elements.append(Paragraph(f"<b>Claim {i}:</b> {c.get('description', '')}", body_style))
            elements.append(Paragraph(f"<i>Legal Basis Noted:</i> {basis} | <i>Confidence:</i> {conf}", italic_style))
            elements.append(Spacer(1, 4))
    elements.append(Spacer(1, 6))

    # ---------------------------------------------------------
    # Section 7: Evidence Map & ML Quality Scores
    # ---------------------------------------------------------
    s7 = case_file.get("section_7_evidence_map", {})
    ev_list = s7.get("evidence", [])
    elements.append(Paragraph("5. Evidence Map & ML Verification Analysis", h1_style))
    if not ev_list:
        elements.append(Paragraph("No evidence documents uploaded.", italic_style))
    else:
        ev_rows = [["Filename", "Type", "ML Quality", "Confidence", "Description & Verified Signals"]]
        for ev in ev_list:
            score = ev.get("quality_score")
            score_text = f"{score:.0f}/100" if score is not None else "N/A"
            doc_type = (ev.get("detected_type") or ev.get("type", "document")).replace("_", " ").title()
            conf_str = str(ev.get("confidence", "medium")).upper()

            signals = ev.get("feature_signals") or {}
            sig_list = []
            if signals.get("ocr_quality"):
                sig_list.append(f"OCR: {signals['ocr_quality']}")
            if signals.get("has_date"):
                sig_list.append("Dated")
            if signals.get("has_parties"):
                sig_list.append("Parties Matched")
            if signals.get("has_financials"):
                sig_list.append("Financials Present")
            if signals.get("timeline_aligned"):
                sig_list.append("Timeline Aligned")
            sig_line = " | ".join(sig_list)

            desc_text = ev.get("description", "")
            if sig_line:
                desc_text += f"<br/><font size='7.5' color='#0284C7'><b>Signals:</b> {sig_line}</font>"

            ev_rows.append([
                Paragraph(f"<b>{ev.get('filename', '')}</b>", body_style),
                Paragraph(doc_type, body_style),
                Paragraph(f"<b>{score_text}</b>", badge_high if (score or 0) >= 75 else (badge_med if (score or 0) >= 50 else badge_low)),
                Paragraph(conf_str, body_style),
                Paragraph(desc_text, body_style),
            ])

        ev_table = Table(ev_rows, colWidths=[110, 70, 60, 65, 215])
        ev_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(ev_table)

    # Financials subsection
    financials = s7.get("financials", [])
    if financials:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<b>Documented Financial Figures:</b>", h2_style))
        f_rows = [["Label", "Amount", "Source"]]
        for f in financials:
            amt_str = _fmt_currency(f.get("amount_inr"))
            f_rows.append([
                Paragraph(f.get("label", "").title(), body_style),
                Paragraph(f"<b>{amt_str}</b>", body_style),
                Paragraph(f.get("source", {}).get("reference") or "Extracted", body_style),
            ])
        f_table = Table(f_rows, colWidths=[200, 140, 180])
        f_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, c_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        elements.append(f_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 8: Inconsistencies & Contradictions
    # ---------------------------------------------------------
    s8 = case_file.get("section_8_inconsistencies", {})
    incons = s8.get("inconsistencies", [])
    critiques = s8.get("critique_findings", [])
    if incons or critiques:
        elements.append(Paragraph("6. Identified Inconsistencies & AI Critique", h1_style))
        for c in incons:
            elements.append(
                Paragraph(
                    f"• <b>[{c.get('type', 'Contradiction').replace('_', ' ').title()}]:</b> {c.get('description', '')}",
                    body_style,
                )
            )
        for cf in critiques:
            elements.append(
                Paragraph(
                    f"• <b>AI Review Finding:</b> {cf.get('description', '')} <i>(Item: {cf.get('affected_item', 'N/A')})</i>",
                    body_style,
                )
            )
        elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Section 10: Potentially Relevant Legal Context (RAG)
    # ---------------------------------------------------------
    s10 = case_file.get("section_10_legal_areas", {})
    rag_results = s10.get("rag_results", [])
    if rag_results:
        elements.append(Paragraph("7. Potentially Relevant Legal Statutes (RAG-Grounded)", h1_style))
        elements.append(Paragraph("<i>Note: Statutory excerpts retrieved for research guidance only — not legal advice.</i>", italic_style))
        elements.append(Spacer(1, 4))
        for r in rag_results[:4]:
            source_doc = r.get("source_document", "Statute Excerpt").replace("_", " ").title()
            excerpt = r.get("excerpt", "").strip()[:350]
            elements.append(Paragraph(f"<b>Provision:</b> {source_doc} (Score: {r.get('relevance_score', 0):.2f})", h2_style))
            elements.append(Paragraph(f"\"{excerpt}...\"", body_style))
            elements.append(Spacer(1, 4))
        elements.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # Section 11: Lawyer Review Action Items
    # ---------------------------------------------------------
    s11 = case_file.get("section_11_lawyer_questions", {})
    lawyer_qs = s11.get("questions", [])
    if lawyer_qs:
        elements.append(Paragraph("8. Action Items for Legal Practitioner", h1_style))
        for i, q in enumerate(lawyer_qs, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {q}", body_style))
            elements.append(Spacer(1, 2))
        elements.append(Spacer(1, 8))

    # Build document
    doc.build(elements)
    return buffer.getvalue()
