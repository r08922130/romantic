# -*- coding: utf-8 -*-
"""
tokyo.py - TokyoScene: Tokyo Skytree over the city at night
===========================================================

    python main.py --scene tokyo

The Skytree (lattice tower, two observatories) changes between its "Iki"
(sky blue) and "Miyabi" (purple) illumination with a light sweeping up the
tower; office windows switch on and off; red aviation lights blink; now and
then a shooting star. A vending machine and a red post box stand on the
street. The cats wear a cosy beanie.
"""
import math
import random

from engine.cats import Accessory
from engine.effects import SPARK_RAMP, Starfield
from engine.render import CW, S, clamp, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop, sym

CX = CW // 2

# the tower, top (row 2) to bottom (row 22); X = lattice, = / ( ) = observatories
TOWER_ROWS = [
    sym("", "|"), sym("", "|"), sym("", "|"),
    sym("_", "|"),
    sym("(=", "="),
    sym("|", "X"), sym("|", "X"), sym("|", "X"), sym("|", "X"),
    sym("_/=", "="),
    sym("(===", "="),
    sym("(___", "_"),
    sym("|X", "X"), sym("|X", "X"), sym("|X", "X"),
    sym("/XX", "X"),
    sym("/XXX", "X"),
    sym("/XXXX", "X"),
    sym("/XXX/ ", " "),
    sym("/XX/   ", " "),
    sym("/X/     ", " "),
]
TOWER_TOP = 2
IKI = (153, 117, 81, 45, 39, 33)       # sky blue
MIYABI = (225, 183, 177, 141, 135, 99)  # purple

VENDING = Art([".----.",
               "|[##]|",
               "|o o:|",
               "|____|",
               "'----'"],
              mask=["WWWWWW",
                    "WLLLLW",
                    "WBBBBW",
                    "WWWWWW",
                    "WWWWWW"],
              palette={"W": S(252, 1), "L": S(229, 1), "B": S(196, 1)})
POSTBOX = Art([" __ ",
               "|==|",
               "|[]|",
               "|__|"], default=S(196, 1))

BEANIE = Accessory("beanie", [(0, -1, " {W}o"), (0, 0, "{B}===")],
                   palette={"B": S(33, 1), "W": S(255, 1)})


class City:
    """Office blocks with windows that switch on and off."""

    def __init__(self, rng, spans=None):
        """spans=None: the stage. Else [(start, stop, leftwards), ...]: blocks
        out in the margins of a wide window (see render.lay_out)."""
        self.blocks = []
        x = 0
        if spans is None:
            while x < CW:
                w = rng.randint(5, 9)
                if x < CX + 10 and x + w > CX - 10:       # keep the tower's feet clear
                    x = CX + 10
                    continue
                h = rng.randint(5, 12)
                self.blocks.append((x, w, h, rng.random() < 0.45))
                x += w + rng.choice((0, 0, 1))
        else:
            make = lambda r: (r.randint(5, 9), r.choice((0, 0, 1)),
                              (r.randint(4, 12), r.random() < 0.45))
            for start, stop, left in spans:
                self.blocks += [(bx, bw, h, av) for (bx, bw, (h, av))
                                in lay_out(rng, start, stop, make, leftwards=left)]
        self.end = x                                   # where the stage's blocks end
        self.win = {}
        for (x, w, h, _a) in self.blocks:
            for yy in range(22 - h + 2, 22, 2):
                for xx in range(x + 1, x + w - 1, 2):
                    self.win[(xx, yy)] = (rng.uniform(0, 6.28), rng.uniform(0.05, 0.25),
                                          rng.choice((229, 223, 230, 195)))

    def draw(self, cv, t, power):
        edge = S(240)
        for (x, w, h, aviation) in self.blocks:
            top = 22 - h + 1
            for xx in range(x, x + w):
                cv.put(xx, top, "_", edge)
                for yy in range(top + 1, 23):
                    cv.put(xx, yy, " ", edge, True)
            for yy in range(top + 1, 23):
                cv.put(x, yy, "|", edge)
                cv.put(x + w - 1, yy, "|", edge)
            if aviation and h >= 9 and int(t * 1.2 + x) % 3 == 0:
                cv.put(x + w // 2, top - 1, "*", S(196, 1))
        for (xx, yy), (ph, sp, col) in self.win.items():
            lit = math.sin(t * sp + ph) > 0.1 - power
            cv.put(xx, yy, ":" if lit else ".", S(col, 1) if lit else S(237))


class TokyoScene(BaseScene):
    name = "tokyo"
    title = "Tokyo Skytree at night"
    label = "東京晴空塔"
    order = 20

    INTRO_END = 8.0
    GAZE = (CX, 3, 4, 12)
    CAT_ACCESSORY = BEANIE
    BANNER = {"ramp": (153, 159, 195, 231, 195, 183), "wish_colour": 183}
    SETTINGS = {
        "greeting": "You light up my Tokyo nights, My Love!",
        "wish": "Higher than the Skytree - that's how much I love you.",
        "surprise_at": 60.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=26, height=10)
        self.city = City(rng)
        self.props = [Prop(VENDING, 12, 24), Prop(POSTBOX, 63, 24)]
        self.next_meteor = 9.0
        self.margin_city = None

    def on_view(self, view):
        x0, _y0, x1, _y1 = view
        self.margin_city = City(random.Random(9), [(-1, x0, True), (self.city.end, x1, False)])

    def update_scene(self, dt):
        if self.t > self.next_meteor:
            self.next_meteor = self.t + random.uniform(6.0, 12.0)
            x0, _y0, x1, _y1 = self.view
            x, y = random.uniform(x0 + 20, x1 - 5), random.uniform(2, 6)
            for k in range(6):
                self.fx.emit(x + k * 1.6, y - k * 0.5, -14.0, 5.0, 0.5 + k * 0.08,
                             "*" if k == 0 else ".", SPARK_RAMP)

    def tower_colour(self, dy, ch):
        t = self.t
        if t < 4.0:
            return S(240)
        ramp = IKI if int(t / 15.0) % 2 == 0 else MIYABI
        if ch in "=()_":                        # observatory glass
            return S(195, 1) if int(t * 2 + dy) % 9 else S(231, 1)
        sweep = (t * 6.0) % 30.0                # a band of light runs up the tower
        dist = abs((len(TOWER_ROWS) - dy) - sweep)
        i = clamp(int(dist), 0, len(ramp) - 1)
        return S(ramp[i], 1 if i < 2 else 0)

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        for dy, row in enumerate(TOWER_ROWS):
            x0 = CX - len(row) // 2
            for dx, ch in enumerate(row):
                if ch != " ":
                    cv.put(x0 + dx, TOWER_TOP + dy, ch, self.tower_colour(dy, ch))
        if int(t * 1.5) % 2 == 0:
            cv.put(CX, TOWER_TOP - 1, "*", S(196, 1))       # aviation light on top
        power = clamp(t / 6.0, 0.0, 1.0) * 1.1 - 0.5
        self.city.draw(cv, t, power)
        if self.margin_city is not None:
            self.margin_city.draw(cv, t, power)
        pat = "=-=-"
        for x in cv.xs():
            cv.put(x, 23, pat[x % len(pat)], S(242))

    def depth_items(self):
        return [(p.base, lambda cv, p=p: p.draw(cv, self.t)) for p in self.props]

    def hideouts(self):
        return self.props
