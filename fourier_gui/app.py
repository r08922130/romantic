# -*- coding: utf-8 -*-
"""
app.py - Fourier Epicycles Christmas Tree (GUI, tkinter)
========================================================

    python fourier_gui/app.py                 (or double-click run_fourier.bat)
    python fourier_gui/app.py --terms 200 --seconds 15

Rotating circles (the terms of a complex Fourier series) are put head to
tail; the tip of the last one draws a Christmas tree. Then the circles fade,
the tree fills in, the star shines, the lights twinkle, presents drop, snow
falls and the greeting appears.

The coefficients come from the tree outline itself (fourier.py): the outline
is sampled evenly by arc length, transformed with a DFT once at start, and
every frame only adds up the rotating vectors.

Keys:  Space pause   R replay   C circles on/off   1-5 terms (20/50/100/200/all)
       Esc / Q quit
"""
import argparse
import cmath
import json
import math
import os
import random
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fourier as F                                 # noqa: E402

SAMPLES = 512
TERM_CHOICES = (20, 50, 100, 200, SAMPLES)
BG = "#0b1026"
GROUND = "#d8e2f0"

# timeline (seconds) - DRAW is set from the speed slider
APPEAR, HOLD, FADE = 1.2, 1.2, 1.6
FILL, LIGHTS, GIFTS, GREETING = 2.0, 3.0, 4.5, 6.0


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, a):
    """Colour c1 -> c2 by a (0..1): tkinter has no transparency, so fades are
    done by mixing towards the background colour."""
    a = 0.0 if a < 0 else (1.0 if a > 1 else a)
    r1, g1, b1 = hex_rgb(c1)
    r2, g2, b2 = hex_rgb(c2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * a), int(g1 + (g2 - g1) * a),
                              int(b1 + (b2 - b1) * a))


def point_in(poly, x, y):
    """Is (x, y) inside the polygon [(x, y), ...]? (ray casting)"""
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def load_greeting():
    """Use the Christmas greeting from the ASCII program's settings.json."""
    greeting, wish = "Merry Christmas, My Love!", "Every day with you feels like Christmas."
    path = os.path.join(os.path.dirname(HERE), "settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        x = data.get("scenes", {}).get("christmas", {})
        greeting, wish = x.get("greeting", greeting), x.get("wish", wish)
    except (OSError, ValueError):
        pass
    return greeting, wish


class Model:
    """The maths, independent of the window: samples, coefficients, the
    reconstructed curve for the chosen number of terms."""

    def __init__(self, terms=100):
        self.outline = F.tree_outline()
        self.samples = F.resample(self.outline, SAMPLES)
        self.coeffs = F.dft(self.samples)                  # computed ONCE
        self.order = "size"
        self.set_terms(terms)

    def set_terms(self, terms):
        self.terms = max(1, min(int(terms), len(self.coeffs)))
        kept = F.truncate(self.coeffs, self.terms)
        self.drawn = F.by_size(kept) if self.order == "size" else F.by_frequency(kept)
        self.error = F.max_error(kept, self.samples)
        self.curve = [F.evaluate(kept, k / 1200.0) for k in range(1201)]

    def set_order(self, order):
        self.order = order
        self.set_terms(self.terms)


class App:
    def __init__(self, root, terms=100, seconds=12.0, at=None):
        self.root = root
        self.model = Model(terms)
        self.greeting, self.wish = load_greeting()
        self.draw_secs = seconds
        self.show_circles = True
        self.paused = False
        self.time = at or 0.0
        self.last = time.perf_counter()
        self.rng = random.Random(7)
        root.title("Fourier Epicycles Christmas Tree")
        root.configure(bg=BG)
        self.build_controls()
        self.cv = tk.Canvas(root, bg=BG, highlightthickness=0, width=900, height=700)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.layout())
        for key, fn in (("<space>", self.toggle_pause), ("r", self.replay), ("R", self.replay),
                        ("c", self.toggle_circles), ("C", self.toggle_circles),
                        ("<Escape>", root.destroy), ("q", root.destroy)):
            root.bind(key, lambda e, f=fn: f())
        for i, n in enumerate(TERM_CHOICES):
            root.bind(str(i + 1), lambda e, n=n: self.choose_terms(n))
        self.scale, self.ox, self.oy = 1.0, 0.0, 0.0
        self.items = {}
        self.snow = []
        self.layout()
        self.tick()

    # ---------------- controls ----------------
    def build_controls(self):
        bar = tk.Frame(self.root, bg="#141a33")
        bar.pack(side="top", fill="x")
        style = dict(bg="#141a33", fg="#c9d4ee", activebackground="#24305a",
                     activeforeground="white", highlightthickness=0, bd=0)
        tk.Label(bar, text="傅立葉項數", **style).pack(side="left", padx=(10, 4), pady=6)
        self.term_buttons = {}
        for n in TERM_CHOICES:
            b = tk.Button(bar, text="全部" if n == SAMPLES else str(n), width=4,
                          command=lambda n=n: self.choose_terms(n), **style)
            b.pack(side="left", padx=2)
            self.term_buttons[n] = b
        tk.Label(bar, text="   速度", **style).pack(side="left")
        self.speed = tk.Scale(bar, from_=5, to=30, orient="horizontal", length=120,
                              showvalue=False, command=self.set_speed, bg=style["bg"],
                              troughcolor="#24305a", highlightthickness=0, bd=0)
        self.speed.set(self.draw_secs)
        self.speed.pack(side="left")
        self.order_var = tk.StringVar(value="size")
        for text, val in (("大圓在前", "size"), ("依頻率", "freq")):
            tk.Radiobutton(bar, text=text, value=val, variable=self.order_var,
                           command=self.set_order, selectcolor="#24305a", **style).pack(side="left")
        self.circles_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="顯示圓", variable=self.circles_var, selectcolor="#24305a",
                       command=lambda: self.set_circles(self.circles_var.get()),
                       **style).pack(side="left", padx=6)
        tk.Button(bar, text="暫停", width=5, command=self.toggle_pause, **style).pack(side="left", padx=2)
        tk.Button(bar, text="重播", width=5, command=self.replay, **style).pack(side="left", padx=2)
        self.info = tk.Label(bar, text="", **style)
        self.info.pack(side="right", padx=10)
        self.refresh_info()

    def refresh_info(self):
        m = self.model
        for n, b in self.term_buttons.items():
            b.configure(fg="#ffd54a" if n == m.terms else "#c9d4ee")
        px = m.error * self.scale if hasattr(self, "scale") else 0
        self.info.configure(text="%d 項   最大誤差 %.2f px" % (m.terms, px))

    def choose_terms(self, n):
        self.model.set_terms(n)
        self.refresh_info()
        self.replay()

    def set_speed(self, v):
        self.draw_secs = float(v)

    def set_order(self):
        self.model.set_order(self.order_var.get())
        self.replay()

    def set_circles(self, on):
        self.show_circles = on

    def toggle_circles(self):
        self.circles_var.set(not self.circles_var.get())
        self.set_circles(self.circles_var.get())

    def toggle_pause(self):
        self.paused = not self.paused

    def replay(self):
        self.time = 0.0
        self.cv.delete("all")
        self.items = {}
        self.layout()

    # ---------------- geometry ----------------
    def layout(self):
        """Fit the tree into the canvas and build the static scenery."""
        w = max(200, self.cv.winfo_width())
        h = max(200, self.cv.winfo_height())
        ys = [z.imag for z in self.model.outline]
        xs = [z.real for z in self.model.outline]
        tree_h = max(ys) - min(ys)
        self.scale = min(h * 0.72 / tree_h, w * 0.8 / (max(xs) - min(xs)))
        self.ox = w / 2.0
        self.oy = h * 0.47 - (max(ys) + min(ys)) / 2.0 * self.scale
        self.ground_y = self.oy + max(ys) * self.scale + 4
        self.w, self.h = w, h
        self.cv.delete("all")
        self.items = {}
        self.build_scene()
        self.refresh_info()

    def to_screen(self, z):
        return self.ox + z.real * self.scale, self.oy + z.imag * self.scale

    def flat(self, pts):
        out = []
        for z in pts:
            x, y = self.to_screen(z)
            out += (x, y)
        return out

    def build_scene(self):
        cv, rng = self.cv, random.Random(3)
        # stars in the sky
        self.stars = []
        for _ in range(110):
            x, y = rng.uniform(0, self.w), rng.uniform(0, self.ground_y - 40)
            r = rng.choice((0.8, 1.0, 1.4))
            self.stars.append((cv.create_oval(x - r, y - r, x + r, y + r, fill="#6f7fa8",
                                              outline=""), rng.uniform(0, 6.28)))
        # snowy ground
        g = self.ground_y
        cv.create_oval(-self.w * 0.2, g - 18, self.w * 1.2, g + self.h, fill="#1b2442", outline="")
        self.items["ground"] = cv.create_oval(-self.w * 0.2, g - 18, self.w * 1.2, g + self.h,
                                              fill=BG, outline="")
        # the tree (hidden until it fills in), its trunk and the star
        poly = self.flat(self.model.curve)
        self.items["fill"] = cv.create_polygon(*poly, fill=BG, outline="", smooth=False)
        tw, top = F.TRUNK_W * self.scale, self.oy + (F.TIERS[-1][0] + 0.03) * self.scale
        self.items["trunk"] = cv.create_rectangle(self.ox - tw + 2, top, self.ox + tw - 2,
                                                  g - 2, fill=BG, outline="")
        star = [F.STAR_r if k % 2 == 0 else F.STAR_R for k in range(10)]
        star_pts = []
        for k, rad in enumerate(star):
            a = math.pi / 2 + k * math.pi / 5
            star_pts.append(complex(rad * math.cos(a), F.STAR_CY + rad * math.sin(a)))
        self.rays = [cv.create_line(0, 0, 0, 0, fill=BG, width=2, capstyle="round")
                     for _ in range(8)]                    # the star's shining rays
        self.items["star"] = cv.create_polygon(*self.flat(star_pts), fill=BG, outline="")
        # lights and ornaments inside the tree
        screen_poly = [self.to_screen(z) for z in self.model.curve]
        self.lights = []
        tries = 0
        while len(self.lights) < 70 and tries < 4000:
            tries += 1
            z = complex(rng.uniform(-0.9, 0.9), rng.uniform(F.STAR_CY + 0.25, F.TIERS[-1][0] - 0.02))
            x, y = self.to_screen(z)
            if not point_in(screen_poly, x, y):
                continue
            if any((x - lx) ** 2 + (y - ly) ** 2 < (self.scale * 0.09) ** 2
                   for (lx, ly, _i, _c, _p, _b) in self.lights):
                continue
            big = rng.random() < 0.3
            r = self.scale * (0.028 if big else 0.016)
            col = rng.choice(("#ff4d4d", "#ffd54a", "#4dd2ff", "#ff7ad9", "#7dff7a", "#ffffff"))
            item = cv.create_oval(x - r, y - r, x + r, y + r, fill=BG, outline="")
            self.lights.append((x, y, item, col, rng.uniform(0, 6.28), big))
        # presents under the tree
        self.gifts = []
        specs = [(-0.62, 0.30, 0.20, "#d83a3a", "#ffd54a"), (-0.30, 0.20, 0.15, "#2f7de1", "#ffffff"),
                 (0.30, 0.26, 0.18, "#8b4fd8", "#ffd54a"), (0.62, 0.20, 0.14, "#e8a23a", "#d83a3a"),
                 (0.02, 0.16, 0.11, "#3ab06a", "#ff4d4d")]
        for i, (x, w, h, box, rib) in enumerate(specs):
            items = [cv.create_rectangle(0, 0, 1, 1, fill=BG, outline=""),
                     cv.create_rectangle(0, 0, 1, 1, fill=BG, outline=""),
                     cv.create_rectangle(0, 0, 1, 1, fill=BG, outline="")]
            self.gifts.append((x, w, h, box, rib, items, GIFTS + i * 0.35))
        # the drawing: trace, circles, vectors, tip (one item each, reused)
        self.items["trace_glow"] = cv.create_line(0, 0, 0, 0, fill=BG, width=7, capstyle="round",
                                                  joinstyle="round")
        self.items["trace"] = cv.create_line(0, 0, 0, 0, fill="#7dff9a", width=2.2,
                                             capstyle="round", joinstyle="round")
        self.circle_items = [cv.create_oval(0, 0, 0, 0, outline=BG) for _ in range(160)]
        self.items["vectors"] = cv.create_line(0, 0, 0, 0, fill=BG, width=1.2)
        self.items["tip"] = cv.create_oval(0, 0, 0, 0, fill="#ffd54a", outline="")
        # snow and the greeting on top
        self.snow = []
        for _ in range(140):
            x, y = rng.uniform(0, self.w), rng.uniform(-self.h, self.h)
            r = rng.choice((1.2, 1.8, 2.4))
            self.snow.append([x, y, r, rng.uniform(25, 60), rng.uniform(0, 6.28),
                              cv.create_oval(0, 0, 0, 0, fill="#ffffff", outline="", state="hidden")])
        self.items["greet"] = cv.create_text(self.w / 2, 34, text="", fill="#ffb3c7",
                                             font=("Georgia", 26, "bold italic"))
        self.items["wish"] = cv.create_text(self.w / 2, 72, text="", fill="#ffd9e3",
                                            font=("Georgia", 15, "italic"))
        self.items["label"] = cv.create_text(12, self.h - 14, anchor="w", text="",
                                             fill="#5c6a92", font=("Consolas", 10))

    def box(self, z, r):
        x, y = self.to_screen(z)
        return x - r, y - r, x + r, y + r

    # ---------------- animation ----------------
    def tick(self):
        now = time.perf_counter()
        dt = min(0.05, now - self.last)
        self.last = now
        if not self.paused:
            self.time += dt
        try:
            self.render()
        except tk.TclError:
            return
        self.root.after(16, self.tick)

    def render(self):
        cv, m, t = self.cv, self.model, self.time
        draw_end = APPEAR + self.draw_secs
        done = draw_end + HOLD + FADE                         # circles gone
        after = t - done                                      # the Christmas part
        p = (t - APPEAR) / self.draw_secs                     # curve parameter
        # ---- the trace (the tip has drawn this much) ----
        n = int(len(m.curve) * min(1.0, max(0.0, p)))
        if n >= 2:
            pts = self.flat(m.curve[:n])
            cv.coords(self.items["trace"], *pts)
            cv.coords(self.items["trace_glow"], *pts)
            glow = mix("#123d24", BG, (after - FILL) / 3.0) if after > FILL else "#123d24"
            cv.itemconfigure(self.items["trace_glow"], fill=glow)
            cv.itemconfigure(self.items["trace"],
                             fill=mix("#7dff9a", "#2f8f4f", after / FILL) if after > 0 else "#7dff9a")
        # ---- circles, vectors and the tip ----
        alpha = min(1.0, t / APPEAR) * (1.0 - max(0.0, (t - draw_end - HOLD) / FADE))
        alpha = max(0.0, alpha) if self.show_circles else 0.0
        heads = F.chain(m.drawn, p)
        prev = heads[0]
        k = 0
        vec = []
        for i in range(1, len(heads)):
            r = abs(m.drawn[i][1]) * self.scale
            if r >= 1.2 and k < len(self.circle_items):
                x, y = self.to_screen(prev)
                cv.coords(self.circle_items[k], x - r, y - r, x + r, y + r)
                fade = min(1.0, 0.35 + 6.0 / (r + 6.0))        # small circles fainter
                cv.itemconfigure(self.circle_items[k], outline=mix(BG, "#5f7bd6", alpha * (1 - fade * 0.6)),
                                 state="normal" if alpha > 0.02 else "hidden")
                k += 1
            if alpha > 0.02:
                vec += self.to_screen(prev)
            prev = heads[i]
        for j in range(k, len(self.circle_items)):
            cv.itemconfigure(self.circle_items[j], state="hidden")
        if alpha > 0.02 and len(vec) >= 4:
            vec += self.to_screen(heads[-1])
            cv.coords(self.items["vectors"], *vec)
            cv.itemconfigure(self.items["vectors"], fill=mix(BG, "#c9d4ee", alpha * 0.8),
                             state="normal")
        else:
            cv.itemconfigure(self.items["vectors"], state="hidden")
        tx, ty = self.to_screen(heads[-1])
        tip_r = 4.5 if alpha > 0.02 else 0
        cv.coords(self.items["tip"], tx - tip_r, ty - tip_r, tx + tip_r, ty + tip_r)
        cv.itemconfigure(self.items["label"], text=(
            "%d terms   |c_n| circles head to tail   max error %.2f px"
            % (m.terms, m.error * self.scale)) if alpha > 0.02 else "")
        # ---- twinkling stars ----
        for item, ph in self.stars:
            v = 0.5 + 0.5 * math.sin(t * 1.5 + ph)
            cv.itemconfigure(item, fill=mix("#2b3557", "#dfe7ff", v))
        self.christmas(after)

    def christmas(self, after):
        """After the drawing: fill, star, lights, presents, snow, greeting."""
        cv, t = self.cv, self.time
        a = after / FILL
        cv.itemconfigure(self.items["ground"], fill=mix(BG, GROUND, a * 0.9))
        cv.itemconfigure(self.items["fill"], fill=mix(BG, "#145c32", a))
        cv.itemconfigure(self.items["trunk"], fill=mix(BG, "#6b3e1f", a))
        star_on = (after - FILL * 0.5) / 1.0
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        cv.itemconfigure(self.items["star"], fill=mix(BG, mix("#ffd54a", "#fff3b0", pulse), star_on))
        sx, sy = self.to_screen(complex(0, F.STAR_CY))
        on = min(1.0, max(0.0, star_on))
        for i, ray in enumerate(self.rays):
            ang = i * math.pi / 4 + math.pi / 8 + t * 0.3
            r0 = self.scale * 0.2
            r1 = r0 + self.scale * (0.07 + 0.05 * (0.5 + 0.5 * math.sin(t * 3 + i * 1.7))) * on
            cv.coords(ray, sx + r0 * math.cos(ang), sy + r0 * math.sin(ang),
                      sx + r1 * math.cos(ang), sy + r1 * math.sin(ang))
            cv.itemconfigure(ray, fill=mix(BG, "#ffe680", on * (0.6 + 0.4 * pulse)))
        # lights switch on one by one from the top, then twinkle
        lit = (after - LIGHTS) / 2.5
        ordered = sorted(self.lights, key=lambda l: l[1])
        for i, (x, y, item, col, ph, big) in enumerate(ordered):
            on = lit * len(ordered) - i
            if on <= 0:
                cv.itemconfigure(item, fill=mix(BG, "#145c32", a))
                continue
            v = 0.55 + 0.45 * math.sin(t * (2.0 if big else 3.5) + ph * 3)
            cv.itemconfigure(item, fill=mix("#145c32", col, min(1.0, on) * (v if not big else 1.0)))
        # presents drop in
        for (x, w, h, box, rib, items, t0) in self.gifts:
            u = (after - t0) / 0.6
            if u <= 0:
                for it in items:
                    cv.itemconfigure(it, state="hidden")
                continue
            drop = (1 - min(1.0, u)) ** 2 * 160
            bx, by = self.ox + x * self.scale, self.ground_y - 2 - drop
            bw, bh = w * self.scale / 2, h * self.scale
            cv.coords(items[0], bx - bw, by - bh, bx + bw, by)
            cv.coords(items[1], bx - bw * 0.12, by - bh, bx + bw * 0.12, by)
            cv.coords(items[2], bx - bw, by - bh * 0.62, bx + bw, by - bh * 0.48)
            for it, col in zip(items, (box, rib, rib)):
                cv.itemconfigure(it, fill=col, state="normal")
        # snow
        snowing = after > FILL
        for f in self.snow:
            if not snowing:
                cv.itemconfigure(f[5], state="hidden")
                continue
            f[1] += f[3] * 0.016
            f[0] += math.sin(t * 0.8 + f[4]) * 0.4
            if f[1] > self.h:
                f[1] = -5
            cv.coords(f[5], f[0] - f[2], f[1] - f[2], f[0] + f[2], f[1] + f[2])
            cv.itemconfigure(f[5], state="normal")
        # the greeting, typed out
        g = max(0, int((after - GREETING) * 14))
        heart = " ♥" if g > len(self.greeting) else ""
        cv.itemconfigure(self.items["greet"], text=self.greeting[:g] + heart)
        w = max(0, int((after - GREETING - len(self.greeting) / 14.0 - 0.6) * 18))
        cv.itemconfigure(self.items["wish"], text=self.wish[:w])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fourier Epicycles Christmas Tree (GUI)")
    ap.add_argument("--terms", type=int, default=100, help="Fourier terms: 20, 50, 100, 200, 512")
    ap.add_argument("--seconds", type=float, default=12.0, help="seconds to draw the outline")
    ap.add_argument("--at", type=float, default=None, help=argparse.SUPPRESS)       # start time
    ap.add_argument("--geometry", default="980x820", help=argparse.SUPPRESS)
    ap.add_argument("--quit-after", type=float, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = tk.Tk()
    root.geometry(args.geometry)
    App(root, args.terms, args.seconds, args.at)
    if args.quit_after:
        root.after(int(args.quit_after * 1000), root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
