"""Draws the paper's figures from results/*.json and results/*.md, sized for one
column of the two-column IEEE layout (3.35 inches wide).

Run: python paper/make_figures.py   (writes paper/figures/*.png)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
TEAL, AMBER, GREY, NAVY, INK = "#0A6B7D", "#C9770F", "#7C8C8C", "#2B3A67", "#10201F"
plt.rcParams.update({"font.family": ["Times New Roman", "DejaVu Serif"], "font.size": 7, "axes.edgecolor": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "axes.linewidth": .6,
                     "axes.spines.top": False, "axes.spines.right": False, "xtick.major.width": .6, "ytick.major.width": .6})
W = 3.35


def pipeline():
    fig, ax = plt.subplots(figsize=(W, 2.35))
    ax.set_xlim(-1, 31.2)
    ax.set_ylim(0, 21)
    ax.axis("off")
    bw, bh = 8.6, 4.6
    cells = {"env": (0, 16, "Environment", "state, rules"), "prop": (10.7, 16, "Propose", "plans"), "merge": (21.4, 16, "Merge", "plan graph"),
             "check": (21.4, 8.6, "Check", "rules, memory"), "choose": (10.7, 8.6, "Choose", "score, solver"),
             "run": (0, 8.6, "Run", "execute"), "path": (0, 1.2, "Valid path", "")}
    for k, (x, y, a, b) in cells.items():
        fc = "#E6ECEC" if k in ("env", "path") else "#DDEFF2"
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.2,rounding_size=0.7", fc=fc, ec=TEAL, lw=.9))
        ax.text(x + bw / 2, y + bh * (.62 if b else .5), a, ha="center", va="center", fontweight="bold", fontsize=7, color=INK)
        if b:
            ax.text(x + bw / 2, y + bh * .27, b, ha="center", va="center", fontsize=5.6, color="#3E5252")

    def arrow(p, q, color=INK, rad=0.0):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, color=color, lw=.8, connectionstyle=f"arc3,rad={rad}"))

    arrow((bw + .3, 18.3), (10.4, 18.3))
    arrow((10.7 + bw + .3, 18.3), (21.1, 18.3))
    arrow((21.4 + bw / 2, 15.8), (21.4 + bw / 2, 13.5))
    arrow((21.1, 10.9), (10.7 + bw + .3, 10.9))
    arrow((10.4, 10.9), (bw + .3, 10.9))
    arrow((bw / 2, 8.3), (bw / 2, 6.1))
    arrow((bw * .8, 13.5), (10.7 + bw * .25, 15.8), color=AMBER, rad=-0.35)
    ax.text(18.8, 14.7, "mismatch: replan", ha="center", va="center", fontsize=5.6, color=AMBER)
    fig.savefig(OUT / "pipeline.png", dpi=300, bbox_inches="tight", pad_inches=.03)
    plt.close(fig)


def boxoban():
    sets = [("Unfiltered", "boxoban_unfiltered.md", TEAL), ("Medium", "boxoban.md", AMBER), ("Hard", "boxoban_hard.md", NAVY)]
    pat = re.compile(r"\| ([\d,]+) \| (\d+)% \[(\d+)%, (\d+)%\] \| (\d+)% \[(\d+)%, (\d+)%\] \|")
    fig, ax = plt.subplots(figsize=(W, 2.55))
    for name, f, col in sets:
        rows = [[int(v.replace(",", "")) for v in m] for m in pat.findall((ROOT / "results" / f).read_text(encoding="utf-8"))]
        x = [r[0] for r in rows]
        ax.plot(x, [r[4] for r in rows], "o-", color=col, ms=2.6, lw=1.1, label=f"{name}, with checker")
        ax.plot(x, [r[1] for r in rows], "o--", color=col, ms=2.6, lw=1.0, alpha=.75, label=f"{name}, no pruning")
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
    for off, arm, col, lab in ((-.2, "plain", GREY, "no checker"), (.2, "checker", TEAL, "pagoda checker")):
        a.bar([i + off for i in xs], [H[k][arm]["solved"] * 100 for k in ks], .38, color=col, label=lab)
        b.bar([i + off for i in xs], [H[k][arm]["nodes"] for k in ks], .38, color=col)
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
    algs = [("BFS", GREY), ("DFS", AMBER), ("weighted A*", TEAL), ("meet in the middle", NAVY)]
    games = list(S)
    fig, ax = plt.subplots(figsize=(W, 3.7))
    h = .2
    for j, (alg, col) in enumerate(algs):
        ys = [i + (j - 1.5) * h for i in range(len(games))]
        ax.barh(ys, [S[g][alg]["solved"] * 100 if alg in S[g] else 0 for g in games], h, color=col, label=alg)
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
