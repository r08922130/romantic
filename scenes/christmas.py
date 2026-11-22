# -*- coding: utf-8 -*-
"""
christmas.py - ChristmasScene: the tree, presents, lights and snow
==================================================================

    python main.py --scene christmas        (also the default)

Story: snow -> the tree lights up from the top -> the star -> presents drop
in -> the cats arrive and play (hiding behind presents, gazing at the tree)
-> they sit under the tree and "Merry Christmas, My Love!" appears.

Everything Christmas-only lives in this file: Snow, Tree, Gift, the snowy
ground, the intro timeline and the Santa hat the cats wear here.
"""
import math
import random

from engine.cats import Accessory
from engine.effects import SPARK_RAMP, Starfield
from engine.render import CH, CW, S, clamp, lay_out
from engine.scene import BaseScene
from engine.sprites import Art

CX = CW // 2               # tree centre column
GIFT_BASE = 24             # bottom row of the presents

# intro timeline (seconds)
T_TREE, T_TREE_LEN = 3.5, 7.0
T_LIGHTS, T_LIGHTS_LEN = 6.5, 6.0
T_STAR = 11.0
T_GIFT0, T_GIFT_STEP = 13.0, 0.6
INTRO_END = 26.0


# ---------------------------------------------------------------------
#  Snow + snowy ground
# ---------------------------------------------------------------------
class Snow:
    def __init__(self, rng, n=90):
        self.f = []
        self.n = 0
        for _ in range(n):
            big = rng.random() < 0.28
            self.f.append([rng.uniform(0, CW), rng.uniform(0, CH),
                           rng.uniform(2.4, 3.6) if big else rng.uniform(1.0, 2.0),
                           rng.uniform(0, 6.28),
                           "*" if big else rng.choice(".'`,"),
                           255 if big else rng.choice((250, 246, 252))])
        self.base = n
        self.view = (0, 0, CW, CH)

    def set_view(self, view):
        """A bigger window gets more flakes (same density), falling over all of it."""
        self.view = view
        x0, y0, x1, _y1 = view
        want = int(self.base * (x1 - x0) * (CH - y0) / float(CW * CH))
        rng = random.Random(len(self.f))
        while len(self.f) < want:
            big = rng.random() < 0.28
            self.f.append([rng.uniform(x0, x1), rng.uniform(y0, CH),
                           rng.uniform(2.4, 3.6) if big else rng.uniform(1.0, 2.0),
                           rng.uniform(0, 6.28),
                           "*" if big else rng.choice(".'`,"),
                           255 if big else rng.choice((250, 246, 252))])

    def update(self, dt, t, intensity):
        n = int(len(self.f) * intensity)
        wind = 1.3 * math.sin(t * 0.15)
        x0, y0, x1, _y1 = self.view
        for f in self.f[:n]:
            f[1] += f[2] * dt
            f[0] += (math.sin(t * 0.8 + f[3]) * 1.2 + wind) * dt
            if f[1] >= CH:
                f[1] = y0 - 1.0
                f[0] = random.uniform(x0, x1)
            if f[0] < x0:
                f[0] += x1 - x0
            elif f[0] >= x1:
                f[0] -= x1 - x0
        self.n = n

    def draw(self, cv):
        for f in self.f[:self.n]:
            cv.put(int(f[0]), int(f[1]), f[4], S(f[5]))


def snowy_floor(rng, columns=None):
    cells = []
    for y in range(24, CH):
        for x in (range(CW) if columns is None else columns):
            v = rng.random()
            if v < 0.10:
                cells.append((x, y, ".", 240))
            elif v < 0.125:
                cells.append((x, y, "*", 244))
    return cells


# small snowy pines for the margins of a wide window
_PINE_COLOURS = {"*": S(255, 1), "^": S(28), "/": S(22), "\\": S(22), "|": S(94)}
PINE_S = Art(["  *  ", " /^\\ ", "/^*^\\", "  |  "], charmap=_PINE_COLOURS)
PINE_L = Art(["  *  ", " /^\\ ", " /*\\ ", "/^^*\\", "/*^^\\", "  |  "],
             charmap=_PINE_COLOURS)


def draw_ground(cv, rng_cells):
    pat = "-~~-._.~-~'"
    for x in cv.xs():
        cv.put(x, 23, pat[x % len(pat)], S(252))
    for (x, y, c, col) in rng_cells:
        cv.put(x, y, c, S(col))


# ---------------------------------------------------------------------
#  The Christmas tree
# ---------------------------------------------------------------------
class Tree:
    TIERS = [(3, 1), (4, 3), (4, 5), (5, 7)]   # (rows, half-width of first row)
    TOP = 5
    FOLIAGE = [(235, 235, 236), (22, 22, 28), (22, 28, 34), (28, 34, 40)]
    LCOL = (196, 226, 46, 51, 201, 214)
    OCOL = (196, 33, 214, 201, 45, 135, 226, 160, 69, 213, 250)

    def __init__(self, rng):
        self.rows = []       # (y, half, [(dx, ch, shade)])
        self.tier_rows = []
        y = self.TOP
        nt = len(self.TIERS)
        for ti, (n, h0) in enumerate(self.TIERS):
            first = y
            for r in range(n):
                h = h0 + 2 * r
                last = (r == n - 1)
                cells = []
                for dx in range(-h, h + 1):
                    if dx == -h:
                        cells.append((dx, "/", 3))
                    elif dx == h:
                        cells.append((dx, "\\", 3))
                    elif last:
                        cells.append((dx, rng.choice("_~._"), 0))
                    else:
                        cells.append((dx, rng.choice("^^^\"'~^;"),
                                      rng.choices([0, 1, 2], [3, 4, 3])[0]))
                self.rows.append((y, h, cells))
                y += 1
            self.tier_rows.append((first, y - 1, n, h0))
        self.base = y   # first row below the tree

        half_at = {}
        for (yy, h, _c) in self.rows:
            half_at[yy] = h
        self.half_at = half_at

        # ---- light strings (swags) ----
        lights = []
        for ti, (y0, y1, n, h0) in enumerate(self.tier_rows):
            swags = [y1 - 1]
            if ti == nt - 1:
                swags.append(y0 + 1)
            for yb in swags:
                h = half_at[yb]
                left, right = -(h - 1) + 1, (h - 1) - 1
                m = max(1, (right - left) // 3)
                for k in range(m + 1):
                    dx = int(round(left + k * (right - left) / float(m)))
                    yy = yb - (1 if (0 < k < m and h >= 5) else 0)
                    if abs(dx) <= half_at[yy] - 1:
                        lights.append((yy, dx))
        lights.sort()
        self.lights = [(yy, dx, rng.uniform(0, 6.28), self.LCOL[i % len(self.LCOL)])
                       for i, (yy, dx) in enumerate(lights)]
        light_cells = set((yy, dx) for (yy, dx) in lights)

        # ---- baubles ----
        cand = []
        for (yy, h, _c) in self.rows[2:]:
            for dx in range(-h + 2, h - 1):
                if (yy, dx) not in light_cells and (yy - 1, dx) not in light_cells:
                    cand.append((yy, dx))
        rng.shuffle(cand)
        chosen = []
        for (yy, dx) in cand:
            ok = True
            for (cy, cx_) in chosen:
                if (dx - cx_) ** 2 + (2 * (yy - cy)) ** 2 < 28:
                    ok = False
                    break
            if ok:
                chosen.append((yy, dx))
            if len(chosen) >= 26:
                break
        chosen.sort()
        self.balls = [(yy, dx, "O" if yy > self.TOP + 6 else "o",
                       self.OCOL[i % len(self.OCOL)], rng.uniform(0, 6.28))
                      for i, (yy, dx) in enumerate(chosen)]

    def draw(self, cv, t, reveal, lit):
        n = len(self.rows)
        # trunk
        if reveal > 0.05:
            for yy in (self.base, self.base + 1):
                cv.put(CX - 2, yy, "|", S(94))
                cv.put(CX + 2, yy, "|", S(94))
                for dx in (-1, 0, 1):
                    cv.put(CX + dx, yy, "#", S(130))
        full = {}
        for i, (yy, h, cells) in enumerate(self.rows):
            b = clamp((reveal * (n + 3) - i) / 3.0, 0.0, 1.0)
            full[yy] = b
            if b <= 0.0:
                continue
            lv = min(3, int(b * 3.999))
            pal = self.FOLIAGE[lv]
            for dx, ch, sh in cells:
                col = pal[sh] if sh < 3 else pal[2]
                cv.put(CX + dx, yy, ch, S(col, 1 if sh == 3 else 0))
        # lights
        nl = len(self.lights)
        mode = int(t / 9.0) % 3
        for i, (yy, dx, ph, col) in enumerate(self.lights):
            if full.get(yy, 0) < 0.99 or i >= lit * nl:
                continue
            if mode == 0:
                v = math.sin(t * 3.1 + ph * 5.0)
            elif mode == 1:
                v = math.sin(t * 5.0 - i * 0.7)
            else:
                v = 1.0 if (int(t * 2.0) + i) % 2 == 0 else -1.0
            if v > 0.35:
                cv.put(CX + dx, yy, "*", S(col, 1))
            elif v > -0.35:
                cv.put(CX + dx, yy, "+", S(col))
            else:
                cv.put(CX + dx, yy, ".", S(240))
        # baubles
        for (yy, dx, ch, col, ph) in self.balls:
            if full.get(yy, 0) < 0.99 or (yy - self.TOP) / float(n) > lit + 0.15:
                continue
            if math.sin(t * 1.9 + ph) > 0.985:
                cv.put(CX + dx, yy, "*", S(231, 1))
            else:
                cv.put(CX + dx, yy, ch, S(col, 1))

    def draw_star(self, cv, t, lit):
        if lit <= 0.0:
            return
        if lit < 1.0 and int(t * 14) % 2 == 1:
            return
        ray = 226 if int(t * 3) % 2 == 0 else 231
        y = self.TOP - 3
        cv.text(CX - 1, y, "\\|/", S(ray, 1))
        cv.text(CX - 2, y + 1, "--", S(220, 1))
        cv.put(CX, y + 1, "*" if int(t * 2) % 2 == 0 else "@", S(231, 1))
        cv.text(CX + 1, y + 1, "--", S(220, 1))
        cv.text(CX - 1, y + 2, "/|\\", S(ray, 1))
        sp = (t * 1.7) % 4.0
        for i, (dx, dy) in enumerate(((-5, 0), (5, 1), (-4, 2), (4, -1))):
            if int(sp) == i:
                cv.put(CX + dx, y + 1 + dy, "+", S(229, 1))


# ---------------------------------------------------------------------
#  Presents
# ---------------------------------------------------------------------
class Gift:
    def __init__(self, dx, w, h, box, rib, t0):
        self.x = CX + dx
        self.w, self.h = w, h
        self.box, self.rib = box, rib
        self.t0 = t0
        self.base = GIFT_BASE
        self.cx = self.x + w / 2.0
        self.sparked = False

    def visible(self, t):
        return t >= self.t0 + 0.7

    def draw(self, cv, t, fx):
        age = t - self.t0
        if age < 0:
            return
        dy = 0
        if age < 0.7:
            u = age / 0.7
            dy = -int(round(14 * (1 - u) ** 2))
        elif not self.sparked:
            self.sparked = True
            for _ in range(7):
                fx.emit(self.cx + random.uniform(-self.w / 2.0, self.w / 2.0),
                        self.base - self.h + random.uniform(-1, 1),
                        random.uniform(-3, 3), random.uniform(-3, -0.5), 0.9,
                        random.choice("*+"), SPARK_RAMP)
        w, h = self.w, self.h
        x0 = self.x
        top = self.base - h + 1 + dy
        mid = x0 + w // 2
        box = S(self.box)
        rib = S(self.rib, 1)
        cv.put(mid - 1, top, "\\", rib)
        cv.put(mid, top, "@", rib)
        cv.put(mid + 1, top, "/", rib)
        r = top + 1
        cv.put(x0, r, "[", box, True)
        for i in range(1, w - 1):
            cv.put(x0 + i, r, "=", box, True)
        cv.put(x0 + w - 1, r, "]", box, True)
        cv.put(mid, r, "#", rib)
        hr = top + 2 + (h - 4) // 2 if h >= 6 else -99
        for r in range(top + 2, top + h - 1):
            cv.put(x0, r, "|", box, True)
            cv.put(x0 + w - 1, r, "|", box, True)
            for i in range(1, w - 1):
                if r == hr:
                    cv.put(x0 + i, r, "-", rib, True)
                else:
                    cv.put(x0 + i, r, " ", box, True)
            cv.put(mid, r, "#", rib)
        r = top + h - 1
        cv.put(x0, r, "'", box, True)
        for i in range(1, w - 1):
            cv.put(x0 + i, r, "-", box, True)
        cv.put(x0 + w - 1, r, "'", box, True)
        cv.put(mid, r, "#", rib)


# (x offset from tree centre, width, height, box colour, ribbon colour)
GIFT_SPECS = [
    (-18, 11, 6, 160, 226),
    (4, 7, 6, 33, 231),
    (-27, 9, 5, 28, 196),
    (12, 9, 5, 135, 226),
    (21, 7, 4, 214, 196),
    (-6, 5, 3, 205, 231),
    (29, 5, 3, 45, 201),
]

# ---------------------------------------------------------------------
#  The cats' Christmas accessory: a red Santa hat with a white brim and
#  pompom, worn on the skin's "hat:" anchor (see skins/README-skins.md)
# ---------------------------------------------------------------------
SANTA_HAT = Accessory("santa_hat", [
    (0, -1, "{R}/#\\.{H}@"),
    (0, 0, "{H}==="),
], palette={"R": S(196, 1), "H": S(255, 1)})


# =====================================================================
#  The scene
# =====================================================================
class ChristmasScene(BaseScene):
    name = "christmas"
    title = "Merry Christmas"
    label = "聖誕節"
    order = 0

    CX = CX
    INTRO_END = INTRO_END
    GAZE = (CX, 9, 8, 10)          # a calm cat gazing at the tree makes it sparkle
    CAT_ACCESSORY = SANTA_HAT
    SETTINGS = {
        "greeting": "Merry Christmas, My Love!",
        "wish": "Every day with you feels like Christmas.",
        "surprise_at": 70.0,
        "every": 75.0,
        "hold": 30.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng)
        self.snow = Snow(rng)
        self.tree = Tree(rng)
        self.gifts = [Gift(dx, w, h, bc, rc, T_GIFT0 + i * T_GIFT_STEP)
                      for i, (dx, w, h, bc, rc) in enumerate(GIFT_SPECS)]
        self.floor = snowy_floor(rng)
        self.floor_extra = []
        self.pines = []
        self.star_fx = False

    def on_view(self, view):
        self.snow.set_view(view)
        self.floor_extra = snowy_floor(random.Random(3), self.margin_columns())
        # little snowy pines out in the margins of a wide window
        x0, _y0, x1, _y1 = view
        make = lambda r: (5, r.randint(5, 14), r.choice((PINE_S, PINE_S, PINE_L)))
        self.pines = (lay_out(random.Random(5), -3, x0, make, leftwards=True) +
                      lay_out(random.Random(6), CW + 3, x1, make))
    def update_scene(self, dt):
        self.snow.update(dt, self.t, min(1.0, 0.12 + self.t / 5.0))

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        self.snow.draw(cv)
        for (x, _w, art) in self.pines:
            art.draw(cv, x, 23 - art.h)
        draw_ground(cv, self.floor + self.floor_extra)
        reveal = clamp((t - T_TREE) / T_TREE_LEN, 0.0, 1.0)
        lit = clamp((t - T_LIGHTS) / T_LIGHTS_LEN, 0.0, 1.0)
        self.tree.draw(cv, t, reveal, lit)
        self.tree.draw_star(cv, t, clamp((t - T_STAR) / 1.2, 0.0, 1.0))
        if abs(t - T_STAR) < 0.05 or (t > T_STAR and not self.star_fx):
            self.star_fx = True
            for _ in range(10):
                self.fx.emit(CX, Tree.TOP - 2, random.uniform(-6, 6), random.uniform(-3, 3),
                             1.0, random.choice("*+"), SPARK_RAMP)

    def depth_items(self):
        return [(g.base, lambda cv, g=g: g.draw(cv, self.t, self.fx)) for g in self.gifts]

    def hideouts(self):
        return [g for g in self.gifts if g.visible(self.t)]
