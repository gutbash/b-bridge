"""b-bridge explainer animation (Manim Community).

Render:  manim -qh docs/video/explainer.py Explainer      (1080p60)
Quick:   manim -ql docs/video/explainer.py Explainer      (480p15)
No LaTeX is used (Text only), so a TeX install is not required.
"""
from manim import *

# validated dark palette
BG, PANEL, INK, INK2, GRID = "#1a1a19", "#22221f", "#ffffff", "#c3c2b7", "#33332f"
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
FONT = "Segoe UI"

config.background_color = BG


def T(s, size=36, color=INK, weight=NORMAL):
    return Text(s, font=FONT, font_size=size, color=color, weight=weight)


def rbox(w, h, stroke, fill=PANEL, r=0.25):
    return RoundedRectangle(width=w, height=h, corner_radius=r, stroke_color=stroke, stroke_width=3, fill_color=fill, fill_opacity=1)


class Explainer(Scene):
    def construct(self):
        self.title()
        self.problem()
        self.idea()
        self.channel()
        self.results()
        self.limits()
        self.outro()

    # ------------------------------------------------------------ 1. title
    def title(self):
        t = T("b-bridge", 96, INK, BOLD)
        s = T("out-of-process Direct3D 9 for GTA IV: The Complete Edition", 30, INK2)
        s.next_to(t, DOWN, buff=0.4)
        line = Line(LEFT * 3, RIGHT * 3, color=AQUA, stroke_width=4).next_to(s, DOWN, buff=0.5)
        self.play(Write(t), run_time=1.2)
        self.play(FadeIn(s, shift=UP * 0.2), Create(line), run_time=1.0)
        self.wait(1.6)
        self.play(FadeOut(VGroup(t, s, line)), run_time=0.6)

    # ------------------------------------------------------------ 2. the problem: the 4 GB wall
    def problem(self):
        h = T("The problem", 44, INK, BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(h, shift=DOWN * 0.2))
        # address-space bar
        bar_w, bar_h = 10.0, 1.1
        frame = Rectangle(width=bar_w, height=bar_h, stroke_color=INK2, stroke_width=3).shift(UP * 0.9)
        lab = T("GTAIV.exe address space: 4 GB, and it is 32-bit, so that is all there is", 24, INK2).next_to(frame, UP, buff=0.3)
        self.play(Create(frame), FadeIn(lab))

        segs = [("game code + data", 0.22, "#3a4250"), ("streamed models", 0.20, BLUE), ("scripts, pools", 0.10, "#4a3aa7"),
                ("driver: textures", 0.22, ORANGE), ("shadow maps, RTs", 0.12, "#e34948"), ("staging", 0.06, YELLOW)]
        x = frame.get_left()[0]
        rects, labels = VGroup(), VGroup()
        for name, frac, col in segs:
            w = bar_w * frac
            r = Rectangle(width=w, height=bar_h - 0.12, stroke_width=0, fill_color=col, fill_opacity=0.95)
            r.move_to([x + w / 2, frame.get_center()[1], 0]); x += w
            rects.add(r)
        for i, (name, frac, col) in enumerate(segs):
            sw = Square(side_length=0.22, stroke_width=0, fill_color=col, fill_opacity=1)
            labels.add(VGroup(sw, T(name, 18, INK2)).arrange(RIGHT, buff=0.12))
        labels.arrange_in_grid(rows=2, cols=3, buff=(0.6, 0.15), cell_alignment=LEFT).next_to(frame, DOWN, buff=0.3)
        # game parts first
        self.play(*[GrowFromEdge(rects[i], LEFT) for i in range(3)], *[FadeIn(labels[i]) for i in range(3)], run_time=1.2)
        note1 = T("the game's own memory", 22, INK2).next_to(labels, DOWN, buff=0.4)
        self.play(FadeIn(note1))
        self.wait(0.6)
        # driver parts fill in the same space
        self.play(*[GrowFromEdge(rects[i], LEFT) for i in range(3, 6)], *[FadeIn(labels[i]) for i in range(3, 6)], run_time=1.4)
        note2 = T("and everything the graphics driver allocates on its behalf", 22, ORANGE).next_to(note1, DOWN, buff=0.15)
        self.play(FadeIn(note2))
        self.wait(0.8)
        gap = Rectangle(width=bar_w * 0.08, height=bar_h - 0.12, stroke_width=0, fill_color="#e34948", fill_opacity=0.95)
        gap.move_to([x + bar_w * 0.04, frame.get_center()[1], 0])
        free = T("what is left: a 5 MB hole", 26, "#e34948", BOLD).next_to(note2, DOWN, buff=0.3)
        self.play(GrowFromEdge(gap, LEFT), Write(free))
        self.wait(0.8)
        wall = T("More RAM does not help. More VRAM does not help.\nThe wall is the 32-bit address space.", 26, INK).next_to(free, DOWN, buff=0.35)
        self.play(FadeIn(wall, shift=UP * 0.2))
        self.wait(2.2)
        self.play(FadeOut(VGroup(h, frame, lab, rects, labels, note1, note2, gap, free, wall)), run_time=0.6)

    # ------------------------------------------------------------ 3. the idea: two processes
    def idea(self):
        h = T("The idea", 44, INK, BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(h, shift=DOWN * 0.2))
        # game box
        game = rbox(4.6, 4.4, "#3a4250").shift(LEFT * 4.0 + DOWN * 0.3)
        gt = T("GTAIV.exe", 34, INK, BOLD).move_to(game.get_top() + DOWN * 0.5)
        gs = T("32-bit", 20, INK2).next_to(gt, DOWN, buff=0.1)
        inner = rbox(4.0, 1.2, BLUE, "#1c2b40").move_to(game.get_center() + UP * 0.2)
        it = T("game, scripts, streaming", 20, INK2).move_to(inner)
        drv = rbox(4.0, 1.2, ORANGE, "#2a2320").move_to(game.get_center() + DOWN * 1.2)
        dt = T("driver resources", 20, INK2).move_to(drv)
        self.play(FadeIn(game), FadeIn(gt), FadeIn(gs), FadeIn(inner), FadeIn(it), FadeIn(drv), FadeIn(dt), run_time=1.0)
        self.wait(0.6)
        say = T("Move the whole Direct3D 9 device out of the process.", 30, INK).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(say, shift=UP * 0.2))
        # server box appears, driver block flies across
        srv = rbox(4.6, 4.4, "#3a4250").shift(RIGHT * 4.0 + DOWN * 0.3)
        st = T("NvRemixBridge.exe", 34, INK, BOLD).move_to(srv.get_top() + DOWN * 0.5)
        ss = T("64-bit  ·  b-bridge server", 20, INK2).next_to(st, DOWN, buff=0.1)
        dx = rbox(4.0, 1.2, BLUE, "#1c2b40").move_to(srv.get_center() + UP * 0.2)
        dxt = T("DXVK 3.0.2 → Vulkan → GPU", 20, "#8fbcf3", BOLD).move_to(dx)
        self.play(FadeIn(srv), FadeIn(st), FadeIn(ss), run_time=0.8)
        # keep the moving block above both process boxes while it crosses
        drv.set_z_index(5); dt.set_z_index(6)
        target = drv.copy().set_stroke(AQUA).set_fill("#1e2a22").move_to(srv.get_center() + DOWN * 1.2)
        tt = T("driver resources, 64-bit", 20, "#7fd6b3").move_to(target).set_z_index(6)
        path = ArcBetweenPoints(drv.get_center(), target.get_center(), angle=-PI / 3)
        self.play(MoveAlongPath(drv, path), MoveAlongPath(dt, path), run_time=1.4, rate_func=smooth)
        self.play(Transform(drv, target), Transform(dt, tt), run_time=0.5)
        self.play(FadeIn(dx), FadeIn(dxt))
        # client label replaces the freed space in the game
        client = rbox(4.0, 1.2, AQUA, "#1e2a22").move_to(game.get_center() + DOWN * 1.2)
        ct = T("thin client: d3d9.dll", 20, "#7fd6b3", BOLD).move_to(client)
        self.play(FadeIn(client), FadeIn(ct))
        arrow = Arrow(game.get_right(), srv.get_left(), buff=0.15, color=AQUA, stroke_width=6, max_tip_length_to_length_ratio=0.12)
        al = T("shared-memory\nchannel", 18, "#7fd6b3").next_to(arrow, UP, buff=0.15)
        self.play(GrowArrow(arrow), FadeIn(al))
        self.wait(0.8)
        say2 = T("The game keeps a thin d3d9.dll. Every call crosses to a 64-bit process\nthat renders through DXVK on Vulkan.", 24, INK).to_edge(DOWN, buff=0.5)
        self.play(Transform(say, say2))
        self.wait(2.2)
        gain = T("~880 MB of address space returned to the game", 30, AQUA, BOLD).to_edge(DOWN, buff=0.7)
        self.play(Transform(say, gain))
        self.wait(1.8)
        self.play(FadeOut(VGroup(h, game, gt, gs, inner, it, drv, dt, srv, st, ss, dx, dxt, client, ct, arrow, al, say)), run_time=0.6)

    # ------------------------------------------------------------ 4. why it is not slow: batching
    def channel(self):
        h = T("Why it is not slow", 44, INK, BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(h, shift=DOWN * 0.2))
        intro = T("GTA IV issues 15,000 to 70,000 D3D9 calls per frame.\nOne message per call across a process boundary would cost more than the frame.", 22, INK2).next_to(h, DOWN, buff=0.35)
        self.play(FadeIn(intro))
        left = T("GTAIV.exe", 24, INK2).shift(LEFT * 5.3 + UP * 0.3)
        right = T("server", 24, INK2).shift(RIGHT * 5.1 + UP * 0.3)
        lane = Line(LEFT * 4.2, RIGHT * 4.2, color=GRID, stroke_width=2).shift(UP * 0.3)
        self.play(FadeIn(left), FadeIn(right), Create(lane))
        # upstream: many small dots
        dots = VGroup(*[Dot(radius=0.07, color=ORANGE).move_to(LEFT * 4.0 + RIGHT * (i * 0.35) + UP * 0.3) for i in range(24)])
        cap1 = T("upstream: one message per call", 22, ORANGE).next_to(lane, DOWN, buff=0.25)
        self.play(LaggedStart(*[FadeIn(d, shift=RIGHT * 0.3) for d in dots], lag_ratio=0.05), FadeIn(cap1), run_time=1.6)
        self.wait(0.8)
        # b-bridge: StateBatch record
        lane2 = Line(LEFT * 4.2, RIGHT * 4.2, color=GRID, stroke_width=2).shift(DOWN * 1.3)
        rec = RoundedRectangle(width=2.6, height=0.6, corner_radius=0.15, stroke_color=BLUE, stroke_width=3, fill_color="#1c2b40", fill_opacity=1).move_to(LEFT * 2.9 + DOWN * 1.3)
        rt = T("StateBatch record", 18, "#8fbcf3").move_to(rec)
        rec2 = rec.copy().shift(RIGHT * 3.0); rt2 = T("index batch", 18, "#8fbcf3").move_to(rec2)
        cap2 = T("b-bridge: hot state packed into one record per flush,\nindices published in batches, frames paced in the game", 20, BLUE).next_to(lane2, DOWN, buff=0.6)
        self.play(Create(lane2), FadeIn(rec), FadeIn(rt), FadeIn(rec2), FadeIn(rt2), FadeIn(cap2), run_time=1.2)
        self.play(rec.animate.shift(RIGHT * 6.4), rt.animate.shift(RIGHT * 6.4), rec2.animate.shift(RIGHT * 0.4), rt2.animate.shift(RIGHT * 0.4), run_time=1.2)
        self.wait(0.6)
        list_ = VGroup(T("• state-block transfer plans for the block GTA IV applies ~475× per frame", 20, INK2),
                       T("• merged device/channel lock, import-free spinlock", 20, INK2),
                       T("• server replies only when a call returns data", 20, INK2)).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(list_, shift=UP * 0.2))
        self.wait(2.4)
        self.play(FadeOut(VGroup(h, intro, left, right, lane, dots, cap1, lane2, rec, rt, rec2, rt2, cap2, list_)), run_time=0.6)

    # ------------------------------------------------------------ 5. results
    def results(self):
        h = T("Measured", 44, INK, BOLD).to_edge(UP, buff=0.6)
        sub = T("same 60 s scripted drive, uncapped · RTX 2070 · 2560×1440 · GTA IV CE 1.2.0.59 + FusionFix", 20, INK2).next_to(h, DOWN, buff=0.2)
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(sub))
        data = [("in-process DXVK", 16.9, ORANGE), ("bridge, upstream client", 22.4, YELLOW), ("bridge, transfer plans", 18.6, AQUA), ("bridge, final client", 13.6, BLUE)]
        base_y = -2.4; scale = 0.16; xs = [-4.5, -1.5, 1.5, 4.5]
        axis = Line(LEFT * 6.2, RIGHT * 6.2, color=GRID).shift(UP * base_y)
        sixty = DashedLine(LEFT * 6.2, RIGHT * 6.2, color=INK2, dash_length=0.12).shift(UP * (base_y + 16.67 * scale))
        sl = T("60 fps (16.7 ms)", 18, INK2).next_to(sixty, UP, buff=0.05).align_to(sixty, RIGHT)
        self.play(Create(axis), Create(sixty), FadeIn(sl))
        bars = VGroup()
        for (name, ms, col), x in zip(data, xs):
            b = Rectangle(width=1.8, height=ms * scale, stroke_width=0, fill_color=col, fill_opacity=0.95)
            b.move_to([x, base_y + ms * scale / 2, 0])
            v = T(f"{ms:.1f} ms", 24, INK, BOLD).next_to(b, UP, buff=0.12)
            n = T(name, 17, INK2).next_to(b, DOWN, buff=0.15)
            bars.add(VGroup(b, v, n))
        for g in bars:
            self.play(GrowFromEdge(g[0], DOWN), FadeIn(g[1]), FadeIn(g[2]), run_time=0.7)
        self.wait(0.8)
        msg = T("Below in-process DXVK on the same route, and 5 MB became ~800 MB of free address space.", 24, INK).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(msg, shift=UP * 0.2))
        self.wait(2.6)
        self.play(FadeOut(VGroup(h, sub, axis, sixty, sl, bars, msg)), run_time=0.6)

    # ------------------------------------------------------------ 6. limits
    def limits(self):
        h = T("What it is not", 44, INK, BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(h, shift=DOWN * 0.2))
        items = [("Not path tracing.", "Raster only; GTA IV's deferred renderer does not work with Remix's ray-traced path."),
                 ("Not a CPU fix.", "Calls still cross the boundary. The win is address space; frame time is held at parity."),
                 ("Tested on one machine.", "One RTX 2070, one driver, one resolution. No AMD or Intel run yet."),
                 ("Startup desync, ~1 in 10.", "The server does not come up; relaunch. Not yet isolated.")]
        g = VGroup()
        for a, b in items:
            row = VGroup(T(a, 28, ORANGE, BOLD), T(b, 22, INK2)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            g.add(row)
        g.arrange(DOWN, aligned_edge=LEFT, buff=0.42).next_to(h, DOWN, buff=0.6).to_edge(LEFT, buff=1.0)
        for row in g:
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.6)
            self.wait(0.9)
        self.wait(1.2)
        self.play(FadeOut(VGroup(h, g)), run_time=0.6)

    # ------------------------------------------------------------ 7. outro
    def outro(self):
        t = T("b-bridge", 80, INK, BOLD)
        s = T("github.com/gutbash/b-bridge   ·   nexusmods.com/gta4/mods/1385", 26, INK2).next_to(t, DOWN, buff=0.4)
        c = T("MIT · fork of NVIDIA bridge-remix · DXVK by doitsujin", 20, INK2).next_to(s, DOWN, buff=0.3)
        self.play(Write(t), run_time=1.0)
        self.play(FadeIn(s), FadeIn(c))
        self.wait(3.0)
        self.play(FadeOut(VGroup(t, s, c)), run_time=0.8)
