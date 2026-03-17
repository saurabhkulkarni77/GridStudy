"""utils/charts.py — Plotly dark-theme chart helpers."""

import plotly.graph_objects as go
import plotly.express as px

DARK_BG   = "#161b22"
GRID_CLR  = "rgba(48,54,61,0.8)"
TEXT_CLR  = "#c9d1d9"
SUBTLE    = "#8b949e"

PALETTE = {
    "green":  "#3fb950",
    "amber":  "#d29922",
    "red":    "#f85149",
    "blue":   "#58a6ff",
    "purple": "#bc8cff",
    "teal":   "#39c5cf",
    "orange": "#f0883e",
}

def base_layout(title: str = "", h: int = 320, legend: bool = True) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=TEXT_CLR, size=13)),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(family="system-ui", color=TEXT_CLR, size=11),
        height=h,
        margin=dict(l=48, r=16, t=36, b=36),
        xaxis=dict(gridcolor=GRID_CLR, zerolinecolor=GRID_CLR, linecolor=GRID_CLR),
        yaxis=dict(gridcolor=GRID_CLR, zerolinecolor=GRID_CLR, linecolor=GRID_CLR),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=GRID_CLR,
            font=dict(size=10),
        ) if legend else dict(visible=False),
        hovermode="x unified",
    )

def status_color(val, warn_thresh, danger_thresh, reverse=False):
    """Return color string based on thresholds."""
    if not reverse:
        if val >= danger_thresh: return PALETTE["red"]
        if val >= warn_thresh:   return PALETTE["amber"]
        return PALETTE["green"]
    else:
        if val <= danger_thresh: return PALETTE["red"]
        if val <= warn_thresh:   return PALETTE["amber"]
        return PALETTE["green"]
