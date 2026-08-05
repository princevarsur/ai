import io
import re
import datetime
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.pdfgen import canvas
from compliance.models import ScanReport


class NumberedCanvas(canvas.Canvas):
    """Custom canvas to generate 'Page X of Y' footers and top headers on pages 2+."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        # Do not draw running header/footer on Cover Page (Page 1)
        if self._pageNumber > 1:
            self.saveState()
            
            # Running Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(54, 745, "THEMIS STATUTORY COMPLIANCE ASSESSMENT")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 745, f"Report #{getattr(self, '_report_id', '')}")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 737, 558, 737)

            # Running Footer
            self.line(54, 45, 558, 45)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(54, 32, "Confidential & Proprietary — Automated Audit Engine Report")
            self.drawRightString(558, 32, f"Page {self._pageNumber} of {total_pages}")
            
            self.restoreState()
        else:
            # Subtle footer on cover page
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#94A3B8"))
            self.drawString(54, 32, "THEMIS AI Employment Legal Shield")
            self.drawRightString(558, 32, "Strictly Private & Confidential")
            self.restoreState()


def get_score_color(score):
    if score < 40:
        return colors.HexColor("#A33F3F")  # Danger Red
    if score < 70:
        return colors.HexColor("#A67C3D")  # Warning Amber
    return colors.HexColor("#4A7856")      # Success Green


def get_category_name(raw_cat):
    mapping = {
        "labour": "Labour Law & Codes",
        "data_privacy": "Data Privacy & DPDP Act",
        "posh": "POSH Act (Workplace Harassment)",
        "workplace_safety": "Workplace Safety & OSH",
        "contract": "Contract & Restraint Law",
        "epf": "EPF & Social Security",
        "maternity": "Maternity Benefits Act",
        "governance": "Corporate Governance",
    }
    return mapping.get(raw_cat or "", (raw_cat or "General").replace("_", " ").title())


def generate_compliance_pdf(report_id: int) -> bytes:
    """Generate a professional PDF compliance report and return as bytes."""
    try:
        report = ScanReport.objects.select_related("policy", "scanned_by").prefetch_related("flagged_issues__legal_rule").get(pk=report_id)
    except ScanReport.DoesNotExist:
        raise ValueError(f"Report ID {report_id} does not exist.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom editorial text styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=32,
        textColor=colors.HexColor("#1F2227"),
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=24,
    )
    logo_style = ParagraphStyle(
        "LogoStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1F2227"),
        characterSpacing=4,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1F2227"),
        spaceAfter=14,
        spaceBefore=6,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1F2227"),
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10,
    )
    body_bold_style = ParagraphStyle(
        "BodyBold_Custom",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    box_text_style = ParagraphStyle(
        "BoxText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
    )
    fix_text_style = ParagraphStyle(
        "FixText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
    )

    story = []

    # ──────────────────────────────────────────────────────────────────────────
    # PAGE 1: COVER PAGE (EXECUTIVE DASHBOARD UI)
    # ──────────────────────────────────────────────────────────────────────────
    # Dark Header Banner
    header_left = Paragraph("<b><font color='#FFFFFF' size='16' face='Helvetica-Bold'>THEMIS</font></b><br/><font color='#94A3B8' size='8'>ADVANCED STATUTORY COMPLIANCE & RISK ENGINE</font>", styles["Normal"])
    header_right = Paragraph("<p align='right'><b><font color='#FFFFFF' size='11'>EXECUTIVE AUDIT</font></b><br/><font color='#94A3B8' size='8'>STRICTLY CONFIDENTIAL</font></p>", styles["Normal"])
    banner_table = Table([[header_left, header_right]], colWidths=[300, 204])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ('PADDING', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 24))

    policy_title = report.policy.title if report.policy else "Employment Policy Document"
    company_name = getattr(report.scanned_by, "company_name", None) or "Client Organization"
    scan_date_str = report.scanned_at.strftime("%B %d, %Y (%H:%M UTC)") if report.scanned_at else timezone.now().strftime("%B %d, %Y")

    story.append(Paragraph("Statutory Compliance Assessment", title_style))
    story.append(Spacer(1, 4))

    # Two-Column Document Metadata Register
    meta_left = Paragraph(f"<b>Document Under Audit:</b><br/><font color='#1E293B' size='11'><b>{policy_title}</b></font><br/><br/><b>Target Statutory Framework:</b><br/><font color='#475569'>Indian Central Labour Codes & State Rules</font>", body_style)
    meta_right = Paragraph(f"<b>Prepared For:</b><br/><font color='#1E293B' size='11'><b>{company_name}</b></font><br/><br/><b>Evaluation Date:</b><br/><font color='#475569'>{scan_date_str}</font>", body_style)
    meta_card = Table([[meta_left, meta_right]], colWidths=[252, 252])
    meta_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(meta_card)
    story.append(Spacer(1, 24))

    # Interactive-Feeling Executive KPI Dashboard Box
    story.append(Paragraph("Executive Risk Posture Dashboard", h2_style))
    score_val = int(round(report.overall_score))
    score_color = get_score_color(score_val)
    score_hex = "#A33F3F" if score_val < 40 else ("#A67C3D" if score_val < 70 else "#10B981")

    d = Drawing(136, 136)
    d.add(Circle(68, 68, 62, fillColor=colors.HexColor("#F1F5F9"), strokeColor=score_color, strokeWidth=2))
    d.add(Circle(68, 68, 56, fillColor=score_color, strokeColor=None))
    d.add(String(68, 58, f"{score_val}%", textAnchor="middle", fontSize=30, fontName="Helvetica-Bold", fillColor=colors.white))

    kpi_1 = Paragraph(f"<font color='#64748B' size='8'><b>RISK POSTURE</b></font><br/><font color='{score_hex}' size='14'><b>{report.risk_level.upper()} RISK</b></font>", styles["Normal"])
    kpi_2 = Paragraph(f"<font color='#64748B' size='8'><b>TOTAL CLAUSES EVALUATED</b></font><br/><font color='#1E293B' size='14'><b>{report.total_clauses} Clauses</b></font>", styles["Normal"])
    kpi_3 = Paragraph(f"<font color='#64748B' size='8'><b>VERIFIED COMPLIANT / DEFERRED</b></font><br/><font color='#059669' size='14'><b>{report.compliant_clauses} Verified Safe</b></font>", styles["Normal"])
    kpi_4 = Paragraph(f"<font color='#64748B' size='8'><b>STATUTORY DISCREPANCIES</b></font><br/><font color='#DC2626' size='14'><b>{report.flagged_clauses} Actionable Flags</b></font>", styles["Normal"])

    kpi_grid = Table([
        [kpi_1, kpi_2],
        [kpi_3, kpi_4]
    ], colWidths=[170, 174])
    kpi_grid.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    dash_box = Table([[d, kpi_grid]], colWidths=[150, 354])
    dash_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(dash_box)

    story.append(Spacer(1, 28))
    summary_notice = (
        "<b>Executive Audit Scope:</b> This document represents an automated statutory compliance audit comparing the submitted corporate "
        "policy against 44 central Indian labour codes, data privacy regulations (DPDP Act 2023), and workplace harassment laws (POSH Act 2013). "
        "Flagged discrepancies represent potential statutory non-compliance requiring prioritization and remediation."
    )
    notice_box = Table([[Paragraph(summary_notice, body_style)]], colWidths=[504])
    notice_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('LINEBEFORE', (0, 0), (0, -1), 4, colors.HexColor("#0F172A")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(notice_box)
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # PAGE 2: EXECUTIVE SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Compliance Assessment", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F2227"), spaceAfter=14))

    exec_p = (
        f"The compliance evaluation yielded an overall health score of <b>{score_val}%</b> with an organizational "
        f"risk posture classified as <b>{report.risk_level.upper()}</b>. Out of <b>{report.total_clauses}</b> total "
        f"extracted clauses, <b>{report.compliant_clauses}</b> were verified as compliant or lawfully deferring to Indian statutes, "
        f"while <b>{report.flagged_clauses}</b> clause(s) triggered high-risk conflict or gap flags."
    )
    story.append(Paragraph(exec_p, body_style))
    story.append(Spacer(1, 10))

    # Category Breakdown Table
    story.append(Paragraph("Statutory Domain Breakdown", h2_style))
    
    issues = list(report.flagged_issues.all())
    cat_counts = {}
    for issue in issues:
        cat = issue.legal_rule.category if (issue.legal_rule and issue.legal_rule.category) else "general"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    table_data = [["Statutory Domain Category", "Risk Assessment", "Flagged Conflicts"]]
    all_cats = ["labour", "posh", "data_privacy", "workplace_safety", "contract"]
    for c in set(list(cat_counts.keys()) + all_cats):
        cnt = cat_counts.get(c, 0)
        status = "Satisfactory (No Flags)" if cnt == 0 else f"Action Required ({cnt} Issue{'s' if cnt > 1 else ''})"
        table_data.append([get_category_name(c), status, str(cnt)])

    t = Table(table_data, colWidths=[200, 204, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F2227")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # PAGE 3+: FLAGGED ISSUES
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Detailed Statutory Discrepancy Register", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F2227"), spaceAfter=14))

    if not issues:
        ok_box = Table([[Paragraph("<b>No statutory violations or gaps were identified in this policy document.</b><br/>All evaluated clauses conform to current Indian labor standards.", body_style)]], colWidths=[504])
        ok_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#4A7856")),
            ('PADDING', (0, 0), (-1, -1), 16),
        ]))
        story.append(ok_box)
    else:
        for idx, issue in enumerate(issues, 1):
            rule = issue.legal_rule
            law_name = rule.law_name if rule else "Statutory Mandate"
            section = rule.section if rule else "N/A"
            status_tag = issue.status.upper()
            severity_val = issue.severity_score

            header_text = f"<b>Issue #{idx} — {law_name} ({section})</b>"
            badge_text = f"Status: <b>{status_tag}</b> | Severity: <b>{severity_val}/100</b>"
            
            # Refined legal domain color palettes per severity/status
            if status_tag == "CONFLICT":
                bg_col = colors.HexColor("#FEE2E2")
                border_col = colors.HexColor("#EF4444")
                text_col = "#7F1D1D"
            elif status_tag == "MISSING":
                bg_col = colors.HexColor("#FEF3C7")
                border_col = colors.HexColor("#F59E0B")
                text_col = "#78350F"
            elif status_tag == "GAP":
                bg_col = colors.HexColor("#E2E8F0")
                border_col = colors.HexColor("#64748B")
                text_col = "#1E293B"
            else:
                bg_col = colors.HexColor("#F0FDF4")
                border_col = colors.HexColor("#10B981")
                text_col = "#065F46"

            header_style_custom = ParagraphStyle("HSC", parent=body_bold_style, textColor=colors.HexColor(text_col))
            badge_style_custom = ParagraphStyle("BSC", parent=body_style, textColor=colors.HexColor(text_col), alignment=2)

            header_table = Table([
                [Paragraph(header_text, header_style_custom), Paragraph(badge_text, badge_style_custom)]
            ], colWidths=[304, 200])
            
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_col),
                ('BOX', (0, 0), (-1, -1), 1, border_col),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            clause_lbl = Paragraph("<b>Extracted Policy Text:</b>", body_style)
            clause_box = Table([[Paragraph(issue.clause_text or "No text", box_text_style)]], colWidths=[504])
            clause_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))

            violate_lbl = Paragraph("<b>Statutory Mandate & Violation Analysis:</b>", body_style)
            desc_text = issue.description or (rule.requirement_text if rule else "Statutory conflict detected.")
            desc_text = re.sub(r'\s*\(\s*Caught by:[^)]*\)', '', desc_text, flags=re.IGNORECASE).strip()
            desc_text = re.sub(r'\s*\(\s*Semantic similarity:[^)]*\)', '', desc_text, flags=re.IGNORECASE).strip()
            desc_box = Table([[Paragraph(desc_text, box_text_style)]], colWidths=[504])
            desc_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))

            fix_flowables = []
            if rule and rule.template_fix:
                fix_lbl = Paragraph("<b>✓ Compliant Template Replacement:</b>", body_style)
                fix_box = Table([[Paragraph(rule.template_fix, fix_text_style)]], colWidths=[504])
                fix_box.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#68D391")),
                    ('PADDING', (0, 0), (-1, -1), 10),
                ]))
                fix_flowables = [Spacer(1, 4), fix_lbl, fix_box]

            issue_group = KeepTogether([
                header_table,
                Spacer(1, 6),
                clause_lbl,
                clause_box,
                Spacer(1, 6),
                violate_lbl,
                desc_box,
                *fix_flowables,
                Spacer(1, 20),
            ])
            story.append(issue_group)

    # ──────────────────────────────────────────────────────────────────────────
    # LAST PAGE: DISCLAIMER & METADATA
    # ──────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Audit Conclusion & Legal Notice", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F2227"), spaceAfter=16))

    disclaimer_text = (
        "<b>IMPORTANT LEGAL DISCLAIMER:</b><br/><br/>"
        "This report is generated by an automated AI compliance software tool (THEMIS) and does <b>not</b> constitute "
        "formal legal advice. THEMIS relies on natural language inference models and semantic vector embeddings to compare "
        "workplace standing orders against central Indian employment codes (including the Labour Codes 2020, POSH Act 2013, "
        "and DPDP Act 2023).<br/><br/>"
        "While stringent quality checks and algorithmic deferral rules are maintained, statutory interpretation involves nuanced "
        "factual evaluation and jurisdiction-specific rule modifications by relevant State labor authorities. This automated assessment "
        "is intended strictly for internal management review, risk scoping, and pre-audit preparation. It must not be viewed as a substitute "
        "for definitive legal representation or formal clearance by an advocate enrolled with the Bar Council of India."
    )
    disc_box = Table([[Paragraph(disclaimer_text, box_text_style)]], colWidths=[504])
    disc_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#A33F3F")),
        ('PADDING', (0, 0), (-1, -1), 16),
    ]))
    story.append(disc_box)
    story.append(Spacer(1, 30))

    meta_text = (
        f"<b>Audit Telemetry Metadata:</b><br/>"
        f"• <b>Engine Version:</b> THEMIS Core 2.0 (Dual-Model NLI Pipeline)<br/>"
        f"• <b>Report Identifier:</b> THMS-AUDIT-{report.id}<br/>"
        f"• <b>Total Processing Duration:</b> {report.scan_duration_seconds:.2f}s<br/>"
        f"• <b>Ledger Timestamp:</b> {scan_date_str}"
    )
    meta_box = Table([[Paragraph(meta_text, body_style)]], colWidths=[504])
    meta_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(meta_box)

    # Attach report ID to canvas during build
    def setup_canvas(canv, doc_obj):
        canv._report_id = str(report.id)

    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=setup_canvas, onLaterPages=setup_canvas)
    return buffer.getvalue()
