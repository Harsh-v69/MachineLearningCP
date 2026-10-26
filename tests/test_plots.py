import xml.etree.ElementTree as ET
from math import nan

from tapegraph.plots import bar_chart, line_chart, scatter

NS = "{http://www.w3.org/2000/svg}"


def parse(svg):
    return ET.fromstring(svg.encode("utf-8"))


def by_class(root, cls, tag=None):
    return [e for e in root.iter() if e.get("class") == cls and (tag is None or e.tag == NS + tag)]


def texts(root, cls):
    return [e.text for e in by_class(root, cls)]


S2 = [{"name": "react", "x": [1, 2, 3], "y": [0.2, 0.5, 0.9], "lo": [0.1, 0.4, 0.8], "hi": [0.3, 0.6, 1.0]},
      {"name": "tape", "x": [1, 2, 3], "y": [0.3, 0.6, 0.7]}]


def test_line_chart_counts_and_metadata():
    svg = line_chart(S2, title="Success", xlabel="T*", ylabel="rate", ylim=(0, 1))
    r = parse(svg)
    assert r.tag == NS + "svg" and r.get("viewBox") and r.get("width") is None
    assert r.find(NS + "title").text == "Success" and "Line chart" in r.find(NS + "desc").text
    assert len(by_class(r, "ln")) == 2
    assert len(by_class(r, "pt", "circle")) == 3 and len(by_class(r, "pt", "rect")) == 3  # distinct marker shapes
    assert len(by_class(r, "band")) == 1  # only the series with lo/hi
    assert texts(r, "legend") == ["react", "tape"]
    assert texts(r, "ytick-label") == ["0", "0.2", "0.4", "0.6", "0.8", "1"]
    assert by_class(r, "bg")[0].get("fill") == "#ffffff"


def test_series_differ_by_dash_and_colour():
    r = parse(line_chart(S2, title="t"))
    l1, l2 = by_class(r, "ln")
    assert l1.get("stroke") != l2.get("stroke") and l1.get("stroke-dasharray") != l2.get("stroke-dasharray")


def test_ci_bars_mode():
    r = parse(line_chart(S2, title="t", ci="bars"))
    assert len(by_class(r, "eb")) == 3 and not by_class(r, "band")


def test_nan_and_none_break_lines():
    s = [{"name": "a", "x": [1, 2, 3, 4, 5], "y": [1, 2, None, 4, nan]}]
    r = parse(line_chart(s, title="t"))
    assert len(by_class(r, "ln")) == 1  # runs: [1,2] line; [4] single point has no line; nan dropped
    assert len(by_class(r, "pt")) == 3
    assert by_class(r, "ln")[0].get("d").count("L") == 1


def test_escaping():
    s = [{"name": 'a<b & "c"', "x": [1, 2], "y": [1, 2]}]
    svg = line_chart(s, title="x < y & z", xlabel='say "hi"', ylabel="<y>")
    r = parse(svg)  # would raise on unescaped characters
    assert r.find(NS + "title").text == "x < y & z"
    assert texts(r, "legend") == ['a<b & "c"'] and texts(r, "xlabel") == ['say "hi"']
    assert "<y>" not in svg and "&lt;y&gt;" in svg


def test_log_axis_ticks():
    s = [{"name": "a", "x": [1, 2, 3], "y": [0.0004, 0.5, 250.0]}]
    r = parse(line_chart(s, title="t", ylog=True))
    assert texts(r, "ytick-label") == ["0.0001", "0.001", "0.01", "0.1", "1", "10", "100", "1000"]
    ys = {t.text: float(t.get("y")) for t in by_class(r, "ytick-label")}
    # equal pixel spacing per decade
    gaps = [ys[a] - ys[b] for a, b in [("0.001", "0.01"), ("0.01", "0.1"), ("1", "10"), ("100", "1000")]]
    assert min(gaps) > 0 and max(gaps) - min(gaps) < 0.1
    big = parse(line_chart([{"name": "a", "x": [1, 2], "y": [1e-6, 1e6]}], title="t", ylog=True))
    assert texts(big, "ytick-label")[0] == "1e-6" and texts(big, "ytick-label")[-1] == "1e6"


def test_log_drops_nonpositive_points():
    r = parse(line_chart([{"name": "a", "x": [1, 2, 3], "y": [0, 5, 50]}], title="t", ylog=True))
    assert len(by_class(r, "pt")) == 2


def test_empty_and_all_nan():
    for series in ([], [{"name": "a", "x": [], "y": []}], [{"name": "a", "x": [1, 2], "y": [nan, None]}]):
        for fn in (line_chart, scatter):
            r = parse(fn(series, title="T"))
            assert texts(r, "nodata") == ["no data"] and r.find(NS + "title").text == "T"
    r = parse(bar_chart(["a"], [{"name": "s", "y": [None]}], title="T"))
    assert texts(r, "nodata") == ["no data"]


def test_deterministic():
    for fn, args in ((line_chart, (S2,)), (scatter, (S2,)), (bar_chart, (["a", "b", "c"], S2))):
        assert fn(*args, title="t") == fn(*args, title="t")


def test_scatter_loglog_ref_and_fail_strip():
    s = [{"name": "rows", "x": [0.001, 0.01, 1], "y": [0.01, 0.5, 20], "kind": "points"},
         {"name": "y = x", "x": [0.001, 1], "y": [0.001, 1], "kind": "ref"},
         {"name": "ILP timeout", "x": [0.02, 0.5], "labels": ["1", "2"], "owner": "rows", "kind": "fail"}]
    r = parse(scatter(s, title="t", xlog=True, ylog=True, xlim=(0.001, 1), ylim=(0.001, 100)))
    assert texts(r, "xtick-label") == ["0.001", "0.01", "0.1", "1"]
    assert texts(r, "ytick-label")[-1] == "100"
    assert len(by_class(r, "pt")) == 3 and len(by_class(r, "ref")) == 1
    assert len(by_class(r, "fail", "path")) == 2 and texts(r, "fail-label") == ["1", "2"]
    assert texts(r, "strip-label") == ["x ILP timeout"]
    cross = by_class(r, "fail")[0]
    assert cross.get("fill") == "none"  # hollow marker
    # the strip sits above the plot frame
    frame = by_class(r, "frame")[0]
    assert float(cross.get("d").split("M")[1].split(",")[1].split("L")[0]) < float(frame.get("y"))
    assert texts(r, "legend") == ["rows", "y = x"]


def test_scatter_x_domain_includes_fail_x():
    s = [{"name": "p", "x": [1, 2], "y": [1, 2]}, {"name": "f", "x": [50], "kind": "fail"}]
    r = parse(scatter(s, title="t"))
    assert float(texts(r, "xtick-label")[-1]) >= 50


def test_bar_chart_counts_whiskers_and_patterns():
    ser = [{"name": "ILP", "y": [1.0, 0.5, 0.25], "lo": [0.8, 0.3, 0.1], "hi": [1.0, 0.7, 0.4]},
           {"name": "A*", "y": [1.0, 1.0, None]}]
    svg = bar_chart(["c2", "c4", "c8"], ser, title="Solve rate", xlabel="c_slack", ylabel="rate", ylim=(0, 1))
    r = parse(svg)
    assert len(by_class(r, "bar")) == 5 and len(by_class(r, "eb")) == 3
    assert texts(r, "xtick-label") == ["c2", "c4", "c8"] and texts(r, "legend") == ["ILP", "A*"]
    fills = {b.get("fill") for b in by_class(r, "bar")}
    assert fills == {"url(#fill0)", "url(#fill1)"} and len(list(r.iter(NS + "pattern"))) == 2
