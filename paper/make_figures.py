"""Draws the paper's figures from results/*.json and results/*.md.

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
TEAL, AMBER, GREY, INK = "#0A6B7D", "#C9770F", "#8A9A9A", "#10201F"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    ax.set_xlim(0, 118)
    ax.set_ylim(0, 32)
    ax.axis("off")
    steps = [("Environment", "state, rules"), ("Propose", "plans"), ("Merge", "plan graph"),
             ("Check", "rules, memory"), ("Choose", "score, solver"), ("Run", "execute")]
    w, gap, x = 14.2, 3.4, 0.8
    centres = []
    for i, (a, b) in enumerate(steps):
        fc = "#E6ECEC" if i == 0 else "#DDEFF2"
        ax.add_patch(FancyBboxPatch((x, 15), w, 12, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fc, ec=TEAL, lw=1.3))
        ax.text(x + w / 2, 22.6, a, ha="center", va="center", fontweight="bold", fontsize=8, color=INK)
        ax.text(x + w / 2, 18.4, b, ha="center", va="center", fontsize=6.6, color="#3E5252")
        centres.append(x + w / 2)
        if i:
            ax.add_patch(FancyArrowPatch((x - gap + 0.3, 21), (x - 0.2, 21), arrowstyle="-|>", mutation_scale=9, color=INK, lw=1.2))
        x += w + gap
    ax.add_patch(FancyArrowPatch((x - gap + 0.3, 21), (x + 0.2, 21), arrowstyle="-|>", mutation_scale=9, color=INK, lw=1.2))
    ax.add_patch(FancyBboxPatch((x + 0.4, 16.5), 9.2, 9, boxstyle="round,pad=0.3,rounding_size=1", fc="#E6ECEC", ec=TEAL, lw=1.3))
    ax.text(x + 5, 21, "Valid\npath", ha="center", va="center", fontsize=7, fontweight="bold", color=INK)
    ax.add_patch(FancyArrowPatch((centres[5], 14.2), (centres[1], 14.2), connectionstyle="arc3,rad=-0.3",
                                 arrowstyle="-|>", mutation_scale=9, color=AMBER, lw=1.3))
    ax.text((centres[1] + centres[5]) / 2, 2.2, "mismatch: record the failure, replan from the real state", ha="center", fontsize=7.2, color=AMBER)
    fig.savefig(OUT / "pipeline.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def boxoban():
    sets = [("Unfiltered", "boxoban_unfiltered.md"), ("Medium", "boxoban.md"), ("Hard", "boxoban_hard.md")]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5), sharey=True)
    pat = re.compile(r"\| ([\d,]+) \| (\d+)% \[(\d+)%, (\d+)%\] \| (\d+)% \[(\d+)%, (\d+)%\] \|")
    for ax, (name, f) in zip(axes, sets):
        rows = [[int(v.replace(",", "")) for v in m] for m in pat.findall((ROOT / "results" / f).read_text(encoding="utf-8"))]
        x = [r[0] for r in rows]
        ax.fill_between(x, [r[2] for r in rows], [r[3] for r in rows], color=GREY, alpha=.25, lw=0)
        ax.fill_between(x, [r[5] for r in rows], [r[6] for r in rows], color=TEAL, alpha=.25, lw=0)
        ax.plot(x, [r[1] for r in rows], "o-", color=GREY, ms=3.5, lw=1.4, label="no pruning")
        ax.plot(x, [r[4] for r in rows], "o-", color=TEAL, ms=3.5, lw=1.4, label="with checker")
        ax.set_title(name, fontsize=9, color=INK)
        ax.set_xscale("log")
        ax.minorticks_off()
        ax.set_xticks([2000, 5000, 10000, 30000])
        ax.set_xticklabels(["2k", "5k", "10k", "30k"])
        ax.set_xlabel("nodes per search")
        ax.set_ylim(0, 100)
        ax.grid(alpha=.25, lw=.5)
    axes[0].set_ylabel("levels solved (%)")
    axes[0].legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "boxoban.png", dpi=220)
    plt.close(fig)


def peg():
    H = json.loads((ROOT / "results" / "hard_games.json").read_text(encoding="utf-8"))["peg"]
    ks = list(H)
    xs = range(len(ks))
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.4))
    for off, arm, col, lab in ((-.2, "plain", GREY, "no checker"), (.2, "checker", TEAL, "pagoda checker")):
        a.bar([i + off for i in xs], [H[k][arm]["solved"] * 100 for k in ks], .38, color=col, label=lab)
        b.bar([i + off for i in xs], [H[k][arm]["nodes"] for k in ks], .38, color=col, label=lab)
    for ax in (a, b):
        ax.set_xticks(list(xs))
        ax.set_xticklabels(ks)
        ax.set_xlabel("jumps from the goal")
        ax.grid(axis="y", alpha=.25, lw=.5)
    a.set_ylabel("positions solved (%)")
    a.set_ylim(0, 105)
    b.set_ylabel("mean nodes per search")
    b.set_yscale("log")
    b.legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "peg.png", dpi=220)
    plt.close(fig)


def search_methods():
    S = json.loads((ROOT / "results" / "search_methods.json").read_text(encoding="utf-8"))["games"]
    algs = [("BFS", GREY), ("DFS", AMBER), ("weighted A*", TEAL), ("meet in the middle", "#2B3A67")]
    games = list(S)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    h = .2
    for j, (alg, col) in enumerate(algs):
        ys = [i + (j - 1.5) * h for i in range(len(games))]
        vals = [S[g][alg]["solved"] * 100 if alg in S[g] else 0 for g in games]
        ax.barh(ys, vals, h, color=col, label=alg)
    ax.set_yticks(range(len(games)))
    ax.set_yticklabels(games, fontsize=7.4)
    ax.invert_yaxis()
    ax.set_xlabel("instances solved within 100,000 nodes (%)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x", alpha=.25, lw=.5)
    ax.legend(frameon=False, fontsize=7.2, ncol=4, loc="upper center", bbox_to_anchor=(.45, 1.1))
    fig.tight_layout()
    fig.savefig(OUT / "search_methods.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    boxoban()
    peg()
    search_methods()
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
