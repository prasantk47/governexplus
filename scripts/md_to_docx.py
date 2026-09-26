#!/usr/bin/env python3
"""Convert all GovernexPlus markdown docs to Word .docx files."""

import re
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

DOCS_DIR = Path(__file__).parent.parent / "docs"
OUTPUT_DIR = DOCS_DIR / "word"

# Files to convert (numbered docs only)
MD_FILES = sorted(DOCS_DIR.glob("[0-9]*.md"))


def parse_md_line(line: str):
    """Classify a markdown line."""
    stripped = line.rstrip()
    if stripped.startswith("# "):
        return "h1", stripped[2:]
    if stripped.startswith("## "):
        return "h2", stripped[3:]
    if stripped.startswith("### "):
        return "h3", stripped[4:]
    if stripped.startswith("#### "):
        return "h4", stripped[5:]
    if stripped.startswith("##### "):
        return "h5", stripped[6:]
    if stripped.startswith("---"):
        return "hr", ""
    if stripped.startswith("|") and "|" in stripped[1:]:
        return "table_row", stripped
    if stripped.startswith("```"):
        return "code_fence", stripped[3:]
    if stripped.startswith("- ") or stripped.startswith("* "):
        return "bullet", stripped[2:]
    if re.match(r"^\d+\.\s", stripped):
        m = re.match(r"^\d+\.\s(.*)", stripped)
        return "numbered", m.group(1) if m else stripped
    if stripped.startswith("> "):
        return "quote", stripped[2:]
    if stripped == "":
        return "blank", ""
    return "para", stripped


def add_formatted_text(paragraph, text: str):
    """Add text with basic inline markdown formatting (bold, italic, code)."""
    # Process **bold**, *italic*, `code`
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`[^`]+`)', text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*") and not part.startswith("**"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
        else:
            # Strip markdown links [text](url) to just text
            cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', part)
            paragraph.add_run(cleaned)


def convert_md_to_docx(md_path: Path, output_path: Path):
    """Convert a single markdown file to Word docx."""
    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    # Configure heading styles
    for level in range(1, 6):
        h_style = doc.styles[f"Heading {level}"]
        h_style.font.color.rgb = RGBColor(0x0C, 0x2D, 0x6B)
        h_style.font.name = "Calibri"
        if level == 1:
            h_style.font.size = Pt(24)
        elif level == 2:
            h_style.font.size = Pt(18)
        elif level == 3:
            h_style.font.size = Pt(14)
        elif level == 4:
            h_style.font.size = Pt(12)

    lines = md_path.read_text(encoding="utf-8").split("\n")
    in_code_block = False
    code_lines = []
    table_rows = []
    i = 0

    while i < len(lines):
        kind, content = parse_md_line(lines[i])

        # Handle code blocks
        if kind == "code_fence":
            if in_code_block:
                # End code block — flush
                p = doc.add_paragraph()
                p.style = doc.styles["Normal"]
                p.paragraph_format.left_indent = Inches(0.3)
                for cl in code_lines:
                    run = p.add_run(cl + "\n")
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(lines[i].rstrip())
            i += 1
            continue

        # Handle tables
        if kind == "table_row":
            cells = [c.strip() for c in content.split("|")[1:-1]]
            if cells and all(set(c) <= {"-", ":", " "} for c in cells):
                # Separator row — skip
                i += 1
                continue
            table_rows.append(cells)
            # Check if next line is still a table
            if i + 1 < len(lines):
                next_kind, _ = parse_md_line(lines[i + 1])
                if next_kind != "table_row":
                    # Flush table
                    if table_rows:
                        num_cols = max(len(r) for r in table_rows)
                        tbl = doc.add_table(rows=len(table_rows), cols=num_cols)
                        tbl.style = "Light Grid Accent 1"
                        tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
                        for ri, row_data in enumerate(table_rows):
                            for ci, cell_val in enumerate(row_data):
                                if ci < num_cols:
                                    cell = tbl.cell(ri, ci)
                                    cell.text = ""
                                    p = cell.paragraphs[0]
                                    add_formatted_text(p, cell_val)
                                    p.style.font.size = Pt(10)
                                    if ri == 0:
                                        for run in p.runs:
                                            run.bold = True
                        doc.add_paragraph()  # Space after table
                    table_rows = []
            i += 1
            continue

        # Flush any remaining table rows
        if table_rows:
            num_cols = max(len(r) for r in table_rows)
            tbl = doc.add_table(rows=len(table_rows), cols=num_cols)
            tbl.style = "Light Grid Accent 1"
            for ri, row_data in enumerate(table_rows):
                for ci, cell_val in enumerate(row_data):
                    if ci < num_cols:
                        tbl.cell(ri, ci).text = cell_val
            doc.add_paragraph()
            table_rows = []

        if kind == "h1":
            p = doc.add_heading(content, level=1)
        elif kind == "h2":
            doc.add_heading(content, level=2)
        elif kind == "h3":
            doc.add_heading(content, level=3)
        elif kind == "h4":
            doc.add_heading(content, level=4)
        elif kind == "h5":
            doc.add_heading(content, level=4)
        elif kind == "hr":
            p = doc.add_paragraph()
            p.add_run("_" * 60)
            p.runs[0].font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        elif kind == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            add_formatted_text(p, content)
        elif kind == "numbered":
            p = doc.add_paragraph(style="List Number")
            add_formatted_text(p, content)
        elif kind == "quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            run = p.add_run(content)
            run.italic = True
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        elif kind == "blank":
            pass  # Skip blank lines
        elif kind == "para":
            p = doc.add_paragraph()
            add_formatted_text(p, content)

        i += 1

    # Add footer with page numbers
    section = doc.sections[0]
    section.page_height = Inches(11)
    section.page_width = Inches(8.5)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1)

    doc.save(str(output_path))
    return output_path


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not MD_FILES:
        print("No numbered markdown files found in docs/")
        sys.exit(1)

    print(f"Converting {len(MD_FILES)} documents to Word...\n")

    for md_file in MD_FILES:
        docx_name = md_file.stem + ".docx"
        output_path = OUTPUT_DIR / docx_name
        try:
            convert_md_to_docx(md_file, output_path)
            size_kb = output_path.stat().st_size / 1024
            print(f"  OK  {docx_name} ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"  FAIL  {docx_name}: {e}")

    print(f"\nAll documents saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
