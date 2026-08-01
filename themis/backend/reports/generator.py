import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from compliance.models import ScanReport


def generate_compliance_pdf(report_id: int) -> bytes:
    """Generate a PDF report and return as bytes."""
    report = ScanReport.objects.get(pk=report_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=40
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2b6cb0'),
        spaceAfter=12
    )
    normal_style = styles['Normal']
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        alignment=TA_CENTER
    )

    story = []

    # --- Page 1: Cover Page ---
    story.append(Paragraph("⚖️ THEMIS", title_style))
    story.append(Paragraph("Compliance Assessment Report", subtitle_style))
    
    story.append(Spacer(1, 40))
    
    # Policy details
    cover_data = [
        ['Policy Title:', report.policy.title],
        ['Scan Date:', report.scanned_at.strftime('%Y-%m-%d %H:%M')],
        ['Scanned By:', report.scanned_by.username],
    ]
    t = Table(cover_data, colWidths=[120, 300])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(t)
    
    story.append(Spacer(1, 60))
    
    # Overall score
    score_color = colors.green if report.overall_score >= 70 else (colors.orange if report.overall_score >= 40 else colors.red)
    score_text = f"<font color='{score_color.hexval()}'><b>{report.overall_score:.1f}/100</b></font>"
    story.append(Paragraph(f"Overall Compliance Score: {score_text}", ParagraphStyle('Score', parent=styles['Heading2'], alignment=TA_CENTER, fontSize=18)))
    story.append(Paragraph(f"Risk Level: <b>{report.risk_level.upper()}</b>", ParagraphStyle('Risk', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14)))
    
    story.append(PageBreak())

    # --- Page 2: Executive Summary ---
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(f"Total Clauses Analyzed: {report.total_clauses}", normal_style))
    story.append(Paragraph(f"Compliant Clauses: {report.compliant_clauses}", normal_style))
    story.append(Paragraph(f"Flagged Clauses: {report.flagged_clauses}", normal_style))
    story.append(Spacer(1, 20))

    # Model comparison
    story.append(Paragraph("AI Semantic Analysis Models", heading_style))
    model_data = [
        ['Model', 'Average Similarity Score'],
        ['MiniLM (General)', f"{report.miniml_avg_score:.2f}"],
        ['InLegal-SBERT (Legal Domain)', f"{report.inlegal_avg_score:.2f}"],
    ]
    t_model = Table(model_data, colWidths=[200, 150])
    t_model.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t_model)
    
    story.append(PageBreak())

    # --- Page 3+: Flagged Issues ---
    story.append(Paragraph("Flagged Issues", heading_style))
    
    issues = report.flagged_issues.all().order_by('-severity_score')
    if not issues:
        story.append(Paragraph("No compliance issues found. The policy appears fully compliant based on the scanned rules.", normal_style))
    else:
        for idx, issue in enumerate(issues, 1):
            story.append(Paragraph(f"Issue #{idx} — {issue.legal_rule.law_name}", ParagraphStyle('IssueTitle', parent=styles['Heading3'], textColor=colors.HexColor('#c53030'))))
            
            issue_data = [
                ['Status', issue.status.upper()],
                ['Severity Score', f"{issue.severity_score}/100"],
                ['Law & Section', f"{issue.legal_rule.law_name} - {issue.legal_rule.section}"],
            ]
            t_issue = Table(issue_data, colWidths=[100, 350])
            t_issue.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t_issue)
            story.append(Spacer(1, 10))
            
            story.append(Paragraph("<b>Flagged Clause:</b>", normal_style))
            story.append(Paragraph(issue.clause_text, ParagraphStyle('Clause', parent=styles['Normal'], backColor=colors.HexColor('#fff5f5'), borderPadding=10)))
            story.append(Spacer(1, 10))
            
            story.append(Paragraph("<b>Description:</b>", normal_style))
            story.append(Paragraph(issue.description, normal_style))
            story.append(Spacer(1, 10))
            
            if issue.legal_rule.template_fix:
                story.append(Paragraph("<b>Suggested Template Fix:</b>", normal_style))
                story.append(Paragraph(issue.legal_rule.template_fix, ParagraphStyle('Fix', parent=styles['Normal'], backColor=colors.HexColor('#f0fff4'), borderPadding=10, fontName='Courier')))
            
            story.append(Spacer(1, 20))

    story.append(PageBreak())

    # --- Last Page: Disclaimer ---
    story.append(Spacer(1, 200))
    story.append(Paragraph("DISCLAIMER", ParagraphStyle('DiscTitle', parent=styles['Heading3'], alignment=TA_CENTER)))
    story.append(Paragraph("This report is generated by an automated tool (THEMIS) using AI semantic analysis and rule-based keyword matching. It is intended for initial screening purposes only and does not constitute formal legal advice. Please consult with qualified legal counsel before making final decisions or updating corporate policies.", disclaimer_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Scan duration: {report.scan_duration_seconds:.2f}s", disclaimer_style))

    # Build the PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
