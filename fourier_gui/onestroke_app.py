# -*- coding: utf-8 -*-
"""
onestroke_app.py - '一筆畫': the whole picture drawn by ONE chain of circles
============================================================================

    python fourier_gui/app.py --mode one

The tree, star, garlands, ornaments (on their strings), trunk, ground and
presents are one closed curve (onestroke.py) with one Fourier series. One
chain of rotating circles draws all of it in a single stroke; the trace
takes the colour of the part it is drawing. Afterwards each part is filled
from its own stretch of the reconstructed curve.
"""
import math
import random

import fourier as F
from app import APPEAR, BG, FADE, FILL, GREETING, GROUND, HOLD, App, mix
from onestroke import OneStroke

STRETCH = 4.5            # the one stroke takes this many times the "tree seconds"
FILL_ORDER = ("trunk", "tree", "star", "garland", "orn", "box", "bow")


class OneStrokeApp(App):
    TERM_CHOICES = (200, 500, 1000, 1500, 2048)
    DEFAULT_TERMS = 1000
    MODE = "one"

    def make_model(self, terms, seconds):
        self.draw_secs = seconds * STRETCH
        return OneStroke(terms)

    @property
    def draw_end(self):
        return APPEAR + self.draw_secs

    @property
    def done(self):
        return self.draw_end + HOLD + FADE

    def refresh_info(self):
        m = self.model
        for n, b in self.term_buttons.items():
            b.configure(fg="#ffd54a" if n == m.terms else "#c9d4ee")
        self.info.configure(text="誤差 %.1f px" % (m.error * self.scale))

    def set_speed(self, v):
        if float(v) != self.seconds:
            self.seconds = float(v)
            self.draw_secs = self.seconds * STRETCH

    # ---------------- geometry ----------------
    def layout(self):
        w = max(200, self.cv.winfo_width())
        h = max(200, self.cv.winfo_height())
        xs = [z.real for z in self.model.path]
        ys = [z.imag for z in self.model.path]
        self.scale = min(h * 0.80 / (max(ys) - min(ys)), w * 0.90 / (max(xs) - min(xs)))
        self.ox = w / 2.0
        self.oy = h * 0.52 - (max(ys) + min(ys)) / 2.0 * self.scale
        self.ground_y = self.oy + F.GROUND_Y * self.scale
        self.w, self.h = w, h
        self.cv.delete("all")
        self.build_scene()
        self.refresh_info()

    def build_scene(self):
        cv, m, rng = self.cv, self.model, random.Random(3)
        self.stars = []
        for _ in range(110):
            x, y = rng.uniform(0, self.w), rng.uniform(0, self.ground_y - 60)
            r = rng.choice((0.8, 1.0, 1.4))
            self.stars.append((cv.create_oval(x - r, y - r, x + r, y + r, fill="#6f7fa8",
                                              outline=""), rng.uniform(0, 6.28)))
        g = self.ground_y
        self.ground = cv.create_rectangle(-10, g, self.w + 10, self.h + 10, fill=BG, outline="")
        # fills, bottom to top (each from its own stretch of the curve)
        self.fills = {}
        labels = sorted((l for l, p in m.parts.items() if p["fill"]),
                        key=lambda l: [l.startswith(k) for k in FILL_ORDER].index(True))
        for label in labels:
            pts = m.part_points(label)
            if len(pts) >= 3:
                self.fills[label] = cv.create_polygon(*self.flat(pts), fill="", outline="")
        # the trace: one line item per stretch of one part, in that part's colour
        self.run_items = []
        for (label, i0, i1) in m.runs:
            part = m.parts[label]
            item = cv.create_line(0, 0, 0, 0, fill=part["colour"], width=part["width"],
                                  capstyle="round", joinstyle="round", state="hidden")
            self.run_items.append([item, label, i0, i1, -1])        # last drawn end
        self.rays = [cv.create_line(0, 0, 0, 0, fill=BG, width=2, capstyle="round")
                     for _ in range(8)]
        self.circles = [cv.create_oval(0, 0, 0, 0, outline=BG, state="hidden")
                        for _ in range(self.POOL)]
        self.vector = cv.create_line(0, 0, 0, 0, fill=BG, width=1.1, state="hidden")
        self.tip = cv.create_oval(0, 0, 0, 0, fill="#ffd54a", outline="", state="hidden")
        self.snow = []
        for _ in range(140):
            x, y = rng.uniform(0, self.w), rng.uniform(-self.h, self.h)
            self.snow.append([x, y, rng.choice((1.2, 1.8, 2.4)), rng.uniform(25, 60),
                              rng.uniform(0, 6.28),
                              cv.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                             state="hidden")])
        self.greet = cv.create_text(self.w / 2, 30, text="", fill="#ffb3c7",
                                    font=("Georgia", 24, "bold italic"))
        self.wish_item = cv.create_text(self.w / 2, 64, text="", fill="#ffd9e3",
                                        font=("Georgia", 14, "italic"))
        self.label = cv.create_text(12, self.h - 14, anchor="w", text="", fill="#5c6a92",
                                    font=("Consolas", 10))

    # ---------------- animation ----------------
    def render(self):
        cv, m, t = self.cv, self.model, self.time
        p = (t - APPEAR) / self.draw_secs
        n = int((len(m.curve) - 1) * min(1.0, max(0.0, p)))
        drawing = None
        for run in self.run_items:                      # the trace, part by part
            item, label, i0, i1, last = run
            end = min(i1, n)
            if end == last:
                continue
            run[4] = end
            if end - i0 >= 1:
                cv.coords(item, *self.flat(m.curve[i0:end + 1]))
                cv.itemconfigure(item, state="normal")
            else:
                cv.itemconfigure(item, state="hidden")
        k = 0
        alpha = min(1.0, t / APPEAR, 1.0 - (t - self.draw_end - HOLD) / FADE)
        alpha = max(0.0, alpha) if self.show_circles else 0.0
        heads = F.chain(m.chain_coeffs, p)
        if alpha > 0.02:
            vec = []
            prev = heads[0]
            for j in range(1, len(heads)):
                r = abs(m.chain_coeffs[j][1]) * self.scale
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
            cv.coords(self.vector, *vec)
            cv.itemconfigure(self.vector, state="normal", fill=mix(BG, "#c9d4ee", alpha * 0.7))
            tx, ty = self.to_screen(heads[-1])
            cv.coords(self.tip, tx - 4, ty - 4, tx + 4, ty + 4)
            cv.itemconfigure(self.tip, state="normal")
            if 0 <= p <= 1:
                drawing = m.curve_labels[n]
        else:
            cv.itemconfigure(self.vector, state="hidden")
            cv.itemconfigure(self.tip, state="hidden")
        for j in range(k, self.POOL):
            if cv.itemcget(self.circles[j], "state") != "hidden":
                cv.itemconfigure(self.circles[j], state="hidden")
        cv.itemconfigure(self.label, text=(
            "one stroke: %d terms, %d circles shown   now drawing: %s   %d%%"
            % (m.terms, k, drawing, int(100 * min(1.0, max(0.0, p)))) if alpha > 0.02 else ""))
        for item, ph in self.stars:
            cv.itemconfigure(item, fill=mix("#2b3557", "#dfe7ff", 0.5 + 0.5 * math.sin(t * 1.5 + ph)))
        self.christmas_one(t - self.done)

    def christmas_one(self, after):
        cv, m, t = self.cv, self.model, self.time
        a = after / FILL
        cv.itemconfigure(self.ground, fill=mix(BG, GROUND, a * 0.85))
        pulse = 0.5 + 0.5 * math.sin(t * 3.0)
        for label, item in self.fills.items():
            if a <= 0:
                cv.itemconfigure(item, fill="")
                continue
            col = m.parts[label]["colour"]
            if label == "tree":
                col = "#145c32"
            elif label == "star":
                col = mix("#ffd54a", "#fff3b0", pulse)
            cv.itemconfigure(item, fill=mix(BG, col, a))
        on = min(1.0, max(0.0, a - 0.5))
        sx, sy = self.to_screen(complex(0, F.STAR_CY))
        for i, ray in enumerate(self.rays):
            ang = i * math.pi / 4 + math.pi / 8 + t * 0.3
            r0 = self.scale * 0.2
            r1 = r0 + self.scale * (0.07 + 0.05 * (0.5 + 0.5 * math.sin(t * 3 + i * 1.7))) * on
            cv.coords(ray, sx + r0 * math.cos(ang), sy + r0 * math.sin(ang),
                      sx + r1 * math.cos(ang), sy + r1 * math.sin(ang))
            cv.itemconfigure(ray, fill=mix(BG, "#ffe680", on * (0.6 + 0.4 * pulse)))
        for f in self.snow:
            if after <= FILL:
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
