# -*- coding: utf-8 -*-
"""
app.py - Fourier Epicycles Christmas Tree (GUI, tkinter)
========================================================

    python fourier_gui/app.py                 (or double-click run_fourier.bat)
    python fourier_gui/app.py --terms 200 --seconds 12

EVERYTHING in the picture is drawn by Fourier epicycles: the tree, the star,
the trunk, the garlands, every ornament (baubles, hearts, bells, candy canes)
and every present (box, ribbons, bow). Each is a closed curve with its own
Fourier series (fourier.scene_shapes); a chain of rotating circles, put head
to tail, draws it. Groups are drawn one after another, the shapes of a group
at the same time. Then the circles fade, every shape fills with its colour,
the star shines, snow falls and the greeting appears.

The coefficients are computed once at start (fourier.py); every frame only
adds up the rotating vectors.

Keys:  Space pause   R replay   C circles on/off   1-5 terms (20/50/100/200/all)
       Esc / Q quit
"""
import argparse
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

TERM_CHOICES = (20, 50, 100, 200, 512)
BG = "#0b1026"
GROUND = "#d8e2f0"

# timeline: the tree takes `seconds`; the other groups take this share of it
APPEAR = 1.2
GROUPS = [("tree", 1.0), ("top", 0.22), ("garlands", 0.28), ("ornaments", 0.34),
          ("gifts", 0.40)]
HOLD, FADE = 1.0, 1.5
FILL, GREETING = 2.0, 4.0                            # after the circles are gone


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, a):
    """Colour c1 -> c2 by a (0..1): tkinter has no transparency, so fades
    mix towards the background colour."""
    a = 0.0 if a < 0 else (1.0 if a > 1 else a)
    r1, g1, b1 = hex_rgb(c1)
    r2, g2, b2 = hex_rgb(c2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * a), int(g1 + (g2 - g1) * a),
                              int(b1 + (b2 - b1) * a))


def load_greeting():
    """Use the Christmas greeting from the ASCII program's settings.json."""
    greeting, wish = "Merry Christmas, My Love!", "Every day with you feels like Christmas."
    try:
        with open(os.path.join(os.path.dirname(HERE), "settings.json"), encoding="utf-8") as f:
            x = json.load(f).get("scenes", {}).get("christmas", {})
        greeting, wish = x.get("greeting", greeting), x.get("wish", wish)
    except (OSError, ValueError):
        pass
    return greeting, wish


# ---------------------------------------------------------------------
#  The maths for one shape
# ---------------------------------------------------------------------
class Drawing:
    """One closed shape: its samples and Fourier coefficients (computed once),
    and the reconstruction with the chosen number of terms."""

    def __init__(self, group, name, outline, colour, samples, cap):
        self.group, self.name, self.colour = group, name, colour
        self.outline = outline
        self.samples = F.resample(outline, samples)
        self.coeffs = F.dft(self.samples)
        self.cap = cap
        self.start = self.dur = 0.0
        self.order = "size"

    def set_terms(self, terms):
        n = terms if self.cap is None else min(terms, self.cap)
        self.terms = max(1, min(n, len(self.coeffs)))
        kept = F.truncate(self.coeffs, self.terms)
        self.chain_coeffs = F.by_size(kept) if self.order == "size" else F.by_frequency(kept)
        self.error = F.max_error(kept, self.samples)
        m = 1200 if self.group == "tree" else 300
        self.curve = [F.evaluate(kept, k / float(m)) for k in range(m + 1)]

    def param(self, t):
        return (t - self.start) / self.dur


class Model:
    def __init__(self, terms=100, seconds=10.0):
        self.drawings = [Drawing(*s) for s in F.scene_shapes()]
        self.order = "size"
        self.set_terms(terms)
        self.set_seconds(seconds)

    def set_terms(self, terms):
        self.terms = terms
        for d in self.drawings:
            d.order = self.order
            d.set_terms(terms)

    def set_order(self, order):
        self.order = order
        self.set_terms(self.terms)

    def set_seconds(self, seconds):
        """Lay the groups out one after another on the timeline."""
        t = APPEAR
        for group, share in GROUPS:
            dur = seconds * share
            for d in self.drawings:
                if d.group == group:
                    d.start, d.dur = t, dur
            t += dur
        self.draw_end = t
        self.done = t + HOLD + FADE                  # all circles gone

    @property
    def tree(self):
        return self.drawings[0]


# ---------------------------------------------------------------------
#  The window
# ---------------------------------------------------------------------
class App:
    POOL = 600                                       # circle items, reused every frame

    def __init__(self, root, terms=100, seconds=10.0, at=None):
        self.root = root
        self.model = Model(terms, seconds)
        self.greeting, self.wish = load_greeting()
        self.seconds = seconds
        self.show_circles = True
        self.paused = False
        self.time = at or 0.0
        self.last = time.perf_counter()
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
            b = tk.Button(bar, text="全部" if n == TERM_CHOICES[-1] else str(n), width=4,
                          command=lambda n=n: self.choose_terms(n), **style)
            b.pack(side="left", padx=2)
            self.term_buttons[n] = b
        tk.Label(bar, text="   速度", **style).pack(side="left")
        self.speed = tk.Scale(bar, from_=4, to=30, orient="horizontal", length=120,
                              showvalue=False, bg=style["bg"], troughcolor="#24305a",
                              highlightthickness=0, bd=0)
        self.speed.set(self.seconds)
        self.speed.configure(command=self.set_speed)
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

    def refresh_info(self):
        m = self.model
        for n, b in self.term_buttons.items():
            b.configure(fg="#ffd54a" if n == m.terms else "#c9d4ee")
        self.info.configure(text="%d 項   %d 個圖形   樹的最大誤差 %.1f px"
                            % (m.terms, len(m.drawings), m.tree.error * self.scale))

    def choose_terms(self, n):
        self.model.set_terms(n)
        self.replay()

    def set_speed(self, v):
        if float(v) != self.seconds:
            self.seconds = float(v)
            self.model.set_seconds(self.seconds)

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
        self.layout()

    # ---------------- geometry ----------------
    def layout(self):
        w = max(200, self.cv.winfo_width())
        h = max(200, self.cv.winfo_height())
        pts = [z for d in self.model.drawings for z in d.outline]
        xs, ys = [z.real for z in pts], [z.imag for z in pts]
        self.scale = min(h * 0.76 / (max(ys) - min(ys)), w * 0.86 / (max(xs) - min(xs)))
        self.ox = w / 2.0
        self.oy = h * 0.50 - (max(ys) + min(ys)) / 2.0 * self.scale
        self.ground_y = self.oy + F.GROUND_Y * self.scale
        self.w, self.h = w, h
        self.cv.delete("all")
        self.build_scene()
        self.refresh_info()

    def to_screen(self, z):
        return self.ox + z.real * self.scale, self.oy + z.imag * self.scale

    def flat(self, pts):
        out = []
        for z in pts:
            out += self.to_screen(z)
        return out

    def build_scene(self):
        cv, rng = self.cv, random.Random(3)
        self.stars = []
        for _ in range(110):                                       # the night sky
            x, y = rng.uniform(0, self.w), rng.uniform(0, self.ground_y - 60)
            r = rng.choice((0.8, 1.0, 1.4))
            self.stars.append((cv.create_oval(x - r, y - r, x + r, y + r, fill="#6f7fa8",
                                              outline=""), rng.uniform(0, 6.28)))
        g = self.ground_y
        self.ground = cv.create_oval(-self.w * 0.2, g - 14, self.w * 1.2, g + self.h,
                                     fill=BG, outline="")
        # every shape: a fill (appears at the end) under its trace
        self.fills, self.traces = [], []
        for d in self.model.drawings:
            self.fills.append(cv.create_polygon(*self.flat(d.curve), fill="", outline=""))
            width = 2.4 if d.group == "tree" else 1.8
            self.traces.append(cv.create_line(0, 0, 0, 0, fill=d.colour, width=width,
                                              capstyle="round", joinstyle="round",
                                              state="hidden"))
        for i, d in enumerate(self.model.drawings):               # the trunk stands
            if d.name == "trunk":                                 # behind the tree
                cv.tag_lower(self.traces[i], self.fills[0])
                cv.tag_lower(self.fills[i], self.traces[i])
        self.rays = [cv.create_line(0, 0, 0, 0, fill=BG, width=2, capstyle="round")
                     for _ in range(8)]                            # the star's rays
        self.circles = [cv.create_oval(0, 0, 0, 0, outline=BG, state="hidden")
                        for _ in range(self.POOL)]
        self.vectors = [cv.create_line(0, 0, 0, 0, fill=BG, width=1.1, state="hidden")
                        for _ in self.model.drawings]
        self.tips = [cv.create_oval(0, 0, 0, 0, fill="#ffd54a", outline="", state="hidden")
                     for _ in self.model.drawings]
        self.snow = []
        for _ in range(140):
            x, y = rng.uniform(0, self.w), rng.uniform(-self.h, self.h)
            self.snow.append([x, y, rng.choice((1.2, 1.8, 2.4)), rng.uniform(25, 60),
                              rng.uniform(0, 6.28),
                              cv.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                             state="hidden")])
        self.greet = cv.create_text(self.w / 2, 34, text="", fill="#ffb3c7",
                                    font=("Georgia", 26, "bold italic"))
        self.wish_item = cv.create_text(self.w / 2, 72, text="", fill="#ffd9e3",
                                        font=("Georgia", 15, "italic"))
        self.label = cv.create_text(12, self.h - 14, anchor="w", text="", fill="#5c6a92",
                                    font=("Consolas", 10))
        self.drawn_n = [-1] * len(self.model.drawings)

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
        after = t - m.done                                    # the Christmas part
        fade_all = 1.0 - max(0.0, (t - m.draw_end - HOLD) / FADE)
        k = 0                                                 # circle items used
        active = []
        for i, d in enumerate(m.drawings):
            p = d.param(t)
            # the trace: how much of its curve this shape's tip has drawn
            n = int(len(d.curve) * min(1.0, max(0.0, p)))
            if n != self.drawn_n[i]:
                self.drawn_n[i] = n
                if n >= 2:
                    cv.coords(self.traces[i], *self.flat(d.curve[:n]))
                    cv.itemconfigure(self.traces[i], state="normal")
                else:
                    cv.itemconfigure(self.traces[i], state="hidden")
            # its circles: fade in before it starts (the tree has a long lead-in),
            # out just after it is done
            lead = APPEAR if d.group == "tree" else 0.35
            alpha = min(1.0, (t - d.start + lead) / lead, (d.start + d.dur + 0.35 - t) / 0.35)
            alpha = max(0.0, min(alpha, fade_all)) if self.show_circles else 0.0
            if alpha > 0.02:
                active.append(d.group)
            heads = F.chain(d.chain_coeffs, p)
            vec = []
            if alpha > 0.02:
                prev = heads[0]
                for j in range(1, len(heads)):
                    r = abs(d.chain_coeffs[j][1]) * self.scale
                    if r >= 1.5 and k < self.POOL:
                        x, y = self.to_screen(prev)
                        cv.coords(self.circles[k], x - r, y - r, x + r, y + r)
                        faint = min(1.0, 0.35 + 6.0 / (r + 6.0))
                        cv.itemconfigure(self.circles[k], state="normal",
                                         outline=mix(BG, "#5f7bd6", alpha * (1 - faint * 0.6)))
                        k += 1
                    vec += self.to_screen(prev)
                    prev = heads[j]
                vec += self.to_screen(heads[-1])
            if len(vec) >= 4:
                cv.coords(self.vectors[i], *vec)
                cv.itemconfigure(self.vectors[i], state="normal",
                                 fill=mix(BG, "#c9d4ee", alpha * 0.75))
                tx, ty = self.to_screen(heads[-1])
                cv.coords(self.tips[i], tx - 3.5, ty - 3.5, tx + 3.5, ty + 3.5)
                cv.itemconfigure(self.tips[i], state="normal")
            else:
                cv.itemconfigure(self.vectors[i], state="hidden")
                cv.itemconfigure(self.tips[i], state="hidden")
        for j in range(k, self.POOL):
            if cv.itemcget(self.circles[j], "state") != "hidden":
                cv.itemconfigure(self.circles[j], state="hidden")
        groups = sorted(set(active), key=[g for g, _s in GROUPS].index)
        cv.itemconfigure(self.label, text=(
            "%d terms   drawing: %s   (%d circles)" % (m.terms, ", ".join(groups), k)
            if groups else ""))
        for item, ph in self.stars:                           # twinkling sky
            cv.itemconfigure(item, fill=mix("#2b3557", "#dfe7ff", 0.5 + 0.5 * math.sin(t * 1.5 + ph)))
        self.christmas(after)

    def christmas(self, after):
        """After the drawing: every shape fills in, the star shines, snow, greeting."""
        cv, m, t = self.cv, self.model, self.time
        a = after / FILL
        cv.itemconfigure(self.ground, fill=mix(BG, GROUND, a * 0.9))
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        for i, d in enumerate(m.drawings):
            if a <= 0:
                cv.itemconfigure(self.fills[i], fill="")
                continue
            fill = "#145c32" if d.group == "tree" else d.colour
            if d.name == "star":
                fill = mix("#ffd54a", "#fff3b0", pulse)
            cv.itemconfigure(self.fills[i], fill=mix(BG, fill, a))
            if d.group == "tree":                             # outline settles down
                cv.itemconfigure(self.traces[i], fill=mix("#2fbf5f", "#1f7a3f", a))
        on = min(1.0, max(0.0, after / FILL - 0.5))
        sx, sy = self.to_screen(complex(0, F.STAR_CY))
        for i, ray in enumerate(self.rays):
            ang = i * math.pi / 4 + math.pi / 8 + t * 0.3
            r0 = self.scale * 0.2
            r1 = r0 + self.scale * (0.07 + 0.05 * (0.5 + 0.5 * math.sin(t * 3 + i * 1.7))) * on
            cv.coords(ray, sx + r0 * math.cos(ang), sy + r0 * math.sin(ang),
                      sx + r1 * math.cos(ang), sy + r1 * math.sin(ang))
            cv.itemconfigure(ray, fill=mix(BG, "#ffe680", on * (0.6 + 0.4 * pulse)))
        snowing = after > FILL
        for f in self.snow:
            if not snowing:
                if cv.itemcget(f[5], "state") != "hidden":
                    cv.itemconfigure(f[5], state="hidden")
                continue
            f[1] += f[3] * 0.016
            f[0] += math.sin(t * 0.8 + f[4]) * 0.4
            if f[1] > self.h:
                f[1] = -5
            cv.coords(f[5], f[0] - f[2], f[1] - f[2], f[0] + f[2], f[1] + f[2])
            cv.itemconfigure(f[5], state="normal")
        g = max(0, int((after - GREETING) * 14))
        heart = " ♥" if g > len(self.greeting) else ""
        cv.itemconfigure(self.greet, text=self.greeting[:g] + heart)
        w = max(0, int((after - GREETING - len(self.greeting) / 14.0 - 0.6) * 18))
        cv.itemconfigure(self.wish_item, text=self.wish[:w])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fourier Epicycles Christmas Tree (GUI)")
    ap.add_argument("--terms", type=int, default=100, help="Fourier terms: 20, 50, 100, 200, 512")
    ap.add_argument("--seconds", type=float, default=10.0,
                    help="seconds to draw the tree (the decorations take a share of it)")
    ap.add_argument("--at", type=float, default=None, help=argparse.SUPPRESS)
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
