"""Draws the paper's figures from results/*.json and results/*.md, sized for one
column of the two-column IEEE layout (3.35 inches wide).

Run: python paper/make_figures.py   (writes paper/figures/*.png)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
TEAL, AMBER, GREY, NAVY, INK = "#000000", "#555555", "#9A9A9A", "#2A2A2A", "#000000"
plt.rcParams.update({"font.family": ["Times New Roman", "DejaVu Serif"], "font.size": 7, "axes.edgecolor": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "axes.linewidth": .6,
                     "axes.spines.top": False, "axes.spines.right": False, "xtick.major.width": .6, "ytick.major.width": .6})
W = 3.35


RNG = np.random.default_rng(7)
HAND = ["Ink Free", "Segoe Print", "Comic Sans MS"]


def wob(ax, pts, lw=1.1, amp=.18, color="#222222", closed=False):
    """A line through pts that wanders a little, like a pen on a canvas."""
    pts = list(pts) + ([pts[0]] if closed else [])
    xs, ys = [], []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(4, int(np.hypot(x1 - x0, y1 - y0) * 1.2))
        t = np.linspace(0, 1, n)
        nx, ny = RNG.normal(0, amp, n), RNG.normal(0, amp, n)
        nx[0] = ny[0] = nx[-1] = ny[-1] = 0
        xs += list(x0 + (x1 - x0) * t + np.convolve(nx, [.5, .5], "same"))
        ys += list(y0 + (y1 - y0) * t + np.convolve(ny, [.5, .5], "same"))
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round")


def pipeline():
    fig, ax = plt.subplots(figsize=(W, 2.45))
    ax.set_xlim(-1, 31.2)
    ax.set_ylim(0, 21)
    ax.axis("off")
    bw, bh = 8.6, 4.6
    cells = {"env": (0, 16, "Environment", "state, rules"), "prop": (10.7, 16, "Propose", "candidate plans"), "merge": (21.4, 16, "Merge", "plan graph"),
             "check": (21.4, 8.6, "Check", "rules + memory"), "choose": (10.7, 8.6, "Choose", "A* or CP-SAT"),
             "run": (0, 8.6, "Run", "execute path"), "path": (0, 1.2, "Done", "")}
    for k, (x, y, a, b) in cells.items():
        corners = [(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)]
        wob(ax, corners, closed=True)
        if k in ("check", "choose"):  # the two parts we added get a second pass of the pen
            wob(ax, [(x - .3, y - .25), (x + bw + .3, y - .2), (x + bw + .25, y + bh + .3), (x - .2, y + bh + .2)], lw=.7, color="#777777", closed=True)
        ax.text(x + bw / 2, y + bh * (.64 if b else .5), a, ha="center", va="center", fontsize=8.5, color="#111111", family=HAND)
        if b:
            ax.text(x + bw / 2, y + bh * .27, b, ha="center", va="center", fontsize=6.6, color="#333333", family=HAND)

    def arrow(p, q, curve=0.0, color="#222222"):
        (x0, y0), (x1, y1) = p, q
        mx, my = (x0 + x1) / 2 + curve, (y0 + y1) / 2 + curve * .4
        wob(ax, [p, (mx, my), q], lw=1.0, amp=.1, color=color)
        d = np.array([x1 - mx, y1 - my])
        d = d / np.hypot(*d)
        n = np.array([-d[1], d[0]])
        for sgn in (1, -1):
            h = np.array([x1, y1]) - d * 1.1 + n * sgn * .55
            wob(ax, [(x1, y1), tuple(h)], lw=1.0, amp=.05, color=color)

    arrow((bw + .3, 18.3), (10.4, 18.3))
    arrow((10.7 + bw + .3, 18.3), (21.1, 18.3))
    arrow((21.4 + bw / 2, 15.8), (21.4 + bw / 2, 13.5))
    arrow((21.1, 10.9), (10.7 + bw + .3, 10.9))
    arrow((10.4, 10.9), (bw + .3, 10.9))
    arrow((bw / 2, 8.3), (bw / 2, 6.1))
    arrow((bw * .85, 13.5), (10.7 + bw * .2, 15.8), curve=-.9, color="#555555")
    ax.text(4.3, 14.6, "mismatch: replan", ha="center", va="center", fontsize=6.2, color="#444444", family=HAND, rotation=0)
    fig.savefig(OUT / "pipeline.png", dpi=300, bbox_inches="tight", pad_inches=.03, facecolor="white")
    plt.close(fig)


def boxoban():
    sets = [("Unfiltered", "boxoban_unfiltered.md", TEAL), ("Medium", "boxoban.md", "#666666"), ("Hard", "boxoban_hard.md", "#999999")]
    pat = re.compile(r"\| ([\d,]+) \| (\d+)% \[(\d+)%, (\d+)%\] \| (\d+)% \[(\d+)%, (\d+)%\] \|")
    fig, ax = plt.subplots(figsize=(W, 2.55))
    for (name, f, col), mk in zip(sets, "os^"):
        rows = [[int(v.replace(",", "")) for v in m] for m in pat.findall((ROOT / "results" / f).read_text(encoding="utf-8"))]
        x = [r[0] for r in rows]
        ax.plot(x, [r[4] for r in rows], mk + "-", color=col, ms=2.8, lw=1.1, label=f"{name}, with checker")
        ax.plot(x, [r[1] for r in rows], mk + "--", color=col, ms=2.8, lw=1.0, mfc="white", label=f"{name}, no pruning")
    ax.set_xscale("log")
    ax.minorticks_off()
    ax.set_xticks([2000, 5000, 10000, 30000])
    ax.set_xticklabels(["2k", "5k", "10k", "30k"])
    ax.set_xlabel("nodes per search")
    ax.set_ylabel("levels solved (%)")
    ax.set_ylim(0, 100)
    ax.grid(alpha=.25, lw=.4)
    ax.legend(frameon=False, fontsize=5.4, ncol=2, loc="lower center", bbox_to_anchor=(.5, 1.0), handlelength=2.2, columnspacing=1.0)
    fig.tight_layout(pad=.4)
    fig.savefig(OUT / "boxoban.png", dpi=300)
    plt.close(fig)


def peg():
    H = json.loads((ROOT / "results" / "hard_games.json").read_text(encoding="utf-8"))["peg"]
    ks = list(H)
    xs = list(range(len(ks)))
    fig, (a, b) = plt.subplots(2, 1, figsize=(W, 3.0), sharex=True)
    for off, arm, col, lab in ((-.2, "plain", "#CFCFCF", "no checker"), (.2, "checker", "white", "pagoda checker")):
        a.bar([i + off for i in xs], [H[k][arm]["solved"] * 100 for k in ks], .38, color=col, label=lab, edgecolor="black", lw=.4, hatch="///" if arm == "checker" else None)
        b.bar([i + off for i in xs], [H[k][arm]["nodes"] for k in ks], .38, color=col, edgecolor="black", lw=.4, hatch="///" if arm == "checker" else None)
    a.set_ylabel("solved (%)")
    a.set_ylim(0, 112)
    b.set_ylabel("mean nodes")
    b.set_yscale("log")
    b.set_xticks(xs)
    b.set_xticklabels(ks)
    b.set_xlabel("jumps from the goal")
    for ax in (a, b):
        ax.grid(axis="y", alpha=.25, lw=.4)
    a.legend(frameon=False, fontsize=6, ncol=2, loc="upper right")
    fig.tight_layout(pad=.4)
    fig.savefig(OUT / "peg.png", dpi=300)
    plt.close(fig)


def search_methods():
    S = json.loads((ROOT / "results" / "search_methods.json").read_text(encoding="utf-8"))["games"]
    algs = [("BFS", "#E0E0E0"), ("DFS", "#A0A0A0"), ("weighted A*", "#505050"), ("meet in the middle", "white")]
    games = list(S)
    fig, ax = plt.subplots(figsize=(W, 3.7))
    h = .2
    for j, (alg, col) in enumerate(algs):
        ys = [i + (j - 1.5) * h for i in range(len(games))]
        ax.barh(ys, [S[g][alg]["solved"] * 100 if alg in S[g] else 0 for g in games], h, color=col, label=alg, edgecolor="black", lw=.4, hatch="///" if alg.startswith("meet") else None)
    ax.set_yticks(range(len(games)))
    ax.set_yticklabels(games, fontsize=5.8)
    ax.invert_yaxis()
    ax.set_xlabel("instances solved within 100,000 nodes (%)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x", alpha=.25, lw=.4)
    ax.legend(frameon=False, fontsize=5.8, ncol=4, loc="upper center", bbox_to_anchor=(.35, 1.1), columnspacing=.8, handlelength=1.2)
    fig.tight_layout(pad=.4)
    fig.savefig(OUT / "search_methods.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    boxoban()
    peg()
    search_methods()
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
