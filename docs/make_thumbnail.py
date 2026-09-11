"""b-bridge gallery thumbnail, 1920x1080.

Designed to survive being shrunk to a ~300 px mod card: three text elements, one shape,
thick strokes. Nothing here is meant to be read at full size.

    python make_thumbnail.py     -> writes ./figures/thumbnail.png
"""
import os
import plotly.graph_objects as go
from figstyle import (SERIF, SANS, MONO, SURFACE, INK, INK2, MUTED,
                      BLUE, ORANGE, AQUA, box, label)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
fig = go.Figure()
fig.update_layout(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    width=W, height=H, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
    xaxis=dict(range=[0, 100], visible=False, fixedrange=True),
    yaxis=dict(range=[0, 100], visible=False, fixedrange=True),
)

# ---- right: the two processes, and the channel between them
box(fig, 55, 56, 77, 84, ORANGE, "rgba(217,89,38,0.20)", width=7)
label(fig, 66, 74, "32-bit", 60, ORANGE, SANS)
label(fig, 66, 64, "the game", 40, INK2, SERIF)

box(fig, 55, 16, 77, 44, AQUA, "rgba(25,158,112,0.20)", width=7)
label(fig, 66, 34, "64-bit", 60, AQUA, SANS)
label(fig, 66, 24, "the renderer", 40, INK2, SERIF)

# the channel, drawn thick so it survives the downscale
fig.add_shape(type="line", x0=83, y0=70, x1=83, y1=30, line=dict(color=BLUE, width=9))
fig.add_shape(type="line", x0=77, y0=70, x1=83, y1=70, line=dict(color=BLUE, width=9))
fig.add_shape(type="line", x0=77, y0=30, x1=83, y1=30, line=dict(color=BLUE, width=9))
label(fig, 86, 50, "shared", 34, BLUE, SANS, anchor="left")
label(fig, 86, 44, "memory", 34, BLUE, SANS, anchor="left")

# ---- left: wordmark and the one number that matters
label(fig, 7, 70, "b-bridge", 150, INK, SERIF, anchor="left")
fig.add_shape(type="line", x0=7.5, y0=58, x1=46, y1=58, line=dict(color=AQUA, width=6))
label(fig, 7.5, 50, "Direct3D 9 moved out", 50, INK2, SERIF, anchor="left")
label(fig, 7.5, 43, "of the 32-bit process", 50, INK2, SERIF, anchor="left")

label(fig, 7.5, 27, "+880 MB", 86, AQUA, SANS, anchor="left")
label(fig, 7.5, 17, "address space returned", 38, MUTED, SERIF, anchor="left")

fig.write_image(os.path.join(OUT, "thumbnail.png"), scale=1)
print("wrote", os.path.join(OUT, "thumbnail.png"))
