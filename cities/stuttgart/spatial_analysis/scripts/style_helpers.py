# spatialviz/style_helpers.py
from __future__ import annotations
from typing import Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def add_north_arrow(ax, extent: Tuple[float,float,float,float], size_frac=0.08):
    xmin, ymin, xmax, ymax = extent
    w, h = xmax - xmin, ymax - ymin
    x = xmin + w*0.93
    y = ymin + h*0.15
    L = max(w,h) * size_frac
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y + L),
        ha="center", va="center",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=2),
        fontsize=11, fontweight="bold",
        bbox=dict(boxstyle="circle,pad=0.25", facecolor="white", edgecolor="black", alpha=0.9),
        color="black"
    )

def add_scalebar(ax, extent: Tuple[float,float,float,float]):
    xmin, ymin, xmax, ymax = extent
    w, h = xmax - xmin, ymax - ymin
    target = w/5
    # nice length (m)
    for L in [500, 1000, 2000, 5000, 10000, 20000]:
        if L >= target: break
    x0 = xmin + w*0.05
    y0 = ymin + h*0.08
    bar_h = max(2.0, L*0.01)
    half = L/2
    rect1 = patches.Rectangle((x0, y0-bar_h/2), half, bar_h, facecolor="black", edgecolor="black")
    rect2 = patches.Rectangle((x0+half, y0-bar_h/2), half, bar_h, facecolor="white", edgecolor="black")
    ax.add_patch(rect1); ax.add_patch(rect2)
    ax.text(x0, y0+bar_h*0.9, "0", fontsize=9, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))
    ax.text(x0+half, y0+bar_h*0.9, f"{int(half/1000)} km", fontsize=9, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))
    ax.text(x0+L, y0+bar_h*0.9, f"{int(L/1000)} km", fontsize=9, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))

def apply_style(ax, extent):
    ax.set_aspect("equal")
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_axis_off()
    add_north_arrow(ax, extent)
    add_scalebar(ax, extent)

def palette():
    return dict(
        motorway="#252525", primary="#4f4f4f", secondary="#8a8a8a", residential="#c2c2c2",
        cycle="#0ea5e9",
        green_fill="#8bd3a3", green_edge="#3d7a57",
        greens=["#e8f5e9","#c8e6c9","#a5d6a7","#81c784","#66bb6a","#43a047","#2e7d32","#1b5e20"],
        blues=["#e3f2fd","#bbdefb","#90caf9","#64b5f6","#42a5f5","#2196f3","#1e88e5","#1976d2"],
        purples=["#f3e5f5","#e1bee7","#ce93d8","#ba68c8","#ab47bc","#9c27b0","#8e24aa","#7b1fa2"],
        oranges=["#fff3e0","#ffe0b2","#ffcc80","#ffb74d","#ffa726","#ff9800","#fb8c00","#f57c00"],
        viridis=["#440154","#482878","#3e4989","#31688e","#26828e","#1f9e89","#35b779","#6ece58","#b5de2b","#fde725"],
    )
