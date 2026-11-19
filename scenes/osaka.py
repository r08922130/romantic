# -*- coding: utf-8 -*-
"""
osaka.py - OsakaScene: Osaka Castle at night in cherry-blossom season
=====================================================================

    python main.py --scene osaka

The castle keep (green roofs, white walls, golden shachihoko, lit windows)
on its stone base, two cherry trees in full bloom, petals drifting down,
glowing stone lanterns. The cats wear a little sakura flower crown.
"""
import math
import random

from engine.cats import Accessory
from engine.effects import Starfield
from engine.render import CH, CW, S, clamp, hash01, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop, sym

CX = CW // 2
PINKS = (218, 217, 211, 224, 225, 212)

# ---------------------------------------------------------------------
#  The castle keep: built from mirrored left halves so it is symmetric
# ---------------------------------------------------------------------
H = 17
CASTLE_ROWS = [
    sym("w)___", "_", H),
    sym("/_____", "_", H),
    sym("/__/___", "_", H),
    sym("|$$[]", "$", H),
    sym("___|____", "_", H),
    sym("/__/____/", "^", H),
    sym("|$[]$[]", "$", H),
    sym("_____|______", "_", H),
    sym("/___/____/___", "_", H),
    sym("|$$[]$[]", "$", H),
    sym("_____|_________", "_", H),
    sym("/____/______/____", "_", H),
    sym("|[]$[]$[]$[]", "$", H),
    sym("|------------", "-", H),
    sym("(=#=#=#=#=#=#=", "#", H),
    sym("(#=#=#=#=#=#=#=#", "=", H),
    sym("(=#=#=#=#=#=#=#=#", "#", H),
]
GREEN, WHITE, GOLD = S(36, 1), S(255, 1), S(220, 1)
CASTLE = Art(CASTLE_ROWS, charmap={
    "_": GREEN, "/": GREEN, "\\": GREEN,
    "|": WHITE, "-": WHITE, "$": WHITE,
    "[": S(250), "]": S(250),
    "w": GOLD, "^": GOLD,
    "(": S(246), ")": S(246), "#": S(244), "=": S(240),
})
CASTLE_X, CASTLE_Y = CX - H, 22 - len(CASTLE_ROWS) + 1     # bottom on row 22

LANTERN = Art([" /^\\ ",
               "(===)",
               " |o| ",
               " _|_ ",
               "[___]"], charmap={"o": S(228, 1)}, default=S(247))

MOON = Art([" .-. ", "( . )", " `-' "], default=S(230, 1))

SAKURA = Accessory("sakura", [(0, 0, "{P}*{Y}@{P}*")],
                   palette={"P": S(218, 1), "Y": S(226, 1)})


class Petals:
    """Cherry-blossom petals drifting down and sideways."""

    def __init__(self, rng, n=55):
        self.p = [[rng.uniform(0, CW), rng.uniform(0, CH), rng.uniform(0.8, 1.8),
                   rng.uniform(0, 6.28), rng.choice("*.'`,"), rng.choice(PINKS)]
                  for _ in range(n)]
        self.n = 0
        self.base = n
        self.view = (0, 0, CW, CH)

    def set_view(self, view):
        """A bigger window gets more petals (same density), drifting over all of it."""
        self.view = view
        x0, y0, x1, _y1 = view
        want = int(self.base * (x1 - x0) * (CH - y0) / float(CW * CH))
        rng = random.Random(len(self.p))
        while len(self.p) < want:
            self.p.append([rng.uniform(x0, x1), rng.uniform(y0, CH), rng.uniform(0.8, 1.8),
                           rng.uniform(0, 6.28), rng.choice("*.'`,"), rng.choice(PINKS)])

    def update(self, dt, t, amount):
        self.n = int(len(self.p) * amount)
        x0, y0, x1, _y1 = self.view
        for p in self.p[:self.n]:
            p[1] += p[2] * dt
            p[0] += (math.sin(t * 0.9 + p[3]) * 1.6 + 0.9) * dt
            if p[1] >= CH:
                p[1] = y0 - 1.0
                p[0] = random.uniform(x0 - 10, x1)
            if p[0] >= x1:
                p[0] -= x1 - x0

    def draw(self, cv):
        for p in self.p[:self.n]:
            cv.put(int(p[0]), int(p[1]), p[4], S(p[5]))


class CherryTree:
    def __init__(self, rng, cx, cy, rx, ry):
        self.cx, self.cy = cx, cy
        self.cells = []
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                d = ((x - cx) / float(rx)) ** 2 + ((y - cy) / float(ry)) ** 2
                if d <= 1.0 and rng.random() < (0.95 if d < 0.6 else 0.6):
                    self.cells.append((x, y, rng.choice("@*o%&8"), rng.choice(PINKS),
                                       rng.uniform(0, 6.28), d))
        self.trunk_top = cy + ry - 1

    def draw(self, cv, t, bloom):
        bark = S(94)
        for y in range(self.trunk_top, 23):
            cv.put(self.cx, y, "|", bark)
            cv.put(self.cx + 1, y, "|", bark)
        cv.put(self.cx - 1, self.trunk_top + 1, "\\", bark)
        cv.put(self.cx + 2, self.trunk_top + 1, "/", bark)
        for (x, y, ch, col, ph, d) in self.cells:
            if d > bloom * 1.2:
                continue
            v = math.sin(t * 0.7 + ph)
            cv.put(x, y, ch, S(231 if v > 0.97 else col, 1 if v > 0.3 else 0))


class OsakaScene(BaseScene):
    name = "osaka"
    title = "Osaka Castle under the cherry blossoms"
    label = "大阪城"
    order = 10

    INTRO_END = 10.0
    GAZE = (CX, 10, 8, 10)
    CAT_ACCESSORY = SAKURA
    BANNER = {"ramp": (218, 225, 231, 225, 218, 212), "wish_colour": 224}
    SETTINGS = {
        "greeting": "Osaka is sweeter with you, My Love!",
        "wish": "Let's walk under the cherry blossoms together.",
        "surprise_at": 60.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=30, height=12)
        self.petals = Petals(rng)
        self.trees = [CherryTree(rng, 8, 13, 9, 5), CherryTree(rng, 69, 12, 10, 5)]
        self.floor = []
        for y in range(24, CH):
            for x in range(CW):
                v = rng.random()
                if v < 0.07:
                    self.floor.append((x, y, ".", rng.choice((217, 224, 218))))
                elif v < 0.10:
                    self.floor.append((x, y, ".", 240))
        self.windows = [rng.uniform(0, 6.28) for _ in range(64)]
        self.lanterns = [Prop(LANTERN, 19, 24, self.lantern_glow),
                         Prop(LANTERN, 55, 24, self.lantern_glow)]
        self.extra_trees, self.floor_extra = [], []

    def on_view(self, view):
        """A wide window: more cherry trees and petals out in the margins."""
        self.petals.set_view(view)
        x0, _y0, x1, _y1 = view
        rng = random.Random(4)
        self.floor_extra = []
        for y in range(24, CH):
            for x in self.margin_columns():
                v = hash01(x, y, 4)
                if v < 0.07:
                    self.floor_extra.append((x, y, ".", (217, 224, 218)[int(v * 100) % 3]))
                elif v < 0.10:
                    self.floor_extra.append((x, y, ".", 240))
        make = lambda r: (r.randint(16, 22), r.randint(2, 8), r.randint(4, 5))
        spots = lay_out(rng, -12, x0 - 12, make, leftwards=True) + lay_out(rng, CW + 13, x1 + 12, make)
        self.extra_trees = [CherryTree(rng, x + w // 2, 18 - ry, w // 2, ry)
                            for (x, w, ry) in spots]

    def lantern_glow(self, t, dx, dy, ch, st):
        if ch == "o":
            return S(228 if math.sin(t * 5.0 + dx) > -0.6 else 222, 1)
        return st

    def update_scene(self, dt):
        self.petals.update(dt, self.t, clamp(self.t / 6.0, 0.15, 1.0))

    def castle_light(self, dx, dy, ch, st):
        t = self.t
        if ch in "[]":                       # windows light up one by one
            k = (dy * 7 + dx) % len(self.windows)
            on = t > 2.0 + (k % 12) * 0.5
            if not on:
                return S(238)
            return S(229 if math.sin(t * 0.6 + self.windows[k]) > -0.7 else 222, 1)
        if ch in "w^" and int(t * 2.5 + dx) % 7 == 0:
            return S(231, 1)                 # golden glints
        return st

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        MOON.draw(cv, 4, 3)
        CASTLE.draw(cv, CASTLE_X, CASTLE_Y, self.castle_light)
        bloom = clamp(t / 5.0, 0.0, 1.0)
        for tree in self.trees + self.extra_trees:
            tree.draw(cv, t, bloom)
        pat = "-.-'.-.-"
        for x in cv.xs():
            cv.put(x, 23, pat[x % len(pat)], S(244))
        for (x, y, c, col) in self.floor + self.floor_extra:
            cv.put(x, y, c, S(col))
        self.petals.draw(cv)

    def depth_items(self):
        return [(p.base, lambda cv, p=p: p.draw(cv, self.t)) for p in self.lanterns]

    def hideouts(self):
        return self.lanterns
