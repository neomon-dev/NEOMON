"""NEOMON Finals Preparation Guide — DOCX Generator
Reads all 10 markdown documents in docs/finals-preparation/ and creates NEOMON_Finals_Preparation_Guide.docx
"""

import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

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

COLOR_NAVY = RGBColor(5, 9, 20)        # #050914
COLOR_CYAN = RGBColor(37, 217, 242)    # #25D9F2
COLOR_BLUE = RGBColor(39, 135, 255)    # #2787FF
COLOR_SLATE = RGBColor(12, 25, 43)     # #0C192B
COLOR_MUTED = RGBColor(100, 116, 139)  # #64748B
COLOR_DARK = RGBColor(26, 32, 44)      # #1A202C

HEX_NAVY = "050914"
HEX_SLATE = "0C192B"
HEX_CYAN = "25D9F2"
HEX_LIGHT_ROW = "F8FAFC"
HEX_ALT_ROW = "F1F5F9"
HEX_BORDER = "CBD5E1"
HEX_CALLOUT_BG = "F0F9FF"
HEX_CALLOUT_BORDER = "0284C7"


def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def add_formatted_text(p, text):
    """Parses bold, italic, code, and links within a paragraph."""
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            run = p.add_run(token[2:-2])
            run.bold = True
            run.font.color.rgb = COLOR_DARK
        elif token.startswith('*') and token.endswith('*'):
            run = p.add_run(token[1:-1])
            run.italic = True
            run.font.color.rgb = COLOR_DARK
        elif token.startswith('`') and token.endswith('`'):
            run = p.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(3, 105, 161)
        else:
            run = p.add_run(token)
            run.font.color.rgb = COLOR_DARK


def build_docx():
    doc = Document()

    # Configure Margins: 0.75 in (54 pt)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        section.different_first_page_header_footer = True

        # Header / Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.text = "NEOMON — Final Round Project Understanding & Technical Defense Guide"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if hp.runs:
            hp.runs[0].font.size = Pt(8)
            hp.runs[0].font.color.rgb = COLOR_MUTED

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.text = "Confidential — Competition Finals Defense | NEOMON Autonomous Research System"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if fp.runs:
            fp.runs[0].font.size = Pt(8)
            fp.runs[0].font.color.rgb = COLOR_MUTED

    # ================= COVER PAGE =================
    cover_p = doc.add_paragraph()
    cover_p.paragraph_format.space_before = Pt(60)
    cover_p.paragraph_format.space_after = Pt(10)
    tag_run = cover_p.add_run("COMPETITION FINALS — TECHNICAL DEFENSE GUIDE & SYSTEM BLUEPRINT")
    tag_run.font.name = "Arial"
    tag_run.font.size = Pt(10)
    tag_run.bold = True
    tag_run.font.color.rgb = COLOR_BLUE

    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(6)
    title_run = title_p.add_run("NEOMON")
    title_run.font.name = "Arial"
    title_run.font.size = Pt(36)
    title_run.bold = True
    title_run.font.color.rgb = COLOR_NAVY

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(24)
    sub_run = subtitle_p.add_run("Neural Evidence Orchestration & Multi-Agent Observation Network")
    sub_run.font.name = "Arial"
    sub_run.font.size = Pt(15)
    sub_run.font.color.rgb = RGBColor(15, 118, 110)

    desc_p = doc.add_paragraph()
    desc_p.paragraph_format.space_after = Pt(36)
    desc_run = desc_p.add_run(
        "A comprehensive architectural evaluation, technical explanation, dialetical multi-agent specification, "
        "reproducibility reference, and defense manual prepared for the competition judging panel."
    )
    desc_run.font.size = Pt(11)
    desc_run.font.color.rgb = COLOR_MUTED

    # Metadata Box
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Document Type:", "Final Round Technical Presentation & Architecture Defense Guide"),
        ("System Architecture:", "Next.js 16 + FastAPI + SQLAlchemy 2.0 (WAL / Postgres) + Multi-Agent Triad"),
        ("Verification Metrics:", "235 Automated Backend Tests Passed | 15 Frontend Suites Passed | 0 ESLint / TS Errors"),
        ("Target Evaluation:", "Competition Finals Technical Judging Panel & Architecture Defense"),
    ]
    for idx, (lbl, val) in enumerate(meta_rows):
        r = meta_table.rows[idx]
        set_cell_background(r.cells[0], "F1F5F9")
        set_cell_background(r.cells[1], "FFFFFF")
        set_cell_margins(r.cells[0], 80, 80, 120, 120)
        set_cell_margins(r.cells[1], 80, 80, 120, 120)

        p0 = r.cells[0].paragraphs[0]
        p0_run = p0.add_run(lbl)
        p0_run.bold = True
        p0_run.font.size = Pt(9.5)
        p0_run.font.color.rgb = COLOR_NAVY

        p1 = r.cells[1].paragraphs[0]
        p1_run = p1.add_run(val)
        p1_run.font.size = Pt(9.5)
        p1_run.font.color.rgb = COLOR_DARK

    doc.add_page_break()

    # ================= TABLE OF CONTENTS =================
    toc_title = doc.add_paragraph()
    toc_title.paragraph_format.space_before = Pt(12)
    toc_title.paragraph_format.space_after = Pt(16)
    t_run = toc_title.add_run("TABLE OF CONTENTS")
    t_run.font.name = "Arial"
    t_run.font.size = Pt(18)
    t_run.bold = True
    t_run.font.color.rgb = COLOR_NAVY

    toc_table = doc.add_table(rows=len(DOC_FILES), cols=2)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (chap_title, filename) in enumerate(DOC_FILES):
        r = toc_table.rows[idx]
        bg = HEX_LIGHT_ROW if idx % 2 == 0 else "FFFFFF"
        set_cell_background(r.cells[0], bg)
        set_cell_background(r.cells[1], bg)
        set_cell_margins(r.cells[0], 60, 60, 100, 100)
        set_cell_margins(r.cells[1], 60, 60, 100, 100)

        p0 = r.cells[0].paragraphs[0]
        p0_run = p0.add_run(chap_title)
        p0_run.font.size = Pt(10)
        p0_run.bold = True
        p0_run.font.color.rgb = COLOR_NAVY

        p1 = r.cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p1_run = p1.add_run(f"Section {idx + 1}")
        p1_run.font.size = Pt(9.5)
        p1_run.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # ================= CHAPTERS PROCESSING =================
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for chap_num, (chap_title, filename) in enumerate(DOC_FILES, start=1):
        file_path = os.path.join(base_dir, filename)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Add Chapter Heading
        c_p = doc.add_paragraph()
        c_p.paragraph_format.space_before = Pt(18)
        c_p.paragraph_format.space_after = Pt(12)
        c_run = c_p.add_run(chap_title)
        c_run.font.name = "Arial"
        c_run.font.size = Pt(18)
        c_run.bold = True
        c_run.font.color.rgb = COLOR_NAVY

        # Process markdown lines
        lines = content.split("\n")
        in_code_block = False
        code_lines = []
        table_lines = []
        in_table = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block toggle
            if line.strip().startswith("```"):
                if in_code_block:
                    in_code_block = False
                    # Render code block
                    block_text = "\n".join(code_lines)
                    table = doc.add_table(rows=1, cols=1)
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    cell = table.rows[0].cells[0]
                    set_cell_background(cell, "0F172A")
                    set_cell_margins(cell, 100, 100, 150, 150)
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_before = Pt(0)
                    cp.paragraph_format.space_after = Pt(0)
                    c_run = cp.add_run(block_text)
                    c_run.font.name = "Consolas"
                    c_run.font.size = Pt(8.5)
                    c_run.font.color.rgb = RGBColor(226, 232, 240)
                    code_lines = []
                    # Spacer
                    sp = doc.add_paragraph()
                    sp.paragraph_format.space_before = Pt(0)
                    sp.paragraph_format.space_after = Pt(6)
                else:
                    in_code_block = True
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Markdown Table detection
            if line.strip().startswith("|") and line.strip().endswith("|"):
                table_lines.append(line)
                in_table = True
                i += 1
                continue
            elif in_table:
                in_table = False
                # Parse and render table
                if len(table_lines) >= 2:
                    rows_data = []
                    for tline in table_lines:
                        # Skip delimiter line (|---|---|)
                        if re.match(r'^\s*\|(?:\s*:?-+:?\s*\|)+\s*$', tline):
                            continue
                        cells = [c.strip() for c in tline.strip().strip('|').split('|')]
                        rows_data.append(cells)

                    if rows_data:
                        num_cols = max(len(r) for r in rows_data)
                        doc_table = doc.add_table(rows=len(rows_data), cols=num_cols)
                        doc_table.alignment = WD_TABLE_ALIGNMENT.CENTER

                        for r_idx, row in enumerate(rows_data):
                            is_header = (r_idx == 0)
                            bg_color = HEX_SLATE if is_header else (HEX_LIGHT_ROW if r_idx % 2 == 1 else "FFFFFF")
                            for c_idx in range(num_cols):
                                cell_val = row[c_idx] if c_idx < len(row) else ""
                                cell = doc_table.rows[r_idx].cells[c_idx]
                                set_cell_background(cell, bg_color)
                                set_cell_margins(cell, 80, 80, 100, 100)
                                cp = cell.paragraphs[0]
                                cp.paragraph_format.space_before = Pt(0)
                                cp.paragraph_format.space_after = Pt(0)
                                if is_header:
                                    hr = cp.add_run(cell_val)
                                    hr.bold = True
                                    hr.font.size = Pt(8.5)
                                    hr.font.color.rgb = RGBColor(255, 255, 255)
                                else:
                                    add_formatted_text(cp, cell_val)
                                    if cp.runs:
                                        for r_item in cp.runs:
                                            r_item.font.size = Pt(8.5)

                        sp = doc.add_paragraph()
                        sp.paragraph_format.space_before = Pt(0)
                        sp.paragraph_format.space_after = Pt(6)
                table_lines = []
                # Fall through to process current line

            # Headings
            if line.startswith("# "):
                # Skip duplicate main title
                i += 1
                continue
            elif line.startswith("## "):
                h2 = doc.add_paragraph()
                h2.paragraph_format.space_before = Pt(14)
                h2.paragraph_format.space_after = Pt(6)
                h2.paragraph_format.keep_with_next = True
                h2_run = h2.add_run(line[3:].strip())
                h2_run.font.name = "Arial"
                h2_run.font.size = Pt(13)
                h2_run.bold = True
                h2_run.font.color.rgb = COLOR_NAVY
            elif line.startswith("### "):
                h3 = doc.add_paragraph()
                h3.paragraph_format.space_before = Pt(10)
                h3.paragraph_format.space_after = Pt(4)
                h3.paragraph_format.keep_with_next = True
                h3_run = h3.add_run(line[4:].strip())
                h3_run.font.name = "Arial"
                h3_run.font.size = Pt(11)
                h3_run.bold = True
                h3_run.font.color.rgb = COLOR_BLUE
            elif line.startswith("#### "):
                h4 = doc.add_paragraph()
                h4.paragraph_format.space_before = Pt(8)
                h4.paragraph_format.space_after = Pt(3)
                h4.paragraph_format.keep_with_next = True
                h4_run = h4.add_run(line[5:].strip())
                h4_run.font.name = "Arial"
                h4_run.font.size = Pt(10)
                h4_run.bold = True
                h4_run.font.color.rgb = COLOR_SLATE
            elif line.strip().startswith(">"):
                # Blockquote / Callout
                callout_text = line.strip()[1:].strip()
                tbl = doc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = tbl.rows[0].cells[0]
                set_cell_background(cell, HEX_CALLOUT_BG)
                set_cell_margins(cell, 80, 80, 140, 140)
                # Left border cyan
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = parse_xml(
                    f'<w:tcBorders {nsdecls("w")}>'
                    f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/>'
                    f'<w:top w:val="none"/>'
                    f'<w:right w:val="none"/>'
                    f'<w:bottom w:val="none"/>'
                    f'</w:tcBorders>'
                )
                tcPr.append(tcBorders)
                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                add_formatted_text(cp, callout_text)
                for r_item in cp.runs:
                    r_item.font.size = Pt(9.5)
                    r_item.italic = True
                    r_item.font.color.rgb = RGBColor(12, 74, 110)
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = Pt(0)
                sp.paragraph_format.space_after = Pt(4)
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                add_formatted_text(p, line.strip()[2:])
            elif re.match(r'^\d+\.\s', line.strip()):
                bullet_text = re.sub(r'^\d+\.\s', '', line.strip())
                p = doc.add_paragraph(style='List Number')
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                add_formatted_text(p, bullet_text)
            elif line.strip().startswith("---"):
                # Divider line
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
            elif line.strip():
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(4)
                add_formatted_text(p, line)
                if p.runs:
                    for r_item in p.runs:
                        r_item.font.size = Pt(9.5)

            i += 1

        # Page break between chapters (except last)
        if chap_num < len(DOC_FILES):
            doc.add_page_break()

    output_path = os.path.join(os.getcwd(), "NEOMON_Finals_Preparation_Guide.docx")
    doc.save(output_path)
    print(f"Successfully generated DOCX: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    build_docx()
