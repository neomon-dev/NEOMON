"""NEOMON Finals Preparation Guide — PDF Generator
Generates NEOMON_Finals_Preparation_Guide.pdf from all 10 markdown files using ReportLab.
Features:
- Professional Dark Navy & Cyan Cyberpunk Scientific Palette
- A4 Format with NumberedCanvas ("Page X of Y")
- Running Headers and Running Footers
- Table of Contents
- Properly wrapped tables with header row styling
- Styled Code & ASCII Diagram Blocks
- Callout Boxes for Pitches and Quotes
"""

import os
import re
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# Page dimensions: A4 is 595.27 x 841.89 points
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 50
MARGIN_RIGHT = 50
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN_LEFT + MARGIN_RIGHT) # ~495 pt

# Branding Palette
C_NAVY = colors.HexColor("#050914")
C_SLATE = colors.HexColor("#0C192B")
C_CYAN = colors.HexColor("#25D9F2")
C_BLUE = colors.HexColor("#2787FF")
C_DARK_TEXT = colors.HexColor("#1A202C")
C_MUTED = colors.HexColor("#64748B")
C_BORDER = colors.HexColor("#CBD5E1")
C_BG_CODE = colors.HexColor("#0F172A")
C_BG_ROW_ALT = colors.HexColor("#F8FAFC")
C_BG_ROW_HIGHLIGHT = colors.HexColor("#F1F5F9")
C_BG_CALLOUT = colors.HexColor("#F0F9FF")
C_BORDER_CALLOUT = colors.HexColor("#0284C7")

DOC_FILES = [
    ("Chapter 1: Project Overview & Strategic Narrative", "PROJECT_OVERVIEW.md"),
    ("Chapter 2: Subsystem Technical Architecture", "TECHNICAL_ARCHITECTURE.md"),
    ("Chapter 3: Comprehensive Functionality Deep Dive", "FUNCTIONALITY_DEEP_DIVE.md"),
    ("Chapter 4: End-to-End Technical Data Flow", "END_TO_END_DATA_FLOW.md"),
    ("Chapter 5: Technical Limitations, Vulnerabilities & Risks", "LIMITATIONS_AND_RISKS.md"),
    ("Chapter 6: Strategic Future Engineering Roadmap", "FUTURE_ROADMAP.md"),
    ("Chapter 7: Finals Presentation Scripts & Live Demo Guide", "FINALS_PRESENTATION_SCRIPT.md"),
    ("Chapter 8: Comprehensive Judges' Q&A Defense Manual", "JUDGES_QA_PREPARATION.md"),
    ("Chapter 9: Last-Minute Finals Revision Sheet", "LAST_MINUTE_REVISION_SHEET.md"),
    ("Chapter 10: Implementation Status Classification Matrix", "IMPLEMENTATION_STATUS_MATRIX.md"),
]


class NumberedCanvas(canvas.Canvas):
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

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Draw premium dark cover header/footer accent
            self.saveState()
            self.setFillColor(C_NAVY)
            self.rect(0, PAGE_HEIGHT - 12, PAGE_WIDTH, 12, fill=True, stroke=False)
            self.setFillColor(C_CYAN)
            self.rect(0, PAGE_HEIGHT - 16, PAGE_WIDTH, 4, fill=True, stroke=False)
            self.setFillColor(C_NAVY)
            self.rect(0, 0, PAGE_WIDTH, 12, fill=True, stroke=False)
            self.restoreState()
            return

        self.saveState()
        # Running Header
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(C_MUTED)
        self.drawString(MARGIN_LEFT, PAGE_HEIGHT - 32, "NEOMON — Final Round Project Understanding & Technical Defense Guide")
        self.setFont("Helvetica", 7.5)
        self.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 32, "Finals Evaluation Copy")
        self.setStrokeColor(C_BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN_LEFT, PAGE_HEIGHT - 36, PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 36)

        # Running Footer
        self.line(MARGIN_LEFT, 40, PAGE_WIDTH - MARGIN_RIGHT, 40)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(C_MUTED)
        self.drawString(MARGIN_LEFT, 28, "Confidential — Competition Finals Defense | Autonomous Research System")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 28, page_str)
        self.restoreState()


def clean_md_inline(text):
    """Converts markdown bold, italic, and code spans into safe ReportLab HTML tags."""
    text = html.escape(text)
    # Convert bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert italic
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Convert code
    text = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0369A1">\1</font>', text)
    return text


def build_pdf():
    output_pdf = os.path.join(os.getcwd(), "NEOMON_Finals_Preparation_Guide.pdf")
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_cover_tag = ParagraphStyle(
        'CoverTag',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=C_BLUE,
        spaceAfter=10,
    )
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=34,
        leading=40,
        textColor=C_NAVY,
        spaceAfter=6,
    )
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F766E"),
        spaceAfter=18,
    )
    style_cover_desc = ParagraphStyle(
        'CoverDesc',
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=C_MUTED,
        spaceAfter=24,
    )

    style_chap_title = ParagraphStyle(
        'ChapTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=C_NAVY,
        spaceBefore=16,
        spaceAfter=10,
        keepWithNext=True,
    )
    style_h2 = ParagraphStyle(
        'Heading2',
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=C_NAVY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )
    style_h3 = ParagraphStyle(
        'Heading3',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=C_BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    style_h4 = ParagraphStyle(
        'Heading4',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=C_SLATE,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )
    style_body = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_DARK_TEXT,
        spaceBefore=2,
        spaceAfter=3,
    )
    style_bullet = ParagraphStyle(
        'Bullet',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_DARK_TEXT,
        leftIndent=15,
        firstLineIndent=-10,
        spaceBefore=1,
        spaceAfter=2,
    )
    style_callout = ParagraphStyle(
        'Callout',
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0C4A6E"),
        spaceBefore=0,
        spaceAfter=0,
    )
    style_code = ParagraphStyle(
        'CodeBlock',
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#E2E8F0"),
        spaceBefore=0,
        spaceAfter=0,
    )
    style_th = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=0,
    )
    style_td = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=C_DARK_TEXT,
        alignment=0,
    )

    story = []

    # ================= 1. COVER PAGE =================
    story.append(Spacer(1, 40))
    story.append(Paragraph("COMPETITION FINALS — TECHNICAL DEFENSE & SYSTEM BLUEPRINT", style_cover_tag))
    story.append(Paragraph("NEOMON", style_cover_title))
    story.append(Paragraph("Neural Evidence Orchestration & Multi-Agent Observation Network", style_cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=C_CYAN, spaceBefore=0, spaceAfter=18))

    story.append(Paragraph(
        "A comprehensive architectural evaluation, technical specification, dialectical multi-agent reference, "
        "reproducibility audit, and finals defense manual prepared for the competition judging panel.",
        style_cover_desc
    ))

    # Metadata Card Table
    meta_data = [
        [Paragraph("<b>Evaluation Target:</b>", style_td), Paragraph("Final Round Technical Presentation & Architecture Defense", style_td)],
        [Paragraph("<b>System Core:</b>", style_td), Paragraph("Next.js 16 (App Router) + FastAPI AsyncIO + SQLAlchemy 2.0 (WAL / Postgres)", style_td)],
        [Paragraph("<b>Verification Stats:</b>", style_td), Paragraph("235 Automated Backend Tests Passed | 15 UI Tests Passed | 0 ESLint / TS Errors", style_td)],
        [Paragraph("<b>Architecture:</b>", style_td), Paragraph("Adversarial Specialist Triad (Advocate vs Skeptic vs Auditor) + 18-Section Report Engine", style_td)],
        [Paragraph("<b>Author / Team:</b>", style_td), Paragraph("NEOMON Core Research & Engineering Team", style_td)],
        [Paragraph("<b>Release Version:</b>", style_td), Paragraph("NEOMON 1.0 (Audit-Ready Finalist Build)", style_td)],
    ]
    meta_table = Table(meta_data, colWidths=[130, CONTENT_WIDTH - 130])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 30))
    # Executive Abstract Callout
    abstract_text = (
        "<b>Executive Architectural Declaration:</b> NEOMON resolves the fundamental crisis of automated research synthesis—namely, "
        "that general-purpose LLMs hallucinate citations, exhibit topical confirmation bias, and conflate paper introductory aspirations "
        "with empirical findings. By combining atomic claim decomposition, multi-source academic retrieval (Crossref, OpenAlex, arXiv, Unpaywall), "
        "SSRF-guarded verbatim passage extraction, an adversarial multi-agent debate triad, and cryptographic SHA-256 reproducibility manifests, "
        "NEOMON delivers audit-ready scientific intelligence in minutes instead of months."
    )
    abs_cell = [[Paragraph(abstract_text, style_body)]]
    abs_table = Table(abs_cell, colWidths=[CONTENT_WIDTH])
    abs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_BG_CALLOUT),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER_CALLOUT),
        ('LINELEFT', (0, 0), (-1, -1), 3.0, C_BORDER_CALLOUT),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(abs_table)

    story.append(PageBreak())

    # ================= 2. TABLE OF CONTENTS =================
    story.append(Paragraph("TABLE OF CONTENTS", style_chap_title))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceBefore=2, spaceAfter=12))

    toc_rows = []
    for idx, (chap_title, filename) in enumerate(DOC_FILES):
        r_num = f"<b>Chapter {idx + 1}</b>"
        r_title = clean_md_inline(chap_title.split(": ", 1)[-1])
        r_sec = f"Section {idx + 1}.0"
        toc_rows.append([
            Paragraph(r_num, style_td),
            Paragraph(f"<b>{r_title}</b>", style_td),
            Paragraph(r_sec, style_td),
        ])

    toc_table = Table(toc_rows, colWidths=[65, CONTENT_WIDTH - 145, 80])
    toc_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, C_BG_ROW_ALT]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ================= 3. CHAPTERS PROCESSING =================
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for chap_num, (chap_title, filename) in enumerate(DOC_FILES, start=1):
        file_path = os.path.join(base_dir, filename)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Chapter Banner
        story.append(Paragraph(f"CHAPTER {chap_num}", style_cover_tag))
        story.append(Paragraph(chap_title.split(": ", 1)[-1].upper(), style_chap_title))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE, spaceBefore=2, spaceAfter=12))

        lines = content.split("\n")
        in_code_block = False
        code_lines = []
        in_table = False
        table_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block
            if line.strip().startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_text = html.escape("\n".join(code_lines))
                    p_code = Paragraph(code_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), style_code)
                    code_box = Table([[p_code]], colWidths=[CONTENT_WIDTH])
                    code_box.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), C_BG_CODE),
                        ('BOX', (0, 0), (-1, -1), 0.5, C_SLATE),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(code_box)
                    story.append(Spacer(1, 4))
                    code_lines = []
                else:
                    in_code_block = True
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Markdown Table
            if line.strip().startswith("|") and line.strip().endswith("|"):
                table_lines.append(line)
                in_table = True
                i += 1
                continue
            elif in_table:
                in_table = False
                # Parse markdown table
                if len(table_lines) >= 2:
                    rows_data = []
                    for tline in table_lines:
                        if re.match(r'^\s*\|(?:\s*:?-+:?\s*\|)+\s*$', tline):
                            continue
                        cells = [c.strip() for c in tline.strip().strip('|').split('|')]
                        rows_data.append(cells)

                    if rows_data:
                        num_cols = max(len(r) for r in rows_data)
                        col_width = CONTENT_WIDTH / num_cols
                        # Custom column widths if 2 cols or 5 cols
                        if num_cols == 2:
                            col_widths = [120, CONTENT_WIDTH - 120]
                        elif num_cols == 3:
                            col_widths = [110, 160, CONTENT_WIDTH - 270]
                        elif num_cols == 5:
                            col_widths = [100, 110, 80, 100, CONTENT_WIDTH - 390]
                        else:
                            col_widths = [col_width] * num_cols

                        table_flow_data = []
                        for r_idx, row in enumerate(rows_data):
                            is_header = (r_idx == 0)
                            row_cells = []
                            for c_idx in range(num_cols):
                                cell_val = clean_md_inline(row[c_idx] if c_idx < len(row) else "")
                                p_style = style_th if is_header else style_td
                                row_cells.append(Paragraph(cell_val, p_style))
                            table_flow_data.append(row_cells)

                        tbl = Table(table_flow_data, colWidths=col_widths)
                        tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), C_SLATE),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_ROW_ALT]),
                            ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
                            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ('LEFTPADDING', (0, 0), (-1, -1), 6),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ]))
                        story.append(tbl)
                        story.append(Spacer(1, 4))
                table_lines = []

            # Headers
            if line.startswith("# "):
                i += 1
                continue
            elif line.startswith("## "):
                story.append(Paragraph(clean_md_inline(line[3:].strip()), style_h2))
            elif line.startswith("### "):
                story.append(Paragraph(clean_md_inline(line[4:].strip()), style_h3))
            elif line.startswith("#### "):
                story.append(Paragraph(clean_md_inline(line[5:].strip()), style_h4))
            elif line.strip().startswith(">"):
                quote_text = clean_md_inline(line.strip()[1:].strip())
                q_p = Paragraph(quote_text, style_callout)
                q_table = Table([[q_p]], colWidths=[CONTENT_WIDTH])
                q_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), C_BG_CALLOUT),
                    ('LINELEFT', (0, 0), (-1, -1), 2.5, C_BORDER_CALLOUT),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(q_table)
                story.append(Spacer(1, 3))
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                bullet_text = clean_md_inline(line.strip()[2:])
                story.append(Paragraph(f"&bull; {bullet_text}", style_bullet))
            elif re.match(r'^\d+\.\s', line.strip()):
                num_text = clean_md_inline(line.strip())
                story.append(Paragraph(num_text, style_bullet))
            elif line.strip().startswith("---"):
                story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceBefore=4, spaceAfter=4))
            elif line.strip():
                story.append(Paragraph(clean_md_inline(line.strip()), style_body))

            i += 1

        if chap_num < len(DOC_FILES):
            story.append(PageBreak())

    # Build the document with our NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {output_pdf} ({os.path.getsize(output_pdf)} bytes)")


if __name__ == "__main__":
    build_pdf()
