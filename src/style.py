"""
style.py
Shared Plotly styling so every chart in the app reads as one system rather
than each page inventing its own colors.

Charts are styled for a dark background.

Palette: Okabe-Ito, with two adjustments for dark backgrounds - 
the dark blue is lightened and pure black is replaced with a light gray. 
Assigned in a FIXED order per category everywhere in the app (never re-cycled 
when a filter changes which categories are present), so a given category always 
maps to the same color across pages.
"""

import plotly.graph_objects as go
import plotly.io as pio

# Fixed categorical order -- do not reorder per-chart; subset from the front
# instead so color always tracks identity, not position.
CATEGORICAL = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#4C9AFF",  # blue (Okabe-Ito #0072B2, lightened for dark bg)
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#A6A6A6",  # light gray (replaces Okabe-Ito black for dark bg)
]

# Sequential (magnitude): single hue, light -> dark.
SEQUENTIAL = "Blues"

# Diverging (polarity, e.g. growth-driver shares that can be + or -):
# two hues with a neutral dark-gray midpoint.
DIVERGING = [
    [0.0, "#D55E00"],
    [0.5, "#4a4f5a"],
    [1.0, "#4C9AFF"],
]

INK_PRIMARY = "#e6e8eb"    # headings, chart titles
INK_SECONDARY = "#a0a4ab"  # axis ticks and labels
INK_MUTED = "#6b7280"      # de-emphasized reference lines and series
GRID = "#262a33"           # recessive gridlines and baseline rules
SURFACE = "#0e1117"        # matches app backgroundColor

FORECAST_BAND = "rgba(76, 154, 255, 0.22)"       # translucent fill under the CI band
PARTIAL_YEAR_FILL = "rgba(255, 255, 255, 0.05)"  # shaded partial-year region


def category_color(index: int) -> str:
    return CATEGORICAL[index % len(CATEGORICAL)]


def category_color_rgba(index: int, alpha: float) -> str:
    """Same categorical color as category_color(), as an rgba() string. Use this
    for faded fills instead of marker.opacity."""
    hex_color = CATEGORICAL[index % len(CATEGORICAL)].lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def apply_layout(
    fig: go.Figure,
    title: str = None,
    y_title: str = None,
    x_title: str = None,
    height: int = 390,
) -> go.Figure:
    """Common layout: transparent panel, recessive grid, title stacked above
    the legend so the two never collide."""
    fig.update_layout(
        title=dict(
            text=title, x=0, xanchor="left", xref="paper",
            y=1, yanchor="top", yref="container", pad=dict(t=8),
            font=dict(size=15, color=INK_PRIMARY),
        ) if title else None,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK_SECONDARY, size=13),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(color=INK_SECONDARY, size=12),
        ),
        margin=dict(l=8, r=16, t=76 if title else 40, b=8),
        height=height,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#171b24", bordercolor=GRID,
            font=dict(color=INK_PRIMARY, size=12),
        ),
    )
    fig.update_xaxes(
        title=x_title, showgrid=False, linecolor=GRID, automargin=True,
        tickfont=dict(color=INK_SECONDARY), title_font=dict(color=INK_SECONDARY),
    )
    fig.update_yaxes(
        title=y_title, showgrid=True, gridcolor=GRID, automargin=True,
        zeroline=True, zerolinecolor=GRID,
        tickfont=dict(color=INK_SECONDARY), title_font=dict(color=INK_SECONDARY),
    )
    return fig


def setup_page_style():
    """Call once per Streamlit page to register the plotly template."""
    pio.templates.default = "plotly_dark"
