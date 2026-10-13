"""Builds paper/paper.docx in the ICCISD two-column IEEE conference format from
paper/paper.md and paper/figures/. Layout values were measured from the
conference template PDF: A4, Times New Roman 10 pt, two columns 245.8 pt wide
with a 15.4 pt gap, small-caps centred section headings with Roman numerals,
italic lettered subheadings, a 9 pt bold abstract, bordered tables with centred
upper-case captions, 10 pt references, and the conference header and copyright
footer on the first page only.

Run: python paper/make_figures.py && python paper/build_paper_docx.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT = "Times New Roman"
ESC = "\u0001"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

CONFERENCE = "2026 International Conference on Computational Intelligence Systems and Devices (ICCISD)"
COPYRIGHT = "979-8-3315-6371-4/26/$31.00 ©2026 IEEE"
AUTHORS = [  # (name, email); department and institute are the same for everyone
    ("Prof. Dr. Premanand P. Ghadekar", "premanand.ghadekar@vit.edu"),
    ("Divyanshu Gajbhiye", "divyanshu.gajbhiye24@vit.edu"),
    ("Vidhi Hadoltikar", "vidhi.hadoltikar24@vit.edu"),
    ("Harshvardhan Rawat", "harshvardhan.rawat24@vit.edu"),
    ("Nirmit Hatti", "nirmit.hatti24@vit.edu"),
]
DEPT, INSTITUTE, CITY = "CSE (AI&ML)", "Vishwakarma Institute of Technology", "Pune, India"

# ---------------------------------------------------------------- page setup
doc = Document()
sec1 = doc.sections[0]
sec1.page_width, sec1.page_height = Pt(595.22), Pt(842)
for s in (sec1,):
    s.left_margin, s.right_margin = Pt(45.4), Pt(42.7)
    s.top_margin, s.bottom_margin = Pt(54), Pt(36)
    s.header_distance, s.footer_distance = Pt(28), Pt(24)
    s.different_first_page_header_footer = True


def fix_fonts(style):
    style.font.name = FONT
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for att in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(att), FONT)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(att)) is not None:
            del rf.attrib[qn(att)]
    style.font.color.rgb = RGBColor(0, 0, 0)


normal = doc.styles["Normal"]
fix_fonts(normal)
normal.font.size = Pt(10)
pf = normal.paragraph_format
pf.space_before = pf.space_after = Pt(0)
pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
for nm in ("Title", "Heading 1", "Heading 2"):
    st = doc.styles[nm]
    fix_fonts(st)
    st.font.bold = False
    st.font.italic = False
    st.font.size = Pt(10)
    st.paragraph_format.keep_with_next = True
    st.element.get_or_add_pPr()
# Title style often carries a bottom border; remove it
for pbdr in doc.styles["Title"].element.xpath(".//w:pBdr"):
    pbdr.getparent().remove(pbdr)


def runs(par, text, size=None, bold=None, italic=None, ital=False):
    """Bold is **text**. Italics (*text*) are parsed only when ital=True (the reference
    list), so that A*, AO* and LAO* in running text are left alone."""
    text = text.replace("\\*", ESC)
    pattern = r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*)" if ital else r"(\*\*.+?\*\*)"
    for tok in re.split(pattern, text):
        if not tok:
            continue
        b = tok.startswith("**") and tok.endswith("**") and len(tok) > 4
        it = ital and (not b) and tok.startswith("*") and tok.endswith("*") and len(tok) > 2
        body = tok[2:-2] if b else tok[1:-1] if it else tok
        r = par.add_run(body.replace(ESC, "*"))
        r.font.name = FONT
        if size:
            r.font.size = Pt(size)
        if b or bold:
            r.bold = True
        if it or italic:
            r.italic = True


def para(text="", align=None, indent=False, size=None, bold=None, italic=None, before=0, after=0, keep_next=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if indent:
        p.paragraph_format.first_line_indent = Pt(14.4)
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(before), Pt(after)
    p.paragraph_format.keep_with_next = keep_next
    if text:
        runs(p, text, size=size, bold=bold, italic=italic)
    return p


def tiny(par):
    """Collapse an empty header or footer paragraph to almost nothing."""
    par.paragraph_format.space_before = par.paragraph_format.space_after = Pt(0)
    par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    par.paragraph_format.line_spacing = Pt(1)
    r = par.add_run("")
    r.font.size = Pt(1)


# headers and footers: the conference line and the copyright line appear on page 1 only
fh = sec1.first_page_header.paragraphs[0]
fh.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fh.add_run(CONFERENCE)
r.font.name, r.font.size = FONT, Pt(8)
ff = sec1.first_page_footer.paragraphs[0]
ff.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = ff.add_run(COPYRIGHT)
r.font.name, r.font.size = FONT, Pt(8)
tiny(sec1.header.paragraphs[0])
tiny(sec1.footer.paragraphs[0])

# ----------------------------------------------------------- title and authors
lines = (HERE / "paper.md").read_text(encoding="utf-8").splitlines()
title = next(l[2:] for l in lines if l.startswith("# "))
tp = para(align=WD_ALIGN_PARAGRAPH.CENTER, before=10, after=12)
r = tp.add_run(title)
r.bold, r.font.size, r.font.name = True, Pt(24), FONT

tbl = doc.add_table(rows=2, cols=6)  # six narrow columns so that two authors can sit centred under three
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl.autofit = False
for row in tbl.rows:
    for c in row.cells:
        c.width = Pt(84)
spans = [((0, 0), (0, 1)), ((0, 2), (0, 3)), ((0, 4), (0, 5)), ((1, 1), (1, 2)), ((1, 3), (1, 4))]
for (name, email), (start, end) in zip(AUTHORS, spans):
    cell = tbl.cell(*start).merge(tbl.cell(*end))
    first = cell.paragraphs[0]
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = first.add_run(name)
    c.font.size, c.font.name = Pt(9), FONT
    for t in (DEPT, INSTITUTE, CITY, email):
        q = cell.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        q.paragraph_format.space_before = q.paragraph_format.space_after = Pt(0)
        rr = q.add_run(t)
        rr.font.size, rr.font.name = Pt(9), FONT
    for pp in cell.paragraphs:
        pp.paragraph_format.space_after = Pt(0)
tbl.rows[0].height = Pt(66)  # space between the two author rows
doc.add_paragraph().paragraph_format.space_after = Pt(4)

# ------------------------------------------------------------ two-column body
sec2 = doc.add_section(WD_SECTION.CONTINUOUS)
for s in (sec2,):
    s.left_margin, s.right_margin = Pt(45.4), Pt(42.7)
    s.top_margin, s.bottom_margin = Pt(54), Pt(36)
    s.header_distance, s.footer_distance = Pt(28), Pt(24)
    s.different_first_page_header_footer = False
sec2.header.is_linked_to_previous = True
sec2.footer.is_linked_to_previous = True
cols = sec2._sectPr.xpath("./w:cols")
col = cols[0] if cols else OxmlElement("w:cols")
col.set(qn("w:num"), "2")
col.set(qn("w:space"), "308")  # 15.4 pt in twentieths of a point
if not cols:
    sec2._sectPr.append(col)


def shade_border(cell, borders=True):
    tcPr = cell._tc.get_or_add_tcPr()
    if borders:
        tb = OxmlElement("w:tcBorders")
        for edge in ("top", "left", "bottom", "right"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            e.set(qn("w:color"), "000000")
            tb.append(e)
        tcPr.append(tb)


def add_table(rows):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    n = len(rows[0])
    weight = [max(10, max(len(r[j].strip()) for r in rows)) for j in range(n)]
    tblPr = t._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge in ("left", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), "60")
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)
    TOTAL = 232  # points; the column is 245.8 wide, so the table stays inside it
    widths = [Pt(TOTAL * w / sum(weight)) for w in weight]
    for j, w in enumerate(widths):
        t.columns[j].width = w  # the grid, so Word does not stretch the table
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(TOTAL * 20)))
    tw.set(qn("w:type"), "dxa")
    tblPr.append(tw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.width = widths[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(1.5)
            rr = p.add_run(val.strip())
            rr.font.size, rr.font.name = Pt(8 if len(rows[0]) <= 4 else 7), FONT
            if j:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rr.bold = True if i == 0 else None
            shade_border(cell)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(6)
    return t


def search_rows():
    S = json.loads((ROOT / "results" / "search_methods.json").read_text(encoding="utf-8"))["games"]
    algs = [("BFS", "BFS"), ("DFS", "DFS"), ("weighted A*", "A*"), ("meet in the middle", "MITM")]
    short = {"Peg Solitaire, 22 jumps out": "Peg, 22 jumps", "24-puzzle, 20 move scramble": "24-puzzle, 20",
             "24-puzzle, 40 move scramble": "24-puzzle, 40", "Rubik's cube, 5 move scramble": "Cube, 5 moves",
             "Rubik's cube, 6 move scramble": "Cube, 6 moves", "Boxoban (20 levels)": "Boxoban", "Peg Solitaire": "Peg, real start"}
    rows = [["Game"] + [b for _, b in algs]]
    for g, v in S.items():
        cells = []
        for a, _ in algs:
            c = v.get(a)
            cells.append("n/a" if c is None else "0" if c["nodes"] is None else f"{c['solved'] * 100:.0f} / " + (f"{c['nodes'] / 1000:.1f}k" if c["nodes"] >= 10000 else f"{c['nodes']:,.0f}"))
        rows.append([short.get(g, g)] + cells)
    return rows


def equation(text, number):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(4)
    p.paragraph_format.tab_stops.add_tab_stop(Pt(122.9), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Pt(245.8), WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run("\t" + text)
    r.italic, r.font.name, r.font.size = True, FONT, Pt(10)
    r2 = p.add_run("\t" + number)
    r2.font.name, r2.font.size = FONT, Pt(10)



# ------------------------------------------------------------ native Word canvas
from docx.oxml import parse_xml

EMU = 12700
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
      'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')
_ids = iter(range(200, 400))


def _xml_esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _para(text, size, bold=False, vert=False):
    b = "<w:b/>" if bold else ""
    return (f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>{b}<w:sz w:val="{size}"/></w:rPr>'
            f'<w:t xml:space="preserve">{_xml_esc(text)}</w:t></w:r></w:p>')


def _box(x, y, w, h, title, desc, fill, line_w):
    i = next(_ids)
    body = _para(title, 17, bold=True) + (_para(desc, 14) if desc else "")
    return (f'<wps:wsp><wps:cNvPr id="{i}" name="Stage {i}"/><wps:cNvSpPr/><wps:spPr>'
            f'<a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
            f'<a:ln w="{int(line_w*EMU)}"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln></wps:spPr>'
            f'<wps:txbx><w:txbxContent>{body}</w:txbxContent></wps:txbx>'
            f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="36000" tIns="18000" rIns="36000" bIns="18000" anchor="ctr" anchorCtr="0"><a:noAutofit/></wps:bodyPr></wps:wsp>')


def _label(x, y, w, h, text):
    i = next(_ids)
    return (f'<wps:wsp><wps:cNvPr id="{i}" name="Label {i}"/><wps:cNvSpPr txBox="1"/><wps:spPr>'
            f'<a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
            f'<wps:txbx><w:txbxContent>{_para(text, 13)}</w:txbxContent></wps:txbx>'
            f'<wps:bodyPr rot="0" vert="vert270" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"><a:noAutofit/></wps:bodyPr></wps:wsp>')


def _line(x0, y0, x1, y1, arrow=False):
    i = next(_ids)
    fl = (' flipH="1"' if x1 < x0 else "") + (' flipV="1"' if y1 < y0 else "")
    tail = '<a:tailEnd type="triangle" w="med" len="med"/>' if arrow else ""
    return (f'<wps:wsp><wps:cNvPr id="{i}" name="Arrow {i}"/><wps:cNvCnPr/><wps:spPr>'
            f'<a:xfrm{fl}><a:off x="{int(min(x0,x1)*EMU)}" y="{int(min(y0,y1)*EMU)}"/>'
            f'<a:ext cx="{int(abs(x1-x0)*EMU)}" cy="{int(abs(y1-y0)*EMU)}"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="9525"><a:solidFill><a:srgbClr val="000000"/></a:solidFill>{tail}</a:ln></wps:spPr><wps:bodyPr/></wps:wsp>')


def pipeline_canvas():
    """Fig. 1 as real Word shapes on a drawing canvas. Box heights follow the amount of text
    and box widths follow its importance, so the sizes differ."""
    stages = [  # title, description, width, ours
        ("Environment", "state, legal moves, goal test", 150, False),
        ("Propose", "candidate plans from the current state", 190, False),
        ("Merge", "replay every plan and join equal states into one directed graph", 214, False),
        ("Check", "a per-game validator rejects or discounts moves; the experience store scales confidence by past failures", 226, True),
        ("Choose", "price each move, then run A* if one piece moves and CP-SAT if several do", 226, True),
        ("Run", "execute the path; on a mismatch, record the failure and replan from the real state", 178, False),
    ]
    W, cx, gap = 242, 108, 15
    y, boxes = 0, []
    for title, desc, w, ours in stages:
        lines = -(-len(desc) * 3.15 // (w - 8))
        h = 6 + 10 + lines * 8.6
        boxes.append((cx - w / 2, y, w, h, title, desc, ours))
        y += h + gap
    H = y - gap
    shapes = []
    for k, (x, yy, w, h, t, d, ours) in enumerate(boxes):
        shapes.append(_box(x, yy, w, h, t, d, "D9D9D9" if ours else "FFFFFF", 1.5 if ours else 0.75))
        if k:
            px, py, pw, ph = boxes[k - 1][:4]
            shapes.append(_line(cx, py + ph, cx, yy, arrow=True))
    lx = 236
    run, prop = boxes[-1], boxes[1]
    ym_run, ym_prop = run[1] + run[3] / 2, prop[1] + prop[3] / 2
    shapes.append(_line(run[0] + run[2], ym_run, lx, ym_run))
    shapes.append(_line(lx, ym_run, lx, ym_prop))
    shapes.append(_line(lx, ym_prop, prop[0] + prop[2], ym_prop, arrow=True))
    shapes.append(_label(lx - 12, (ym_run + ym_prop) / 2 - 22, 10, 44, "replan"))
    xml = (f'<w:drawing {NS}><wp:inline distT="0" distB="0" distL="0" distR="0">'
           f'<wp:extent cx="{int(W*EMU)}" cy="{int(H*EMU)}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
           f'<wp:docPr id="199" name="Pipeline canvas"/><wp:cNvGraphicFramePr/>'
           f'<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas">'
           f'<wpc:wpc><wpc:bg><a:noFill/></wpc:bg><wpc:whole><a:ln><a:noFill/></a:ln></wpc:whole>'
           + "".join(shapes) + '</wpc:wpc></a:graphicData></a:graphic></wp:inline></w:drawing>')
    return parse_xml(xml)


sec_no, sub_no, fig_no, tab_no = 0, 0, 0, 0
in_refs, i = False, 0
body = lines[lines.index(next(l for l in lines if l.startswith("## Abstract"))):]
while i < len(body):
    ln = body[i]
    if not ln.strip():
        i += 1
        continue
    if ln.startswith("## "):
        head = ln[3:].strip()
        if head == "Abstract":
            i += 1
            while i < len(body) and not body[i].strip():
                i += 1
            p = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, size=9, before=2, after=6)
            r = p.add_run("Abstract—")
            r.bold, r.italic, r.font.size, r.font.name = True, True, Pt(9), FONT
            r = p.add_run(body[i].strip())
            r.bold, r.font.size, r.font.name = True, Pt(9), FONT
            i += 1
            continue
        in_refs = head == "References"
        if in_refs:
            p = para(align=WD_ALIGN_PARAGRAPH.CENTER, before=12, after=6, keep_next=True)
            r = p.add_run("References")
            r.font.small_caps, r.font.size, r.font.name = True, Pt(10), FONT
        else:
            sec_no += 1
            sub_no = 0
            p = para(align=WD_ALIGN_PARAGRAPH.CENTER, before=12, after=6, keep_next=True)
            a = p.add_run(f"{ROMAN[sec_no - 1]}. ")
            a.font.size, a.font.name = Pt(10), FONT
            b = p.add_run(head)
            b.font.small_caps, b.font.size, b.font.name = True, Pt(10), FONT
        i += 1
        continue
    if ln.startswith("### "):
        sub_no += 1
        p = para(align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=4, keep_next=True)
        r = p.add_run(f"{chr(64 + sub_no)}. {ln[4:].strip()}")
        r.italic, r.font.size, r.font.name = True, Pt(10), FONT
        i += 1
        continue
    if ln.startswith("Keywords:"):
        p = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, size=9, before=2, after=6)
        r = p.add_run("Index Terms—")
        r.bold = r.italic = True
        r.font.size, r.font.name = Pt(9), FONT
        r = p.add_run(ln[len("Keywords:"):].strip())
        r.bold = r.italic = True
        r.font.size, r.font.name = Pt(9), FONT
        i += 1
        continue
    if ln.startswith("EQ: "):
        text, number = ln[4:].split(" | ")
        equation(text, number)
        i += 1
        continue
    if ln.startswith("TABLE: "):
        tab_no += 1
        cap = para(align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=0, keep_next=True)
        r = cap.add_run(f"TABLE {ROMAN[tab_no - 1]}")
        r.font.size, r.font.name, r.font.small_caps = Pt(8), FONT, True
        t2 = para(align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=4, keep_next=True)
        r = t2.add_run(ln[7:].strip().upper())
        r.font.size, r.font.name, r.font.small_caps = Pt(8), FONT, True
        i += 1
        if body[i].strip() == "@search_table":
            add_table(search_rows())
            i += 1
        else:
            rows = []
            while i < len(body) and body[i].startswith("|"):
                if not re.fullmatch(r"\|[\s\-|:]+\|", body[i].strip()):
                    rows.append(body[i].strip().strip("|").split("|"))
                i += 1
            add_table(rows)
        continue
    if ln.startswith("!["):
        fig_no += 1
        m = re.match(r"!\[(.*)\]\((.*)\)", ln)
        pic = doc.add_paragraph()
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.paragraph_format.space_before = Pt(4)
        pic.paragraph_format.keep_with_next = True
        if m.group(2) == "canvas:pipeline":
            pic.add_run()._r.append(pipeline_canvas())
        else:
            pic.add_run().add_picture(str(HERE / m.group(2)), width=Pt(240))
        cap_txt = m.group(1).strip()
        c = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY if len(cap_txt) > 60 else WD_ALIGN_PARAGRAPH.CENTER, before=2, after=8)
        r = c.add_run(cap_txt)
        r.font.size, r.font.name = Pt(8), FONT
        i += 1
        continue
    if ln.startswith("> "):
        i += 1  # builder note, not part of the paper
        continue
    if in_refs and ln.startswith("["):
        p = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Pt(20), Pt(-20)
        p.paragraph_format.tab_stops.add_tab_stop(Pt(20))
        runs(p, re.sub(r"^(\[\d+\]) ", lambda m: m.group(1) + "	", ln), size=8, ital=True)
    else:
        p = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True)
        runs(p, ln)
    i += 1

out = HERE / "paper.docx"
doc.save(out)
print("wrote", out)
