# -*- coding: utf-8 -*-
"""
busan.py - BusanScene: Gwangalli beach and Gwangan Bridge at night
==================================================================

    python main.py --scene busan

Gwangan Bridge (suspension bridge with two towers) glows in changing rainbow
colours over the sea, Marine City's towers shine on the right, the moon and
the bridge lights shimmer on the waves, fireworks go up over the water, and
the cats play on the sand by a sandcastle. They wear straw sun hats.
"""
import math
import random

from engine.cats import Accessory
from engine.effects import Fireworks, Starfield
from engine.render import CW, S, hash01, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop

CX = CW // 2
DECK = 13                       # bridge deck row
TOWERS = (22, 55)               # bridge tower columns (left edge, 3 wide)
TOWER_TOP = 4
SEA_TOP, SEA_BOT = 15, 22
RAINBOW = (196, 208, 226, 46, 51, 33, 129, 201)

SANDCASTLE = Art(["   |> ",
                  " []|[]",
                  "[_:_:_]",
                  "[_____]"],
                 mask=["   FR  ", "       ", "       ", "       "],
                 palette={"F": S(250), "R": S(196, 1)}, default=S(222))
PARASOL = Art([" .-^-. ",
               "/_\\_/_\\",
               "   |   ",
               "   |   ",
               "  _|_  "],
              mask=["RWRWRWR", "RWRWRWR", "", "", ""],
              palette={"R": S(196, 1), "W": S(255, 1)}, default=S(250))

STRAW_HAT = Accessory("straw_hat", [(0, -1, "{Y}/^\\"), (-1, 0, "{Y}-{R}==={Y}-")],
                      palette={"Y": S(222, 1), "R": S(196, 1)})


def cable_y(x):
    """Main cable: high at the towers, sagging in the middle and side spans."""
    l, r = TOWERS[0] + 1, TOWERS[1] + 1
    if l <= x <= r:
        u = (x - l) / float(r - l) * 2 - 1           # -1 .. 1 between towers
        return TOWER_TOP + 1 + (1 - u * u) * 6.0
    end = 0 if x < l else CW - 1
    near = l if x < l else r
    u = abs(x - near) / float(abs(end - near) or 1)
    return TOWER_TOP + 1 + u * (DECK - 1 - TOWER_TOP - 1)


class Skyline:
    """Marine City towers on the right, Hwangnyeongsan hill on the left."""

    def __init__(self, rng):
        self.towers = []
        x = 61
        while x < CW - 2:
            w = rng.randint(3, 5)
            h = rng.randint(6, 10)
            self.towers.append((x, w, h, rng.uniform(0, 6.28)))
            x += w + 1
        self.end = x
        self.extra = []

    def set_view(self, x1):
        """A wide window: Marine City goes on to the right edge."""
        make = lambda r: (r.randint(3, 5), r.choice((1, 1, 2, 3)),
                          (r.randint(4, 10), r.uniform(0, 6.28)))
        self.extra = [(x, w, h, ph)
                      for (x, w, (h, ph)) in lay_out(random.Random(8), self.end, x1, make)]

    def draw(self, cv, t):
        hill = S(23)
        for x in range(min(cv.x0, 0), 20):
            if x >= 0:
                top = int(DECK - 1 - 4 * math.sin(math.pi * x / 22.0))
            else:                                       # rolling hills further left
                top = int(DECK - 1 - 2.5 - 1.5 * math.sin(x * 0.13))
            for y in range(top, DECK):
                cv.put(x, y, "^" if y == top else " ", hill, y != top)
        for (x, w, h, ph) in self.towers + self.extra:
            top = DECK - h
            for y in range(top, DECK):
                for xx in range(x, x + w):
                    edge = xx in (x, x + w - 1)
                    if y == top:
                        cv.put(xx, y, "_", S(244))
                    elif edge:
                        cv.put(xx, y, "|", S(240))
                    else:
                        on = math.sin(t * 0.3 + ph + xx * 1.7 + y * 2.3) > -0.2
                        cv.put(xx, y, ":" if on else ".", S(117 if on else 238))


class BusanScene(BaseScene):
    name = "busan"
    title = "Busan: Gwangalli beach and Gwangan Bridge"
    label = "韓國釜山"
    order = 30

    INTRO_END = 8.0
    GAZE = (CX, 14, 8, 4)
    CAT_ACCESSORY = STRAW_HAT
    BANNER = {"ramp": (51, 87, 123, 159, 195, 123), "wish_colour": 159}
    SETTINGS = {
        "greeting": "Busan by the sea with you, My Love!",
        "wish": "Let's watch the waves and the fireworks together.",
        "surprise_at": 60.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=30, height=9)
        self.skyline = Skyline(rng)
        self.props = [Prop(SANDCASTLE, 17, 24), Prop(PARASOL, 59, 24)]
        self.sand = [(x, y, rng.choice(".,'`"), rng.choice((180, 186, 223, 144)))
                     for y in range(24, 27) for x in range(CW) if rng.random() < 0.25]
        self.next_fw = 6.0
        self.fireworks = None            # needs self.fx, made on first update
        self.sand_extra = []

    def on_view(self, view):
        x0, _y0, x1, _y1 = view
        self.skyline.set_view(x1)
        self.sand_extra = [(x, y, ".,'`"[int(hash01(x, y, 2) * 4)],
                            (180, 186, 223, 144)[int(hash01(x, y, 3) * 4)])
                           for y in range(24, 27) for x in self.margin_columns()
                           if hash01(x, y, 1) < 0.25]

    # ---------------- fireworks ----------------
    def update_scene(self, dt):
        if self.fireworks is None:
            self.fireworks = Fireworks(self.fx)
        if self.t > self.next_fw:
            self.next_fw = self.t + random.uniform(2.5, 6.0)
            x0, _y0, x1, _y1 = self.view
            self.fireworks.launch(random.uniform(x0 + 8, x1 - 8), SEA_TOP - 1,
                                  random.uniform(2.5, 6.5))
        self.fireworks.update(dt)

    # ---------------- drawing ----------------
    def bridge_colour(self, x, y):
        t = self.t
        if t < 3.0:
            return S(240)
        mode = int(t / 12.0) % 3
        if mode == 0:                                       # rainbow flowing along
            return S(RAINBOW[int(x / 4.0 + t * 3.0) % len(RAINBOW)], 1)
        if mode == 1:                                       # one colour, pulsing
            return S(RAINBOW[int(t / 2.0) % len(RAINBOW)], 1 if math.sin(t * 4) > 0 else 0)
        return S(RAINBOW[(x // 8) % len(RAINBOW)] if int(t * 3 + x / 6) % 2 else 231, 1)

    def draw_bridge(self, cv):
        for x in range(CW):                                 # cables + hangers
            cy = cable_y(x)
            y0 = int(round(cy))
            st = self.bridge_colour(x, y0)
            cv.put(x, y0, "~", st)
            if x % 3 == 0:
                for y in range(y0 + 1, DECK):
                    cv.put(x, y, "|", S(240))
        for tx in TOWERS:                                   # towers
            for y in range(TOWER_TOP, DECK + 2):
                cv.put(tx, y, "|", S(250, 1))
                cv.put(tx + 2, y, "|", S(250, 1))
                cv.put(tx + 1, y, "=" if (y - TOWER_TOP) % 3 == 0 else " ", S(250), True)
            cv.put(tx + 1, TOWER_TOP - 1, "*", S(196, 1) if int(self.t * 1.5) % 2 else S(52))
        for x in cv.xs():                                   # double deck (+ the approach roads)
            cv.put(x, DECK, "=", self.bridge_colour(x, DECK))
            cv.put(x, DECK + 1, "-", S(244))

    def draw_sea(self, cv):
        t = self.t
        for y in range(SEA_TOP, SEA_BOT + 1):
            depth = (y - SEA_TOP) / float(SEA_BOT - SEA_TOP)
            for x in cv.xs():
                v = math.sin(x * 0.45 + t * 1.6 + y * 1.3) + math.sin(x * 0.17 - t * 0.9)
                if v > 1.1:
                    cv.put(x, y, "~", S(31 if depth > 0.5 else 25))
                elif v > 0.3:
                    cv.put(x, y, "-", S(24))
        # reflections: moon column + bridge lights shimmering under the deck
        for y in range(SEA_TOP, SEA_BOT):
            if math.sin(t * 3 + y * 2.1) > -0.3:
                cv.put(9 + int(math.sin(t * 2 + y) * 1.5), y, "=", S(229))
        for x in range(cv.x0 - cv.x0 % 3, cv.x1, 3):
            for y in range(SEA_TOP, SEA_TOP + 3):
                if math.sin(t * 4 + x * 0.9 + y * 2.0) > 0.4:
                    cv.put(x, y, "'", self.bridge_colour(x, DECK))
        # foam on the shore
        for x in cv.xs():
            v = math.sin(x * 0.3 - t * 1.2)
            cv.put(x, 23, "~" if v > 0.2 else ("." if v > -0.5 else "_"),
                   S(255, 1) if v > 0.6 else S(152))

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        for dy, row in enumerate((" .-. ", "(   )", " `-' ")):
            cv.text(7, 2 + dy, row, S(230, 1))
        if self.fireworks is not None:
            self.fireworks.draw(cv)
        self.skyline.draw(cv, t)
        self.draw_bridge(cv)
        self.draw_sea(cv)
        for (x, y, c, col) in self.sand + self.sand_extra:
            cv.put(x, y, c, S(col))

    def depth_items(self):
        return [(p.base, lambda cv, p=p: p.draw(cv, self.t)) for p in self.props]

    def hideouts(self):
        return [self.props[0]]           # hide behind the sandcastle
