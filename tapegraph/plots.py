"""Dependency-free SVG charts (stdlib only): line_chart, bar_chart, scatter.

Every function returns a self-contained, deterministic SVG string (no ids from counters of the clock, no randomness).
Colour is never the only cue: each series also gets its own marker shape and dash pattern (bars: a fill pattern).

Series are dicts:  {"name": str, "x": [...], "y": [...], "lo": [...] | None, "hi": [...] | None,
                    "kind": "line" | "points" | "ref" | "fail", "labels": [...] | None}
  - "line"   (default of line_chart): line + markers, broken at None/NaN points
  - "points" (default of scatter): markers only
  - "ref"    thin dashed reference line (e.g. y = x), no markers
  - "fail"   failure markers (colour of the data series named by its optional "owner"): hollow crosses in a strip above the plot area (one strip row per fail series), at the x
             of each entry (y is ignored); optional `labels` (e.g. counts) are printed beside the crosses
  - lo/hi    confidence limits per point; drawn as a band (`ci="band"`) or whiskers (`ci="bars"`)
Bar chart series: {"name", "y": [per category], "lo", "hi"}; None/NaN values draw no bar.
"""
from __future__ import annotations

from math import ceil, floor, isfinite, log10
from xml.sax.saxutils import escape

PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#999999"]  # Okabe-Ito
DASHES = ["", "7 3", "2 3", "8 3 2 3", "12 4", "4 2 1 2"]
MARKERS = ["circle", "square", "triangle", "diamond", "triangle_down", "hexagon"]
INK, GRID, MUTED, BG = "#222222", "#dddddd", "#666666", "#ffffff"
FONT = "font-family=\"Helvetica, Arial, sans-serif\""


def _t(s):
    return escape(str(s), {'"': "&quot;"})


def _n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _ok(v):
    try:
        return v is not None and isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _fmt_tick(v, log=False):
    if log:
        e = round(log10(v))
        return f"{10.0 ** e:.6g}" if -4 <= e <= 4 else f"1e{e}"
    return f"{v:.6g}"


def _nice_ticks(lo, hi, target=6):
    """Ticks at 'nice' numbers (1, 2, 5 x 10^k) covering [lo, hi]; returns (ticks, domain_lo, domain_hi)."""
    if hi <= lo:
        lo, hi = lo - 1, hi + 1
    raw = (hi - lo) / max(1, target - 1)
    mag = 10 ** floor(log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    a, b = floor(lo / step + 1e-9), ceil(hi / step - 1e-9)
    return [round(i * step, 10) for i in range(a, b + 1)], round(a * step, 10), round(b * step, 10)


def _log_ticks(lo, hi):
    a, b = floor(log10(lo) + 1e-9), ceil(log10(hi) - 1e-9)
    if a == b:
        b = a + 1
    return [10.0 ** e for e in range(a, b + 1)], 10.0 ** a, 10.0 ** b


def _axis(vals, log, lim):
    """(ticks, lo, hi) for the data values `vals` (finite; positive if log) or a user limit."""
    if lim is not None:
        lo, hi = lim
    elif vals:
        lo, hi = min(vals), max(vals)
    else:
        lo, hi = (1.0, 10.0) if log else (0.0, 1.0)
    if log:
        ticks, tlo, thi = _log_ticks(lo, hi)
        return ticks, tlo, thi
    ticks, tlo, thi = _nice_ticks(lo, hi)
    if lim is not None:  # an explicit limit is kept exactly; only ticks inside it are shown
        return [t for t in ticks if lim[0] - 1e-9 <= t <= lim[1] + 1e-9], lim[0], lim[1]
    return ticks, tlo, thi


def _marker(shape, x, y, color, cls="pt", r=4.0):
    f = f'class="{cls}" fill="{color}" stroke="{BG}" stroke-width="1"'
    if shape == "circle":
        return f'<circle {f} cx="{_n(x)}" cy="{_n(y)}" r="{_n(r)}"/>'
    if shape == "square":
        return f'<rect {f} x="{_n(x - r)}" y="{_n(y - r)}" width="{_n(2 * r)}" height="{_n(2 * r)}"/>'
    pts = {"triangle": [(0, -1.2), (1.1, 0.9), (-1.1, 0.9)], "triangle_down": [(0, 1.2), (1.1, -0.9), (-1.1, -0.9)],
           "diamond": [(0, -1.3), (1.3, 0), (0, 1.3), (-1.3, 0)],
           "hexagon": [(1, 0), (0.5, 0.87), (-0.5, 0.87), (-1, 0), (-0.5, -0.87), (0.5, -0.87)]}[shape]
    return f'<polygon {f} points="{" ".join(_n(x + r * a) + "," + _n(y + r * b) for a, b in pts)}"/>'


def _cross(x, y, color, r=4.5):
    d = f"M{_n(x - r)},{_n(y - r)}L{_n(x + r)},{_n(y + r)}M{_n(x - r)},{_n(y + r)}L{_n(x + r)},{_n(y - r)}"
    return f'<path class="fail" d="{d}" fill="none" stroke="{color}" stroke-width="2"/>'


def _svg(w, h, title, desc, body, defs=""):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" '
            f'style="max-width:100%;height:auto" role="img" {FONT}>\n'
            f"<title>{_t(title)}</title>\n<desc>{_t(desc)}</desc>\n"
            + (f"<defs>{defs}</defs>\n" if defs else "")
            + f'<rect class="bg" x="0" y="0" width="{w}" height="{h}" fill="{BG}"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def _text(x, y, s, size=11, anchor="start", cls="", color=INK, extra=""):
    c = f' class="{cls}"' if cls else ""
    return f'<text{c} x="{_n(x)}" y="{_n(y)}" font-size="{size}" text-anchor="{anchor}" fill="{color}"{extra}>{_t(s)}</text>'


def _title(title, w):
    """Title text, wrapped greedily at ~78 characters into at most two centred lines."""
    lines, cur = [], ""
    for word in str(title).split():
        if cur and len(cur) + 1 + len(word) > 78 and len(lines) == 0:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    lines.append(cur)
    return [_text(w / 2, 20 + 16 * i, ln, 13, "middle", "title") for i, ln in enumerate(lines)]


def _empty(title, w, h, msg="no data"):
    body = _title(title, w) + [_text(w / 2, h / 2, msg, 14, "middle", "nodata", MUTED)]
    return _svg(w, h, title, f"{title}: {msg}", body)


def _runs(pts):
    """Split [(x, y, ...)] at invalid points into runs of valid ones."""
    run, out = [], []
    for p in pts:
        if p is None:
            if run:
                out.append(run)
            run = []
        else:
            run.append(p)
    if run:
        out.append(run)
    return out


def _legend(entries, x, y):
    """entries: [(name, swatch svg builder taking (x0, y0))]; returns svg lines."""
    out = []
    for i, (name, sw) in enumerate(entries):
        yy = y + 18 * i
        out += [sw(x, yy), _text(x + 34, yy + 4, name, 11, cls="legend")]
    return out


def _layout(w, h, series, legend_names, strips):
    longest = max([len(n) for n in legend_names] + [len(s["name"]) + 2 for s in strips] + [0])
    right = 16 + (longest * 6.4 + 40 if longest else 0)
    left, top, bottom = 66, 48 + 18 * len(strips) + (6 if strips else 0), 54
    return left, top, w - right, h - bottom


def _xy(kind, series, title, xlabel, ylabel, xlog, ylog, xlim, ylim, ci, width, height, desc):
    series = [{**s, "kind": s.get("kind", "line" if kind == "line" else "points")} for s in series]

    def xs_ok(x):
        return _ok(x) and (not xlog or float(x) > 0)

    def ys_ok(y):
        return _ok(y) and (not ylog or float(y) > 0)

    data = [s for s in series if s["kind"] in ("line", "points", "ref")]
    fails = [s for s in series if s["kind"] == "fail"]
    xv, yv = [], []
    for s in data:
        for i, (x, y) in enumerate(zip(s["x"], s["y"])):
            if xs_ok(x) and ys_ok(y):
                xv.append(float(x))
                yv.append(float(y))
                for k in ("lo", "hi"):
                    if s.get(k) is not None and ys_ok(s[k][i]):
                        yv.append(float(s[k][i]))
    for s in fails:
        xv += [float(x) for x in s["x"] if xs_ok(x)]
    if not xv:  # nothing to place; failure markers alone still get a frame (y axis falls back to a default range)
        return _empty(title, width, height)
    xt, x0, x1 = _axis(xv, xlog, xlim)
    yt, y0, y1 = _axis(yv, ylog, ylim)
    left, top, right, bottom = _layout(width, height, series, [s["name"] for s in data if s.get("name")], fails)

    def sc(v, lo, hi, log):
        if log:
            v = max(v, lo) if v > 0 else lo
            f = (log10(v) - log10(lo)) / (log10(hi) - log10(lo))
        else:
            f = (v - lo) / (hi - lo)
        return min(1.0, max(0.0, f))

    px = lambda v: left + sc(v, x0, x1, xlog) * (right - left)  # noqa: E731
    py = lambda v: bottom - sc(v, y0, y1, ylog) * (bottom - top)  # noqa: E731
    body = _title(title, width)
    for t in yt:
        body.append(f'<line class="grid" x1="{_n(left)}" x2="{_n(right)}" y1="{_n(py(t))}" y2="{_n(py(t))}" stroke="{GRID}"/>')
        body.append(_text(left - 6, py(t) + 4, _fmt_tick(t, ylog), 10, "end", "ytick-label", MUTED))
    for t in xt:
        body.append(f'<line class="xtick" x1="{_n(px(t))}" x2="{_n(px(t))}" y1="{_n(bottom)}" y2="{_n(bottom + 4)}" stroke="{MUTED}"/>')
        body.append(_text(px(t), bottom + 17, _fmt_tick(t, xlog), 10, "middle", "xtick-label", MUTED))
    body.append(f'<rect class="frame" x="{_n(left)}" y="{_n(top)}" width="{_n(right - left)}" height="{_n(bottom - top)}" '
                f'fill="none" stroke="{MUTED}"/>')
    body.append(_text((left + right) / 2, bottom + 40, xlabel, 12, "middle", "xlabel"))
    body.append(_text(16, (top + bottom) / 2, ylabel, 12, "middle", "ylabel", extra=f' transform="rotate(-90 16 {_n((top + bottom) / 2)})"'))
    legend = []
    for i, s in enumerate(data):
        color, dash, shape = PALETTE[i % len(PALETTE)], DASHES[i % len(DASHES)], MARKERS[i % len(MARKERS)]
        lo, hi = s.get("lo"), s.get("hi")
        pts = []
        for j, (x, y) in enumerate(zip(s["x"], s["y"])):
            if xs_ok(x) and ys_ok(y):
                has = lo is not None and hi is not None and ys_ok(lo[j]) and ys_ok(hi[j])
                pts.append((float(x), float(y), float(lo[j]) if has else None, float(hi[j]) if has else None))
            else:
                pts.append(None)
        if s["kind"] == "ref":
            for run in _runs(pts):
                d = "M" + "L".join(f"{_n(px(p[0]))},{_n(py(p[1]))}" for p in run)
                body.append(f'<path class="ref" d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="5 4"/>')
            legend.append((s["name"], lambda x, y: f'<line x1="{x}" x2="{x + 26}" y1="{y}" y2="{y}" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="5 4"/>'))
            continue
        for run in _runs(pts):
            if ci == "band":
                for sub in _runs([p if p[2] is not None else None for p in run]):
                    if len(sub) > 1:
                        up = [f"{_n(px(p[0]))},{_n(py(p[3]))}" for p in sub]
                        dn = [f"{_n(px(p[0]))},{_n(py(p[2]))}" for p in reversed(sub)]
                        body.append(f'<polygon class="band" points="{" ".join(up + dn)}" fill="{color}" fill-opacity="0.18" stroke="none"/>')
                    else:  # a lone point has no band: draw its whisker
                        body.append(_whisker(px(sub[0][0]), py(sub[0][2]), py(sub[0][3]), color))
            elif ci == "bars":
                body += [_whisker(px(p[0]), py(p[2]), py(p[3]), color) for p in run if p[2] is not None]
            if s["kind"] == "line" and len(run) > 1:
                d = "M" + "L".join(f"{_n(px(p[0]))},{_n(py(p[1]))}" for p in run)
                da = f' stroke-dasharray="{dash}"' if dash else ""
                body.append(f'<path class="ln" d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{da}/>')
        for run in _runs(pts):
            body += [_marker(shape, px(p[0]), py(p[1]), color) for p in run]
        if s.get("name"):
            da = f' stroke-dasharray="{dash}"' if dash and s["kind"] == "line" else ""
            line = s["kind"] == "line"
            legend.append((s["name"], lambda x, y, c=color, da=da, sh=shape, line=line: (
                (f'<line x1="{x}" x2="{x + 26}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="1.8"{da}/>' if line else "")
                + _marker(sh, x + 13, y, c, "swatch"))))
    # failure strips above the plot, one row per fail series
    for k, s in enumerate(fails):
        j = next((m for m, d in enumerate(data) if d.get("name") == s.get("owner")), None)
        color = PALETTE[(j if j is not None else len(data) + k) % len(PALETTE)]
        yy = top - 14 - 18 * (len(fails) - 1 - k)
        body.append(f'<line class="strip" x1="{_n(left)}" x2="{_n(right)}" y1="{_n(yy + 9)}" y2="{_n(yy + 9)}" stroke="{GRID}"/>')
        labels = s.get("labels")
        for m, x in enumerate(s["x"]):
            if xs_ok(x):
                body.append(_cross(px(float(x)), yy, color))
                if labels is not None and labels[m] not in (None, ""):
                    body.append(_text(px(float(x)) + 7, yy + 4, labels[m], 9, cls="fail-label", color=MUTED))
        body.append(_text(right + 10, yy + 4, "x " + s["name"], 11, cls="strip-label", color=color))
    body += _legend(legend, right + 14, top + 8)
    d = desc or (f"{'Line chart' if kind == 'line' else 'Scatter plot'} \"{title}\": {len(data)} series, "
                 f"x axis {xlabel}{' (log)' if xlog else ''} from {_fmt_tick(x0, xlog)} to {_fmt_tick(x1, xlog)}, "
                 f"y axis {ylabel}{' (log)' if ylog else ''} from {_fmt_tick(y0, ylog)} to {_fmt_tick(y1, ylog)}"
                 + (f"; {len(fails)} failure rows" if fails else "") + ".")
    return _svg(width, height, title, d, body)


def _whisker(x, ylo, yhi, color):
    d = f"M{_n(x)},{_n(ylo)}L{_n(x)},{_n(yhi)}M{_n(x - 3)},{_n(ylo)}h6M{_n(x - 3)},{_n(yhi)}h6"
    return f'<path class="eb" d="{d}" fill="none" stroke="{color}" stroke-width="1.2"/>'


def line_chart(series, title="", xlabel="", ylabel="", ylog=False, xlim=None, ylim=None, ci="band",
               width=720, height=440, desc=None):
    """Lines with markers vs a numeric x axis; ci = "band" | "bars" for series that carry lo/hi."""
    return _xy("line", series, title, xlabel, ylabel, False, ylog, xlim, ylim, ci, width, height, desc)


def scatter(series, title="", xlabel="", ylabel="", xlog=False, ylog=False, xlim=None, ylim=None, ci="bars",
            width=720, height=440, desc=None):
    """Markers (and optional "ref" lines / "fail" strips) on linear or log axes."""
    return _xy("scatter", series, title, xlabel, ylabel, xlog, ylog, xlim, ylim, ci, width, height, desc)


def bar_chart(categories, series, title="", xlabel="", ylabel="", ylim=None, width=720, height=440, desc=None):
    """Grouped bars: one group per category, one bar per series; optional lo/hi whiskers; fill patterns per series."""
    vals = [float(v) for s in series for v in s["y"] if _ok(v)]
    if not categories or not vals:
        return _empty(title, width, height)
    allv = vals + [float(v) for s in series for k in ("lo", "hi") if s.get(k) is not None for v in s[k] if _ok(v)]
    yt, y0, y1 = _axis(allv + [0.0], False, ylim)
    left, top, right, bottom = _layout(width, height, series, [s["name"] for s in series], [])
    py = lambda v: bottom - min(1.0, max(0.0, (v - y0) / (y1 - y0))) * (bottom - top)  # noqa: E731
    band = (right - left) / len(categories)
    bw = band * 0.8 / len(series)
    body = _title(title, width)
    for t in yt:
        body.append(f'<line class="grid" x1="{_n(left)}" x2="{_n(right)}" y1="{_n(py(t))}" y2="{_n(py(t))}" stroke="{GRID}"/>')
        body.append(_text(left - 6, py(t) + 4, _fmt_tick(t), 10, "end", "ytick-label", MUTED))
    defs = "".join(
        f'<pattern id="fill{i}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate({a})">'
        f'<rect width="6" height="6" fill="{PALETTE[i % len(PALETTE)]}"/>{m}</pattern>'
        for i, (a, m) in enumerate(_hatch(len(series))))
    for c, cat in enumerate(categories):
        cx = left + band * (c + 0.5)
        body.append(_text(cx, bottom + 17, cat, 10, "middle", "xtick-label", MUTED))
        for i, s in enumerate(series):
            v = s["y"][c]
            if not _ok(v):
                continue
            x = left + band * c + band * 0.1 + bw * i
            body.append(f'<rect class="bar" x="{_n(x)}" y="{_n(py(float(v)))}" width="{_n(bw * 0.92)}" '
                        f'height="{_n(py(0) - py(float(v)))}" fill="url(#fill{i})" stroke="{INK}" stroke-width="0.6"/>')
            lo, hi = s.get("lo"), s.get("hi")
            if lo is not None and hi is not None and _ok(lo[c]) and _ok(hi[c]):
                body.append(_whisker(x + bw * 0.46, py(float(lo[c])), py(float(hi[c])), INK))
    body.append(f'<rect class="frame" x="{_n(left)}" y="{_n(top)}" width="{_n(right - left)}" height="{_n(bottom - top)}" fill="none" stroke="{MUTED}"/>')
    body.append(_text((left + right) / 2, bottom + 40, xlabel, 12, "middle", "xlabel"))
    body.append(_text(16, (top + bottom) / 2, ylabel, 12, "middle", "ylabel", extra=f' transform="rotate(-90 16 {_n((top + bottom) / 2)})"'))
    body += _legend([(s["name"], lambda x, y, i=i: f'<rect class="swatch" x="{x + 4}" y="{y - 6}" width="22" height="12" fill="url(#fill{i})" stroke="{INK}" stroke-width="0.6"/>')
                     for i, s in enumerate(series)], right + 14, top + 8)
    d = desc or (f"Bar chart \"{title}\": {len(categories)} categories ({', '.join(categories)}), {len(series)} series, "
                 f"y axis {ylabel} from {_fmt_tick(y0)} to {_fmt_tick(y1)}.")
    return _svg(width, height, title, d, body, defs)


def _hatch(n):
    """(rotation, white mark) of each series' fill pattern: solid, diagonal, horizontal, dots, cross."""
    marks = [(0, ""),
             (45, '<line x1="0" y1="0" x2="0" y2="6" stroke="#fff" stroke-width="2.2"/>'),
             (0, '<line x1="0" y1="3" x2="6" y2="3" stroke="#fff" stroke-width="2"/>'),
             (0, '<circle cx="3" cy="3" r="1.4" fill="#fff"/>'),
             (0, '<line x1="0" y1="0" x2="0" y2="6" stroke="#fff" stroke-width="1.6"/><line x1="0" y1="3" x2="6" y2="3" stroke="#fff" stroke-width="1.6"/>')]
    return [marks[i % len(marks)] for i in range(n)]
