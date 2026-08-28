"""
style.py
Shared Plotly styling so every chart in the app reads as one system rather
than each page inventing its own colors.

Palette: Okabe-Ito, the standard colorblind-safe qualitative palette used
in scientific visualization (Okabe & Ito, 2008). Assigned in a FIXED order
per category everywhere in the app (never re-cycled when a filter changes
which categories are present), so a given category always maps to the same
color across pages.
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
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]

# Sequential (magnitude): single hue, light -> dark.
SEQUENTIAL = "Blues"

# Diverging (polarity, e.g. growth-driver shares that can be + or -):
# two hues with a neutral gray midpoint.
DIVERGING = [
    [0.0, "#D55E00"],
    [0.5, "#E5E5E5"],
    [1.0, "#0072B2"],
]

INK_PRIMARY = "#1a1a1a"
INK_SECONDARY = "#595959"
INK_MUTED = "#8c8c8c"
GRID = "#e8e8e8"
SURFACE = "#ffffff"

FORECAST_BAND = "rgba(0, 114, 178, 0.15)"  # translucent fill under the CI band


def category_color(index: int) -> str:
    return CATEGORICAL[index % len(CATEGORICAL)]


def apply_layout(fig: go.Figure, title: str = None, y_title: str = None, x_title: str = None) -> go.Figure:
    """Common layout: recessive grid, one axis, consistent type/margins."""
    fig.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=INK_PRIMARY, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60 if title else 20, b=10),
        hovermode="x unified",
    )
    fig.update_xaxes(title=x_title, showgrid=False, linecolor=GRID, tickfont=dict(color=INK_SECONDARY))
    fig.update_yaxes(title=y_title, showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                      tickfont=dict(color=INK_SECONDARY))
    return fig


def setup_page_style():
    """Call once per Streamlit page to register the plotly template."""
    pio.templates.default = "plotly_white"
