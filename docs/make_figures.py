"""Build the BrokerBridge research figures (Plotly) from the reference install's bench CSVs.

Outputs docs/figures/fig1..fig5.png and docs/figures.html. Run from anywhere:
    python docs/make_figures.py
"""
import csv, glob, os, statistics
import plotly.graph_objects as go
import plotly.io as pio

RUNS = r"H:\Steam\steamapps\common\Grand Theft Auto IV\GTAIV\_runs"
SCRATCH = r"C:\Users\Bash\AppData\Local\Temp\claude\H--Steam-steamapps-common-Grand-Theft-Auto-IV\13ee3bb3-b580-42af-aa5b-18f115dcb91a\scratchpad"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

# Reference palette (validated: adjacent CVD dE 9.2, normal dE 27.6, light surface)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"

LAYOUT = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color=INK),
    title=dict(x=0.0, xanchor="left", font=dict(size=16)),
    margin=dict(l=60, r=24, t=72, b=56),
    hovermode="closest",
    legend=dict(orientation="h", y=-0.22, x=0, font=dict(color=INK2)),
)
AXIS = dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=GRID,
            tickfont=dict(color=INK2), title_font=dict(color=INK2))


def frames(stamp):
    p = sorted(glob.glob(os.path.join(RUNS, f"benchroute_{stamp}*.csv")))[0]
    return [float(r[1]) for r in csv.reader(open(p)) if r and r[0].isdigit()]


def stats(ms):
    s = sorted(ms, reverse=True); k = max(1, len(ms) // 100)
    return statistics.mean(ms), 1000.0 / statistics.mean(s[:k])


def group(stamps):
    m = [stats(frames(s)) for s in stamps]
    return statistics.mean(x[0] for x in m), statistics.mean(x[1] for x in m), len(stamps)


def save(fig, name):
    fig.update_layout(**LAYOUT)
    fig.update_xaxes(**AXIS); fig.update_yaxes(**AXIS)
    fig.write_image(os.path.join(OUT, name + ".png"), width=1100, height=560, scale=2)
    return fig


figs = []

# ---------------------------------------------------------------- Figure 1: frame time by stage
stages = [
    ("In-process DXVK\n(2026-09-04, 6 runs)", ["20260904_0101", "20260904_0105", "20260904_0110", "20260904_0114", "20260904_0221", "20260904_0350"]),
    ("Bridge, upstream client\n(5 runs)", ["20260905_0240", "20260905_0246", "20260905_0250", "20260905_0254", "20260905_0259"]),
    ("Bridge, transfer plans +\nresponses off (4 runs)", ["20260905_0315", "20260905_0319", "20260905_0327", "20260905_0334"]),
    ("Bridge, final client\n(5 runs)", ["20260905_0441", "20260905_0459", "20260905_0504", "20260905_0508", "20260905_0353"]),
]
labels, means, lows = [], [], []
for name, stamps in stages:
    ok = [s for s in stamps if glob.glob(os.path.join(RUNS, f"benchroute_{s}*.csv"))]
    m, lo, n = group(ok)
    labels.append(name.replace("(%d runs)" % len(stamps), "(%d runs)" % n)); means.append(m); lows.append(lo)

fig1 = go.Figure()
fig1.add_bar(x=labels, y=means, marker=dict(color=BLUE, line=dict(width=0)), width=0.55,
             text=[f"{m:.1f} ms" for m in means], textposition="outside", textfont=dict(color=INK),
             hovertemplate="%{x}<br>mean %{y:.2f} ms<br>1%% low %{customdata:.1f} fps<extra></extra>",
             customdata=lows, name="Mean frame time")
fig1.add_hline(y=16.67, line=dict(color=INK2, width=1, dash="dot"),
               annotation_text="60 fps (16.7 ms)", annotation_position="top right", annotation_font_color=INK2)
fig1.update_layout(title="Figure 1. Mean frame time per client stage, same 60 s route (uncapped, RTX 2070, 1440p)",
                   yaxis_title="mean frame time (ms), lower is better", showlegend=False)
fig1.update_yaxes(range=[0, max(means) * 1.25])
figs.append(save(fig1, "fig1_frametime_stages"))

# ---------------------------------------------------------------- Figure 2: ECDF in-process vs bridge
a = sorted(frames("20260904_0350")); b = sorted(frames("20260905_0508"))
def ecdf(v): return v, [i / len(v) for i in range(1, len(v) + 1)]
fig2 = go.Figure()
for v, name, col in [(a, "In-process DXVK", ORANGE), (b, "BrokerBridge, final client", BLUE)]:
    x, y = ecdf(v)
    fig2.add_scatter(x=x, y=y, mode="lines", name=name, line=dict(color=col, width=2),
                     hovertemplate=name + "<br>%{x:.1f} ms at %{y:.0%} of frames<extra></extra>")
fig2.add_vline(x=16.67, line=dict(color=INK2, width=1, dash="dot"),
               annotation_text="60 fps", annotation_position="top", annotation_font_color=INK2)
fig2.update_layout(title="Figure 2. Frame-time distribution over the route, in-process vs bridged (one run each)",
                   xaxis_title="frame time (ms)", yaxis_title="share of frames at or below", hovermode="x unified")
fig2.update_xaxes(range=[5, 40]); fig2.update_yaxes(tickformat=".0%")
figs.append(save(fig2, "fig2_frametime_ecdf"))

# ---------------------------------------------------------------- Figure 3: address space at view 100
# In-process figure from the 2026-09-03 view-100 test (address-space census, largest contiguous free run);
# bridged figures are the per-session minimum of largest_free_mb from the 2026-09-06 evening runs.
bridged = []
for stamp in ["224023", "224606", "225049", "225533", "230015"]:
    rows = [r for r in csv.reader(open(os.path.join(RUNS, f"addrspace_20260906_{stamp}.csv")))
            if r and not r[0].startswith("#") and r[0] != "elapsed_s" and len(r) > 4]
    bridged.append(min(float(r[4]) for r in rows))
fig3 = go.Figure()
fig3.add_bar(x=["In-process DXVK", "BrokerBridge"], y=[5.4, statistics.median(bridged)],
             marker=dict(color=[ORANGE, BLUE], line=dict(width=0)), width=0.45,
             text=["5.4 MB", f"{statistics.median(bridged):.0f} MB (min {min(bridged):.0f}, max {max(bridged):.0f}, 5 sessions)"],
             textposition="outside", textfont=dict(color=INK),
             hovertemplate="%{x}<br>largest free region %{y:.0f} MB<extra></extra>")
fig3.update_layout(title="Figure 3. Largest contiguous free region in the game's address space, view and detail distance 100",
                   yaxis_title="largest free region (MB), higher is better", showlegend=False)
fig3.update_yaxes(range=[0, 1000])
figs.append(save(fig3, "fig3_address_space"))

# ---------------------------------------------------------------- Figure 4: content and effects ladder
ladder = [
    ("Baseline, no texture packs", "20260906_154131"),
    ("+ hi-res shadows, AO16, refl MSAA, ReShade w/ SSR", "20260906_185647"),
    ("Texture packs + effects, first configuration", "20260906_224244"),
    ("Effects trimmed, 4 GB VRAM report", "20260906_224827"),
    ("ReShade disabled", "20260906_225310"),
    ("Sharp shadow filter instead of CHSS", "20260906_230235"),
]
names = [n for n, _ in ladder]; st = [stats(frames(s)) for _, s in ladder]
fig4 = go.Figure()
fig4.add_bar(y=names[::-1], x=[m for m, _ in st][::-1], orientation="h", marker=dict(color=BLUE, line=dict(width=0)), width=0.55,
             text=[f"{m:.1f} ms  |  1% low {lo:.0f} fps" for m, lo in st][::-1], textposition="outside", textfont=dict(color=INK),
             hovertemplate="%{y}<br>mean %{x:.2f} ms<extra></extra>", name="Mean frame time")
fig4.add_vline(x=16.67, line=dict(color=INK2, width=1, dash="dot"), annotation_text="60 fps", annotation_position="top", annotation_font_color=INK2)
fig4.update_layout(title="Figure 4. Cost of the content and post-processing stack on the bridge (mean over the route, uncapped)",
                   xaxis_title="mean frame time (ms), lower is better", showlegend=False, margin=dict(l=330, r=140, t=72, b=56))
fig4.update_xaxes(range=[0, 30])
figs.append(save(fig4, "fig4_content_ladder"))

# ---------------------------------------------------------------- Figure 5: GPU utilisation over a route
rows = [r for r in csv.reader(open(os.path.join(SCRATCH, "gpu_full2.csv"))) if len(r) >= 2]
t0 = None; xs, ys = [], []
from datetime import datetime
for r in rows:
    ts = datetime.strptime(r[0].strip()[:23], "%Y/%m/%d %H:%M:%S.%f"); u = int(r[1].strip().split()[0])
    t0 = t0 or ts; xs.append((ts - t0).total_seconds()); ys.append(u)
fig5 = go.Figure()
fig5.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=BLUE, width=2), name="GPU utilisation",
                 hovertemplate="t=%{x:.0f} s<br>GPU %{y}%<extra></extra>")
fig5.add_vrect(x0=97, x1=162, fillcolor=BLUE, opacity=0.06, line_width=0,
               annotation_text="scripted route (60 s)", annotation_position="top left", annotation_font_color=INK2)
fig5.update_layout(title="Figure 5. GPU utilisation through one bench session: load, scripted route, then idle in the menu (nvidia-smi, 2 s samples)",
                   xaxis_title="seconds since launch", yaxis_title="GPU utilisation (%)", showlegend=False, hovermode="x unified")
fig5.update_yaxes(range=[0, 105])
figs.append(save(fig5, "fig5_gpu_util"))

# ---------------------------------------------------------------- HTML page with all figures
html = ["<!doctype html><html><head><meta charset='utf-8'><title>BrokerBridge figures</title>",
        "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>",
        f"<style>body{{background:{SURFACE};color:{INK};font-family:Inter,Segoe UI,Arial,sans-serif;max-width:1120px;margin:24px auto;padding:0 16px}}",
        f"p{{color:{INK2};line-height:1.5}} .fig{{margin:28px 0}}</style></head><body>",
        "<h1>BrokerBridge: measurements</h1>",
        "<p>Reference system: Intel i7-9700K, NVIDIA GeForce RTX 2070 (8 GB), driver 610.74, 2560x1440 borderless, "
        "GTA IV CE 1.2.0.59 with FusionFix. Frame times are means over a fixed 60-second scripted drive, uncapped. "
        "One machine, one vendor; see the README's Limitations section.</p>"]
for i, f in enumerate(figs, 1):
    html.append(f"<div class='fig'>{pio.to_html(f, include_plotlyjs=False, full_html=False, config={'displaylogo': False})}</div>")
html.append("</body></html>")
open(os.path.join(os.path.dirname(OUT), "figures.html"), "w", encoding="utf-8").write("\n".join(html))
print("wrote", len(figs), "figures to", OUT)
