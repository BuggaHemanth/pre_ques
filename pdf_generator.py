"""
PDF Generation for AI Maturity Assessment Reports
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime


def generate_assessment_pdf(results: dict, scraping: dict, mcq_answers: dict = None) -> BytesIO:
    """
    Generate comprehensive PDF report for AI maturity assessment

    Args:
        results: Analysis results dict
        scraping: Scraping results dict
        mcq_answers: User's MCQ responses

    Returns:
        BytesIO object containing PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#202A44'),  # Navy blue
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#202A44'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )

    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#202A44'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )

    # Header with logo (if available)
    try:
        logo = Image('https://databeat.io/wp-content/uploads/2025/05/DataBeat-Mediamint-Logo-1-1.png', width=2*inch, height=0.5*inch)
        elements.append(logo)
        elements.append(Spacer(1, 0.3*inch))
    except:
        pass  # Skip logo if not available

    # Title
    company_name = scraping.get('company_name', 'Company')
    elements.append(Paragraph(f"AI Maturity Assessment Report", title_style))
    elements.append(Paragraph(f"{company_name}", heading_style))
    elements.append(Spacer(1, 0.2*inch))

    # Metadata
    metadata_text = f"""
    <b>Assessment Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
    <b>Website Analyzed:</b> {scraping.get('base_url', 'N/A')}<br/>
    <b>Pages Analyzed:</b> {scraping.get('page_count', 0)}<br/>
    """
    elements.append(Paragraph(metadata_text, body_style))
    elements.append(Spacer(1, 0.3*inch))

    # Overall Score Section
    elements.append(Paragraph("Overall Assessment", heading_style))

    score_data = [
        ['Metric', 'Score'],
        ['Overall AI Maturity Score', f"{results.get('overall_score', 0)}/100"],
        ['Maturity Level', results.get('maturity_tag', 'N/A')],
    ]

    if 'base_score' in results:
        score_data.append(['Website Analysis Score', f"{results.get('base_score', 0)}/100"])
    if 'mcq_score' in results:
        score_data.append(['Questionnaire Score', f"{results.get('mcq_score', 0)}/100"])

    score_table = Table(score_data, colWidths=[3.5*inch, 2*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#202A44')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(score_table)
    elements.append(Spacer(1, 0.3*inch))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    summary = results.get('summary', 'No summary available.')
    elements.append(Paragraph(summary, body_style))
    elements.append(Spacer(1, 0.2*inch))

    # Dimensional Breakdown - list format instead of table
    elements.append(Paragraph("Dimensional Analysis", heading_style))

    dimensional_scores = results.get('dimensional_scores', {})
    if dimensional_scores:
        for dimension, score in dimensional_scores.items():
            elements.append(Paragraph(f"• {dimension}: {score}/100", body_style))
        elements.append(Spacer(1, 0.2*inch))

    # Key Findings
    elements.append(Paragraph("Key Findings", heading_style))

    key_findings = results.get('key_findings', [])
    if key_findings:
        for finding in key_findings:
            elements.append(Paragraph(f"• {finding}", body_style))
    else:
        elements.append(Paragraph("No key findings available.", body_style))

    elements.append(Spacer(1, 0.2*inch))

    # Evidence Section
    evidence = results.get('evidence', {})

    if evidence.get('strengths'):
        elements.append(Paragraph("Strengths", subheading_style))
        for strength in evidence['strengths']:
            elements.append(Paragraph(f"✓ {strength}", body_style))
        elements.append(Spacer(1, 0.15*inch))

    if evidence.get('gaps'):
        elements.append(Paragraph("Areas for Improvement", subheading_style))
        for gap in evidence['gaps']:
            elements.append(Paragraph(f"• {gap}", body_style))
        elements.append(Spacer(1, 0.15*inch))

    if evidence.get('opportunities'):
        elements.append(Paragraph("Opportunities", subheading_style))
        for opp in evidence['opportunities']:
            elements.append(Paragraph(f"→ {opp}", body_style))
        elements.append(Spacer(1, 0.2*inch))

    # Links Analyzed Section
    elements.append(PageBreak())
    elements.append(Paragraph("Links Analyzed", heading_style))

    # Website pages
    sources = results.get('sources', {})
    scraped_pages = sources.get('scraped_pages', [])
    if scraped_pages:
        elements.append(Paragraph("Website Pages Analyzed:", subheading_style))
        for i, page in enumerate(scraped_pages[:10], 1):
            page_url = page.get('url', 'N/A')
            page_text = f'{i}. <link href="{page_url}" color="blue">{page.get("title", "Page")}</link>'
            elements.append(Paragraph(page_text, body_style))
        elements.append(Spacer(1, 0.15*inch))

    # External sources
    external_sources = sources.get('external_sources', [])
    if external_sources:
        elements.append(Paragraph("External Research Sources:", subheading_style))
        for i, source in enumerate(external_sources[:10], 1):
            source_url = source.get('url', 'N/A')
            source_text = f'{i}. <link href="{source_url}" color="blue">{source.get("title", "Source")}</link>'
            elements.append(Paragraph(source_text, body_style))

    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = f"""
    <para alignment="center">
    <i>This report was generated by DataBeat AI Maturity Assessment Tool<br/>
    {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i>
    </para>
    """
    elements.append(Paragraph(footer_text, body_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    return buffer
