"""PR-style figure set for b-bridge (dark theme, 3D where three variables exist) plus the
architecture diagram used as the Nexus thumbnail and header.

Outputs docs/figures_pr/*.png and docs/figures_pr.html.   python docs/make_figures_pr.py
"""
import csv, glob, os, statistics
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

RUNS = r"H:\Steam\steamapps\common\Grand Theft Auto IV\GTAIV\_runs"
SCRATCH = r"C:\Users\Bash\AppData\Local\Temp\claude\H--Steam-steamapps-common-Grand-Theft-Auto-IV\13ee3bb3-b580-42af-aa5b-18f115dcb91a\scratchpad"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures_pr"); os.makedirs(OUT, exist_ok=True)

# dark-mode slots of the validated palette (surface #1a1a19)
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
SURFACE, PANEL, INK, INK2, GRID = "#1a1a19", "#22221f", "#ffffff", "#c3c2b7", "#33332f"
FONT = "Inter, Segoe UI, Arial, sans-serif"

def base_layout(title, sub=None, h=1240):
    t = f"<b>{title}</b>" + (f"<br><span style='font-size:15px;color:{INK2}'>{sub}</span>" if sub else "")
    return dict(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font=dict(family=FONT, size=14, color=INK),
                title=dict(text=t, x=0.03, y=0.96, xanchor="left", font=dict(size=24)),
                margin=dict(l=70, r=40, t=120, b=70), legend=dict(orientation="h", y=-0.14, x=0, font=dict(color=INK2)))

AX2D = dict(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=INK2), title_font=dict(color=INK2))
AX3D = dict(backgroundcolor=PANEL, gridcolor=GRID, showbackground=True, zerolinecolor=GRID,
            tickfont=dict(color=INK2, size=11), title_font=dict(color=INK2, size=13))

def save(fig, name, w=2200, h=1240):
    fig.write_image(os.path.join(OUT, name + ".png"), width=w, height=h, scale=1)
    return fig

def frames(stamp):
    p = sorted(glob.glob(os.path.join(RUNS, f"benchroute_{stamp}*.csv")))[0]
    return [float(r[1]) for r in csv.reader(open(p)) if r and r[0].isdigit()]

def stats(ms):
    s = sorted(ms, reverse=True); k = max(1, len(ms) // 100)
    return statistics.mean(ms), 1000.0 / statistics.mean(s[:k])

def addr(stamp):
    p = sorted(glob.glob(os.path.join(RUNS, f"addrspace_{stamp}*.csv")))[0]
    rows = [r for r in csv.reader(open(p)) if r and not r[0].startswith("#") and r[0] != "elapsed_s" and len(r) > 4]
    return [float(r[0]) for r in rows], [float(r[1]) for r in rows], [float(r[4]) for r in rows]

figs = []

# ------------------------------------------------------------------ 1. Architecture diagram (thumbnail + header)
def architecture(w, h, header=False):
    fig = go.Figure()
    fig.update_xaxes(visible=False, range=[0, 100]); fig.update_yaxes(visible=False, range=[0, 100 * h / w] if False else [0, 56.25])
    def box(x0, y0, x1, y1, fill, line, r=2.2):
        # rounded rectangle path
        path = (f"M{x0+r},{y0} L{x1-r},{y0} Q{x1},{y0} {x1},{y0+r} L{x1},{y1-r} Q{x1},{y1} {x1-r},{y1} "
                f"L{x0+r},{y1} Q{x0},{y1} {x0},{y1-r} L{x0},{y0+r} Q{x0},{y0} {x0+r},{y0} Z")
        fig.add_shape(type="path", path=path, fillcolor=fill, line=dict(color=line, width=2), layer="below")
    def text(x, y, s, size=16, color=INK, anchor="center", bold=False):
        fig.add_annotation(x=x, y=y, text=(f"<b>{s}</b>" if bold else s), showarrow=False, font=dict(size=size, color=color, family=FONT), xanchor=anchor, align="left" if anchor == "left" else "center")
    def arrow(x0, y0, x1, y1, color, width=4):
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=width, arrowcolor=color, text="")
    S = 1.0 if not header else 0.62   # font scale for the short header
    # left process: game
    box(4, 8, 38, 50, "#20242c", "#3a4250")
    text(21, 46.5, "GTAIV.exe", 26 * S, INK, bold=True); text(21, 43.2, "32-bit  ·  4 GB address space", 14 * S, INK2)
    box(7, 27, 35, 40, "#1c2b40", BLUE); text(21, 36.5, "game, scripts, streaming", 14 * S, INK2); text(21, 31.5, "b-bridge client  d3d9.dll", 18 * S, "#8fbcf3", bold=True)
    box(7, 11, 35, 24, "#2a2320", "#5a4a3a"); text(21, 20.5, "textures · shadow maps · render targets", 13 * S, INK2)
    text(21, 15.5, "no longer live here", 15 * S, ORANGE, bold=True)
    # channel
    box(40, 24, 58, 38, "#1e2a22", AQUA)
    text(49, 34, "shared-memory", 15 * S, "#7fd6b3", bold=True); text(49, 30.5, "command channel", 15 * S, "#7fd6b3", bold=True)
    text(49, 26.6, "StateBatch · batched publish · frame pacer", 11 * S, INK2)
    arrow(38.5, 33, 40.5, 33, AQUA, 3); arrow(57.5, 29, 59.5, 29, AQUA, 3)
    # right process: server
    box(60, 8, 96, 50, "#20242c", "#3a4250")
    text(78, 46.5, "NvRemixBridge.exe", 26 * S, INK, bold=True); text(78, 43.2, "64-bit  ·  b-bridge server", 14 * S, INK2)
    box(63, 27, 93, 40, "#1c2b40", BLUE); text(78, 36.5, "command replay", 14 * S, INK2); text(78, 31.5, "DXVK 3.0.2  →  Vulkan  →  GPU", 18 * S, "#8fbcf3", bold=True)
    box(63, 11, 93, 24, "#1e2a22", AQUA); text(78, 20.5, "textures · shadow maps · render targets", 13 * S, INK2)
    text(78, 15.5, "live here now (64-bit)", 15 * S, "#7fd6b3", bold=True)
    # footer strip
    text(50, 4.2, "b-bridge  ·  out-of-process Direct3D 9 for GTA IV: The Complete Edition  ·  ~880 MB of address space returned to the game", 14 * S, INK2)
    fig.update_layout(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      title=None, xaxis=dict(range=[0, 100], fixedrange=True), yaxis=dict(range=[0, 56.25], fixedrange=True, scaleanchor="x", scaleratio=1))
    return fig

arch = architecture(1920, 1080); arch.update_layout(title=dict(text="<b>b-bridge</b>  <span style='font-size:22px;color:#c3c2b7'>architecture</span>", x=0.03, y=0.955, font=dict(size=34, color=INK)), margin=dict(t=90))
arch.write_image(os.path.join(OUT, "arch_thumbnail.png"), width=1920, height=1080, scale=1)
archh = architecture(1300, 372, header=True)
archh.update_yaxes(range=[6, 52]); archh.update_layout(margin=dict(t=0, b=0))
archh.write_image(os.path.join(OUT, "arch_header.png"), width=1300, height=372, scale=1)
figs.append(("Architecture", arch))

# ------------------------------------------------------------------ 2. 3D ridge: frame-time distributions per stage
stages = [("In-process DXVK", ["20260904_0101", "20260904_0105", "20260904_0110", "20260904_0114", "20260904_0221", "20260904_0350"], ORANGE),
          ("Bridge, upstream client", ["20260905_0240", "20260905_0246", "20260905_0250", "20260905_0254", "20260905_0259"], YELLOW),
          ("Bridge, transfer plans", ["20260905_0315", "20260905_0319", "20260905_0327", "20260905_0334"], AQUA),
          ("Bridge, final client", ["20260905_0441", "20260905_0459", "20260905_0504", "20260905_0508", "20260905_0353"], BLUE)]
fig = go.Figure(); bins = np.linspace(5, 40, 71); centers = (bins[:-1] + bins[1:]) / 2
for i, (name, stamps, col) in enumerate(stages):
    allms = sum((frames(s) for s in stamps), []); hist, _ = np.histogram(allms, bins=bins, density=True)
    y = np.full_like(centers, i)
    fig.add_scatter3d(x=centers, y=y, z=hist, mode="lines", line=dict(color=col, width=6), name=name,
                      hovertemplate=name + "<br>%{x:.1f} ms<br>density %{z:.3f}<extra></extra>")
    # filled ridge via mesh (curtain to z=0)
    xs = np.concatenate([centers, centers[::-1]]); ys = np.concatenate([y, y]); zs = np.concatenate([hist, np.zeros_like(hist)])
    n = len(centers); I, J, K = [], [], []
    for k in range(n - 1):
        I += [k, k]; J += [k + 1, 2 * n - 1 - k]; K += [2 * n - 1 - k, 2 * n - 2 - k]
    fig.add_mesh3d(x=xs, y=ys, z=zs, i=I, j=J, k=K, color=col, opacity=0.35, showlegend=False, hoverinfo="skip")
m = max(stats(sum((frames(s) for s in st[1]), []))[0] for st in stages)
fig.add_scatter3d(x=[16.67, 16.67], y=[-0.3, 3.3], z=[0, 0], mode="lines", line=dict(color=INK2, width=4, dash="dot"), name="60 fps (16.7 ms)")
fig.update_layout(**base_layout("Frame-time distribution by client stage", "Density of per-frame times over the same 60 s route, every run per stage pooled. Uncapped, RTX 2070, 1440p."))
fig.update_layout(scene=dict(xaxis=dict(title="frame time (ms)", **AX3D), yaxis=dict(title="", tickvals=[0, 1, 2, 3], ticktext=[s[0] for s in stages], **AX3D),
                             zaxis=dict(title="density", **AX3D), camera=dict(eye=dict(x=1.35, y=-1.25, z=0.55), center=dict(x=0, y=0, z=-0.15)), aspectratio=dict(x=1.8, y=1.2, z=0.6), bgcolor=SURFACE, domain=dict(x=[0, 1], y=[0, 0.92])))
figs.append(("Frame-time ridges", save(fig, "pr1_ridges_3d")))

# ------------------------------------------------------------------ 3. 3D terrain: address space through a session (in-process vs bridged)
fig = go.Figure()
for name, stamp, col, yoff in [("In-process DXVK, 2026-09-04 (52 min)", "20260904_0224", ORANGE, 0), ("b-bridge, 2026-09-06 (22 min)", "20260906_2215", BLUE, 1)]:
    t, c, f = addr(stamp); t = np.array(t) / 60
    fig.add_scatter3d(x=t, y=np.full_like(t, yoff), z=f, mode="lines", line=dict(color=col, width=6), name=name + ", largest free region",
                      hovertemplate=name + "<br>t=%{x:.1f} min<br>largest free %{z:.0f} MB<extra></extra>")
    fig.add_scatter3d(x=t, y=np.full_like(t, yoff + 0.35), z=c, mode="lines", line=dict(color=col, width=3, dash="dot"), name=name + ", committed",
                      hovertemplate=name + "<br>t=%{x:.1f} min<br>committed %{z:.0f} MB<extra></extra>", opacity=0.7)
fig.add_scatter3d(x=[0, 55], y=[-0.2, -0.2], z=[4096, 4096], mode="lines", line=dict(color=INK2, width=3, dash="dash"), name="4 GB wall")
fig.update_layout(**base_layout("Address space through a session", "Committed bytes and the largest contiguous free region in GTAIV.exe, sampled every 500 ms. View distance 70 (in-process) and 100 (bridged)."))
fig.update_layout(scene=dict(xaxis=dict(title="minutes", **AX3D), yaxis=dict(title="", tickvals=[0, 1], ticktext=["in-process", "b-bridge"], range=[-0.4, 1.7], **AX3D),
                             zaxis=dict(title="MB", range=[0, 4300], **AX3D), camera=dict(eye=dict(x=1.25, y=-1.35, z=0.5), center=dict(x=0, y=0, z=-0.1)), aspectratio=dict(x=2.0, y=0.8, z=0.8), bgcolor=SURFACE, domain=dict(x=[0, 1], y=[0, 0.92])))
figs.append(("Address space terrain", save(fig, "pr2_address_space_3d")))

# ------------------------------------------------------------------ 4. 3D scatter: every bench run, three metrics
groups = [("In-process DXVK", [f"20260904_{s}" for s in ["0101", "0105", "0110", "0114", "0221", "0350"]], "20260904_0224", ORANGE),
          ("Bridge, upstream client", [f"20260905_{s}" for s in ["0240", "0246", "0250", "0254", "0259"]], "20260905_0238", YELLOW),
          ("Bridge, final client", [f"20260905_{s}" for s in ["0441", "0459", "0504", "0508", "0353"]], "20260905_0439", BLUE),
          ("Final client + 5 GB texture packs", [f"20260906_{s}" for s in ["2242", "2248", "2253", "2257", "2302"]], "20260906_2246", AQUA)]
fig = go.Figure()
for name, stamps, astamp, col in groups:
    _, _, free = addr(astamp); mf = min(free)
    pts = [stats(frames(s)) for s in stamps]
    fig.add_scatter3d(x=[p[0] for p in pts], y=[p[1] for p in pts], z=[mf] * len(pts), mode="markers", name=name,
                      marker=dict(size=9, color=col, opacity=0.95, line=dict(color=INK, width=1)),
                      hovertemplate=name + "<br>mean %{x:.2f} ms<br>1%% low %{y:.1f} fps<br>largest free %{z:.0f} MB<extra></extra>")
fig.update_layout(**base_layout("Every bench run in three dimensions", "Mean frame time, 1% low, and the session's minimum largest-free region. One point per 60 s route run."))
fig.update_layout(scene=dict(xaxis=dict(title="mean frame time (ms)", **AX3D), yaxis=dict(title="1% low (fps)", **AX3D), zaxis=dict(title="largest free region (MB)", **AX3D),
                             camera=dict(eye=dict(x=1.3, y=1.15, z=0.6), center=dict(x=0, y=0, z=-0.1)), bgcolor=SURFACE, domain=dict(x=[0, 1], y=[0, 0.92])))
figs.append(("Run scatter", save(fig, "pr3_runs_3d")))

# ------------------------------------------------------------------ 5. Stage bars, dark PR style with gradient + 1% low secondary panel
labels, means, lows = [], [], []
for name, stamps, col in stages:
    pts = [stats(frames(s)) for s in stamps]; labels.append(name); means.append(statistics.mean(p[0] for p in pts)); lows.append(statistics.mean(p[1] for p in pts))
fig = go.Figure()
fig.add_bar(x=labels, y=means, marker=dict(color=[ORANGE, BLUE, BLUE, BLUE], line=dict(width=0)), width=0.55,
            text=[f"<b>{m:.1f} ms</b><br><span style='color:{INK2}'>1% low {lo:.0f} fps</span>" for m, lo in zip(means, lows)], textposition="outside", textfont=dict(size=15),
            hovertemplate="%{x}<br>mean %{y:.2f} ms<extra></extra>", showlegend=False)
fig.add_hline(y=16.67, line=dict(color=INK2, width=1.5, dash="dot"), annotation_text="60 fps", annotation_position="top right", annotation_font_color=INK2)
fig.update_layout(**base_layout("Mean frame time per client stage", "Same 60 s route, uncapped. Orange: in-process DXVK. Blue: b-bridge client stages."))
fig.update_xaxes(**AX2D); fig.update_yaxes(title="mean frame time (ms)", range=[0, 27], **AX2D)
figs.append(("Stage bars", save(fig, "pr4_stage_bars")))

# ------------------------------------------------------------------ 6. GPU utilisation with the route shaded, area fill
rows = [r for r in csv.reader(open(os.path.join(SCRATCH, "gpu_full2.csv"))) if len(r) >= 2]
t0 = None; xs, ys = [], []
for r in rows:
    ts = datetime.strptime(r[0].strip()[:23], "%Y/%m/%d %H:%M:%S.%f"); t0 = t0 or ts; xs.append((ts - t0).total_seconds()); ys.append(int(r[1].strip().split()[0]))
fig = go.Figure()
fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=BLUE, width=3, shape="spline", smoothing=0.6), fill="tozeroy", fillcolor="rgba(57,135,229,0.18)", name="GPU utilisation",
                hovertemplate="t=%{x:.0f} s<br>GPU %{y}%<extra></extra>")
fig.add_vrect(x0=97, x1=162, fillcolor=AQUA, opacity=0.12, line_width=0, annotation_text="scripted route", annotation_position="top left", annotation_font_color="#7fd6b3")
fig.update_layout(**base_layout("GPU utilisation through a bench session", "Load, the 60 s scripted route, then idle in the menu. Full content stack. nvidia-smi, 2 s samples."))
fig.update_layout(hovermode="x unified", showlegend=False); fig.update_xaxes(title="seconds since launch", **AX2D); fig.update_yaxes(title="GPU %", range=[0, 105], **AX2D)
figs.append(("GPU", save(fig, "pr5_gpu_area")))

# ------------------------------------------------------------------ HTML gallery
html = ["<!doctype html><html><head><meta charset='utf-8'><title>b-bridge figures (PR set)</title>",
        "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>",
        f"<style>body{{background:{SURFACE};color:{INK};font-family:{FONT};max-width:1200px;margin:24px auto;padding:0 16px}} .fig{{margin:28px 0}} h1{{font-weight:700}} p{{color:{INK2}}}</style></head><body>",
        "<h1>b-bridge: measurements, interactive</h1><p>Drag to rotate the 3D figures. Reference system: i7-9700K, RTX 2070, 2560x1440, GTA IV CE 1.2.0.59 + FusionFix. One machine, one vendor; see the README Limitations.</p>"]
for name, f in figs:
    html.append(f"<div class='fig'>{pio.to_html(f, include_plotlyjs=False, full_html=False, config={'displaylogo': False})}</div>")
html.append("</body></html>")
open(os.path.join(HERE, "figures_pr.html"), "w", encoding="utf-8").write("\n".join(html))
print("wrote", len(figs), "figures + arch_thumbnail/arch_header to", OUT)
