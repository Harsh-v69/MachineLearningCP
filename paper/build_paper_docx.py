"""Builds paper/paper.docx (editable Word version) from paper/paper.md, with the
figures in paper/figures/. Run paper/make_figures.py first.

Run: python paper/build_paper_docx.py
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FONT = "Times New Roman"
ESC = "\u0001"  # stands in for an escaped asterisk while inline markup is parsed

doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(1)

for name, size, bold in (("Normal", 11, False), ("Heading 1", 14, True), ("Heading 2", 12, True), ("Title", 18, True)):
    st = doc.styles[name]
    st.font.name, st.font.size, st.font.bold = FONT, Pt(size), bold
    st.font.color.rgb = RGBColor(0x10, 0x20, 0x1F) if name != "Normal" else RGBColor(0, 0, 0)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
doc.styles["Normal"].paragraph_format.space_after = Pt(6)
doc.styles["Normal"].paragraph_format.line_spacing = 1.08
for h in ("Heading 1", "Heading 2"):
    doc.styles[h].paragraph_format.space_before = Pt(12)
    doc.styles[h].paragraph_format.space_after = Pt(4)
    doc.styles[h].paragraph_format.keep_with_next = True


def runs(par, text, size=None, italic=False):
    text = text.replace("\\*", ESC)
    for tok in re.split(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)", text):
        if not tok:
            continue
        bold = tok.startswith("**") and tok.endswith("**") and len(tok) > 4
        code = tok.startswith("`") and tok.endswith("`") and len(tok) > 2
        ital = (not bold and not code and tok.startswith("*") and tok.endswith("*") and len(tok) > 2)
        body = tok[2:-2] if bold else tok[1:-1] if (code or ital) else tok
        r = par.add_run(body.replace(ESC, "*"))
        r.bold = bold or None
        r.italic = (ital or italic) or None
        if code:
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        elif size:
            r.font.size = Pt(size)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def add_table(rows):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            runs(par, val.strip(), size=8.5)
            if i == 0:
                for r in par.runs:
                    r.bold = True
                shade(cell, "DCE8EA")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_number_footer():
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        r._r.append(el)


lines = (HERE / "paper.md").read_text(encoding="utf-8").splitlines()
i, in_refs, in_code = 0, False, False
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        in_code = not in_code
        i += 1
        continue
    if in_code:
        par = doc.add_paragraph()
        r = par.add_run(ln)
        r.font.name, r.font.size = "Consolas", Pt(8.5)
        par.paragraph_format.space_after = Pt(0)
        i += 1
        continue
    if not ln.strip() or ln.strip() == "---":
        i += 1
        continue
    if ln.startswith("# "):
        par = doc.add_paragraph(style="Title")
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run(ln[2:])
    elif ln.startswith("## "):
        in_refs = ln[3:].strip() == "References"
        doc.add_heading(ln[3:], level=1)
    elif ln.startswith("### "):
        doc.add_heading(ln[4:], level=2)
    elif ln.startswith("> "):
        par = doc.add_paragraph()
        par.paragraph_format.left_indent = Inches(.3)
        par.paragraph_format.right_indent = Inches(.3)
        runs(par, ln[2:], size=9.5, italic=True)
    elif ln.startswith("|"):
        block = []
        while i < len(lines) and lines[i].startswith("|"):
            block.append(lines[i])
            i += 1
        rows = [[c for c in b.strip().strip("|").split("|")] for b in block if not re.fullmatch(r"\|[\s\-|:]+\|", b.strip())]
        add_table(rows)
        continue
    elif ln.startswith("!["):
        m = re.match(r"!\[(.*)\]\((.*)\)", ln)
        cap, path = m.group(1), HERE / m.group(2)
        pic = doc.add_paragraph()
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.paragraph_format.keep_with_next = True
        pic.add_run().add_picture(str(path), width=Inches(6.2))
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runs(c, cap, size=9.5, italic=True)
    elif re.match(r"- ", ln):
        par = doc.add_paragraph(style="List Bullet")
        runs(par, ln[2:])
    elif re.match(r"\d+\. ", ln):
        par = doc.add_paragraph(style="List Number")
        runs(par, re.sub(r"^\d+\.\s", "", ln))
    elif ln.startswith("**Authors:**") or ln.startswith("**Guide:**") or ln.startswith("**Course:**"):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(0)
        runs(par, ln)
    else:
        par = doc.add_paragraph()
        if in_refs and ln.startswith("["):
            par.paragraph_format.left_indent = Inches(.35)
            par.paragraph_format.first_line_indent = Inches(-.35)
            runs(par, ln, size=9.5)
        else:
            runs(par, ln)
    i += 1

page_number_footer()
out = HERE / "paper.docx"
doc.save(out)
print("wrote", out)
