"""Shared figure style: Computer Modern on a dark surface.

Palette is the validated dark set (blue / orange / aqua / yellow on #1a1a19), which passes
the CVD separation and contrast checks. Type is CMU, the Computer Modern family LaTeX uses,
so the figures read as paper output rather than dashboard output.
"""

SERIF = "CMU Serif"
SANS  = "CMU Sans Serif"
MONO  = "CMU Typewriter Text"

SURFACE = "#1a1a19"
PANEL   = "#232320"
GRID    = "#3a3a36"
INK     = "#f2f0ea"
INK2    = "#b8b4a8"
MUTED   = "#7d7a70"

BLUE   = "#3987e5"
ORANGE = "#d95926"
AQUA   = "#199e70"
YELLOW = "#c98500"

BLUE_F   = "#16283f"
ORANGE_F = "#3b1d10"
AQUA_F   = "#0e2c22"
YELLOW_F = "#332413"


def base_layout(title=None, subtitle=None, height=720, width=1280):
    """Layout every figure starts from."""
    t = None
    if title:
        txt = f"<b>{title}</b>"
        if subtitle:
            txt += f"<br><span style='font-size:15px;color:{INK2}'>{subtitle}</span>"
        t = dict(text=txt, x=0.045, xanchor="left", y=0.94, yanchor="top",
                 font=dict(family=SERIF, size=26, color=INK))
    return dict(
        title=t,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=SANS, size=15, color=INK2),
        width=width,
        height=height,
        margin=dict(l=70, r=60, t=110 if title else 40, b=70),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, color=INK2,
                   linecolor=GRID, ticks="outside", tickcolor=GRID,
                   title_font=dict(family=SANS, size=15, color=INK2)),
        yaxis=dict(gridcolor=GRID, zeroline=False, color=INK2,
                   linecolor=GRID, ticks="outside", tickcolor=GRID,
                   title_font=dict(family=SANS, size=15, color=INK2)),
    )


def note(fig, text, y=-0.14):
    """A caption under the plot, the way a figure in a paper carries one."""
    fig.add_annotation(text=text, xref="paper", yref="paper", x=0, y=y,
                       xanchor="left", yanchor="top", showarrow=False,
                       align="left",
                       font=dict(family=SERIF, size=14, color=MUTED))


def box(fig, x0, y0, x1, y1, line, fill, width=2, dash=None):
    fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                  line=dict(color=line, width=width, dash=dash),
                  fillcolor=fill, layer="below")


def label(fig, x, y, text, size=15, color=None, family=None, anchor="center",
          valign="middle", angle=0):
    fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                       xanchor=anchor, yanchor=valign, textangle=angle,
                       font=dict(family=family or SANS, size=size, color=color or INK))


def arrow(fig, x0, y0, x1, y1, color=None, width=2, dash=None):
    fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y",
                       axref="x", ayref="y", showarrow=True, text="",
                       arrowhead=2, arrowsize=1.1, arrowwidth=width,
                       arrowcolor=color or MUTED)
    if dash:
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(color=color or MUTED, width=width, dash=dash))
