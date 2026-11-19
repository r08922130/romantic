# -*- coding: utf-8 -*-
"""
effects.py - reusable, holiday-agnostic effects any scene may use
=================================================================

  Fx         particles (hearts, zzz, sparkles ...) with colour ramps
  Starfield  twinkling stars in the upper part of the sky
  Banner     the typewriter greeting at the top (two lines + shimmer)

Scene-specific effects (snow, petals, fireworks ...) live in the scene's
own module instead.
"""
import math
import random

from .render import CW, S, clamp, fit, hash01, text_width

# colour ramps (young -> old) for particles
HEART_RAMP = (211, 204, 168, 132, 95, 238)
Z_RAMP = (153, 111, 67, 60, 238)
SPARK_RAMP = (231, 229, 222, 179, 137, 238)


class Fx:
    def __init__(self, limit=220):
        self.p = []
        self.limit = limit

    def emit(self, x, y, vx, vy, life, ch, ramp, wob=0.0, bold=1):
        if len(self.p) < self.limit:
            self.p.append([x, y, vx, vy, life, life, ch, ramp, wob,
                           random.uniform(0, 6.28), bold])

    def update(self, dt):
        for q in self.p:
            q[4] -= dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
        self.p = [q for q in self.p if q[4] > 0]

    def draw(self, cv, t):
        for q in self.p:
            r = 1.0 - q[4] / q[5]
            ramp = q[7]
            col = ramp[min(len(ramp) - 1, int(r * len(ramp)))]
            x = q[0] + math.sin(t * 3.0 + q[9]) * q[8]
            cv.put(cv.px(x), cv.py(q[1]), q[6], S(col, q[10]))


FIREWORK_RAMPS = [(231, 226, 220, 214, 208, 238), (231, 159, 51, 39, 27, 238),
                  (231, 219, 213, 201, 163, 238), (231, 157, 120, 46, 34, 238),
                  (231, 224, 217, 210, 203, 238)]


class Fireworks:
    """Rockets that rise and burst into particles (drawn by an Fx)."""

    def __init__(self, fx):
        self.fx = fx
        self.rockets = []

    def launch(self, x, y0, peak, ramp=None, n=22):
        self.rockets.append([x, float(y0), peak, ramp or random.choice(FIREWORK_RAMPS), n])

    def burst(self, x, y, ramp=None, n=22, speed=(5.0, 9.0)):
        ramp = ramp or random.choice(FIREWORK_RAMPS)
        for k in range(n):
            a = k / float(n) * 6.283
            sp = random.uniform(*speed)
            self.fx.emit(x, y, math.cos(a) * sp, math.sin(a) * sp * 0.5,
                         random.uniform(0.9, 1.5), random.choice("*+."), ramp)

    def update(self, dt):
        for r in self.rockets:
            r[1] -= 14.0 * dt
            if r[1] <= r[2]:
                self.burst(r[0], r[1], r[3], r[4])
        self.rockets = [r for r in self.rockets if r[1] > r[2]]

    def draw(self, cv):
        for r in self.rockets:
            if cv.k == 1:
                cv.put(int(r[0]), int(r[1]), "|", S(223))
            else:
                cv.put(cv.px(int(r[0])), cv.py(int(r[1])), "|", S(223))


class Starfield:
    """Twinkling stars. `rng` makes the layout repeatable."""

    def __init__(self, rng, n=40, width=CW, height=17):
        self.stars = []
        for _ in range(n):
            self.stars.append((rng.randrange(0, width), rng.randrange(0, height),
                               rng.uniform(0, 6.28)))
        self.width, self.height = width, height
        self.density = n / float(width * height)
        self.extra = []              # stars outside the stage (wide / tall windows)
        self.extra_for = (0, 0, width)

    def fill_margins(self, x0, y0, x1):
        """Scatter stars (same density) over the sky outside the stage."""
        if (x0, y0, x1) == self.extra_for:
            return
        self.extra_for = (x0, y0, x1)
        self.extra = []
        for y in range(y0, self.height):
            for x in range(x0, x1):
                if 0 <= x < self.width and y >= 0:
                    continue
                if hash01(x, y, 7) < self.density:
                    self.extra.append((x, y, hash01(x, y, 8) * 6.28))

    def big_sky(self, cv):
        """Drawn bigger (cv.k > 1): stars over the bigger sky, a little
        sparser per cell (the same sky, seen bigger)."""
        key = (cv.k, cv.x0, cv.y0, cv.x1)
        if getattr(self, "big_for", None) != key:
            self.big_for = key
            top = int(self.height * cv.k)
            self.big = [(x, y, hash01(x, y, 9) * 6.28)
                        for y in range(cv.y0, top) for x in range(cv.x0, cv.x1)
                        if hash01(x, y, 7) < self.density / cv.k]
        return self.big

    def draw(self, cv, t):
        if cv.k != 1:
            stars = self.big_sky(cv)
        else:
            self.fill_margins(min(cv.x0, 0), min(cv.y0, 0), max(cv.x1, self.width))
            stars = self.stars + self.extra
        for x, y, ph in stars:
            v = math.sin(t * 1.3 + ph)
            if v > 0.88:
                cv.put(x, y, "+", S(255, 1))
            elif v > 0.0:
                cv.put(x, y, ".", S(250))
            else:
                cv.put(x, y, ".", S(239))


class Banner:
    """Two-line greeting typed out letter by letter, with a shimmer.
    Colours are parameters so each scene can have its own palette."""
    RAMP = (210, 217, 224, 229, 224, 217)

    def __init__(self, greeting, wish, heart, width=CW, ramp=None,
                 wish_colour=218, heart_colours=(196, 203)):
        self.width = width
        self.l1 = fit((greeting + " " + heart).strip(), width - 2)
        self.l2 = fit(wish, width - 2)
        self.w1, self.w2 = text_width(self.l1), text_width(self.l2)
        self.ramp = ramp or self.RAMP
        self.wish_colour = wish_colour
        self.heart_colours = heart_colours
        self.shown = 0.0
        self.dir = -1
        self.total = len(self.l1) + len(self.l2) + 6

    def show(self):
        self.dir = 1

    def hide(self):
        self.dir = -1

    def update(self, dt):
        rate = 15.0 if self.dir > 0 else 70.0
        self.shown = clamp(self.shown + self.dir * rate * dt, 0, self.total)

    def draw(self, cv, t):
        n = int(self.shown)
        if n <= 0:
            return
        hc = self.heart_colours

        def c1(i, c):
            if c == "♥":
                return S(hc[0] if int(t * 3) % 2 == 0 else hc[1], 1)
            return S(self.ramp[int(t * 6 + i) % len(self.ramp)], 1)

        # a cropped (small) window: keep the greeting on screen and inside it
        y = max(0, getattr(cv, "y0", 0))
        width = self.width if getattr(cv, "k", 1) == 1 else cv.sw   # centred on the stage
        avail = min(width, getattr(cv, "x1", width) - getattr(cv, "x0", 0))
        l1, l2 = self.l1, self.l2
        if avail < width:
            l1, l2 = fit(l1, avail - 2), fit(l2, avail - 2)
        w1, w2 = text_width(l1), text_width(l2)
        end = cv.put_text((width - w1) // 2, y, l1[:n], c1)
        if n < len(l1) and int(t * 4) % 2 == 0:
            cv.put(end, y, "_", S(231, 1))
        m = n - len(l1) - 3
        if m > 0:
            wc = S(self.wish_colour)
            end = cv.put_text((width - w2) // 2, y + 1, l2[:m],
                              lambda i, c: wc)
            if m < len(l2) and int(t * 4) % 2 == 0:
                cv.put(end, y + 1, "_", wc)
