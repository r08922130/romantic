# -*- coding: utf-8 -*-
"""
seoul.py - SeoulScene: N Seoul Tower, the Han River and Banpo Bridge
====================================================================

    python main.py --scene seoul

N Seoul Tower on Namsan hill changes colour, Lotte World Tower rises on the
right, the city twinkles, and Banpo Bridge's Moonlight Rainbow Fountain
pours rainbow water into the Han River. On the riverside walk: a love-lock
fence (like the one at Namsan) and a blue-and-red cheongsachorong lantern.
The cats wear a traditional gat (horsehair hat).
"""
import math
import random

from engine.cats import Accessory
from engine.effects import Starfield
from engine.render import CW, S, clamp, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop, sym

CX = CW // 2
HILL_X, HILL_TOP = 24, 11          # Namsan peak
BRIDGE = 18                        # Banpo Bridge deck row
RIVER_TOP, RIVER_BOT = 19, 22
RAINBOW = (196, 208, 226, 46, 51, 33, 129, 201)
TOWER_COLOURS = (33, 39, 129, 201, 213, 45)

N_TOWER = [sym("", "|"), sym("", "|"), sym("", "!"),
           sym("_", "|"), sym("(=", "="), sym("(_", "_"),
           sym("", "|"), sym("|", "="), sym("|", " "), sym("_|", "_")]

LOVE_LOCKS = Art([" _______ ",
                  "|o8o8o8o|",
                  "|8o8o8o8|",
                  "|_|___|_|"], default=S(244))
LOCK_COLOURS = (196, 213, 226, 51, 208, 141, 46, 218)
LANTERN = Art([" _^_ ",
               "(===)",
               "|:::|",
               "(===)",
               " '-' "],
              mask=[" BBB ", "BBBBB", "RRRRR", "RRRRR", " RRR "],
              palette={"B": S(33, 1), "R": S(196, 1)})

GAT = Accessory("gat", [(1, -1, "{G}n"), (-1, 0, "{G}=====")], palette={"G": S(242, 1)})


class SeoulScene(BaseScene):
    name = "seoul"
    title = "Seoul: N Seoul Tower and the Han River"
    label = "韓國首爾"
    order = 40

    INTRO_END = 8.0
    GAZE = (HILL_X, 3, 3, 7)
    CAT_ACCESSORY = GAT
    BANNER = {"ramp": (213, 219, 225, 231, 225, 219), "wish_colour": 219}
    SETTINGS = {
        "greeting": "Saranghae, My Love!",
        "wish": "Let's lock our love at Namsan Tower forever.",
        "surprise_at": 60.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=30, height=10)
        self.city = []
        x = 0
        while x < CW:
            w = rng.randint(3, 7)
            h = rng.randint(2, 6)
            if 60 <= x <= 70:
                h = rng.randint(2, 4)
            self.city.append((x, w, h, rng.uniform(0, 6.28)))
            x += w
        self.city_end = x
        self.city_extra = []
        self.hill = []
        for y in range(HILL_TOP, BRIDGE):
            half = int((y - HILL_TOP) * 3.2) + 2
            for xx in range(HILL_X - half, HILL_X + half + 1):
                if 0 <= xx < CW:
                    edge = abs(xx - HILL_X) >= half - 1
                    self.hill.append((xx, y, "^" if edge or rng.random() < 0.25 else "$",
                                      rng.choice((22, 28, 29))))
        self.locks = [rng.choice(LOCK_COLOURS) for _ in range(20)]
        self.props = [Prop(LOVE_LOCKS, 12, 24, self.lock_colour), Prop(LANTERN, 60, 24)]

    def on_view(self, view):
        """A wide window: the city goes on along the river to both edges."""
        x0, _y0, x1, _y1 = view
        rng = random.Random(6)
        make = lambda r: (r.randint(3, 7), 0, (r.randint(2, 6), r.uniform(0, 6.28)))
        self.city_extra = [(x, w, h, ph) for (x, w, (h, ph)) in
                           lay_out(rng, 0, x0, make, leftwards=True) +
                           lay_out(rng, self.city_end, x1, make)]

    def lock_colour(self, t, dx, dy, ch, st):
        if ch in "o8":
            return S(self.locks[(dx + dy * 7) % len(self.locks)], 1)
        return st

    # ---------------- pieces ----------------
    def draw_city(self, cv, t):
        for (x, w, h, ph) in self.city + self.city_extra:
            top = BRIDGE - h
            for y in range(top, BRIDGE):
                for xx in range(x, x + w):
                    if y == top:
                        cv.put(xx, y, "_", S(239))
                    else:
                        on = math.sin(t * 0.25 + ph + xx * 2.1 + y * 1.3) > 0.2
                        cv.put(xx, y, "." if on else " ", S(222 if on else 236), True)

    def draw_lotte(self, cv, t):
        """Lotte World Tower: slender, tapering, with a split crown."""
        cx, top = 66, 2
        cv.put(cx, top - 1, "*", S(196, 1) if int(t * 1.5) % 2 else S(52))
        cv.text(cx - 1, top, "/|\\", S(252, 1))
        for y in range(top + 1, BRIDGE):
            half = 1 + (y - top) // 6
            cv.put(cx - half, y, "/" if (y - top) % 6 == 0 else "|", S(250))
            cv.put(cx + half, y, "\\" if (y - top) % 6 == 0 else "|", S(250))
            for xx in range(cx - half + 1, cx + half):
                lit = math.sin(t * 0.5 + y * 0.7 + xx) > -0.3
                cv.put(xx, y, ":" if lit else " ", S(117 if lit else 236), True)

    def draw_n_tower(self, cv, t):
        lit = t > 3.0
        col = TOWER_COLOURS[int(t / 6.0) % len(TOWER_COLOURS)]
        top = HILL_TOP - len(N_TOWER) + 1
        for dy, row in enumerate(N_TOWER):
            x0 = HILL_X - len(row) // 2
            for dx, ch in enumerate(row):
                if ch == " ":
                    continue
                if ch == "!":
                    st = S(196, 1) if int(t * 2) % 2 else S(255, 1)
                elif ch in "(=_)" and dy in (4, 5):        # observation deck
                    st = S(229, 1) if lit and int(t * 3 + dx) % 8 else S(231, 1)
                else:
                    st = S(col, 1) if lit else S(244)
                cv.put(x0 + dx, top + dy, ch, st)

    def draw_river(self, cv, t):
        for x in cv.xs():
            cv.put(x, BRIDGE, "=", S(248))
            if x % 6 == 0:
                for y in range(RIVER_TOP, RIVER_BOT + 1):
                    cv.put(x, y, "|", S(240))
        for y in range(RIVER_TOP, RIVER_BOT + 1):
            for x in cv.xs():
                v = math.sin(x * 0.5 + t * 1.3 + y * 1.7)
                if v > 0.6:
                    cv.put(x, y, "~", S(24 if y > RIVER_TOP + 1 else 31))
        # Moonlight Rainbow Fountain: arcs of water pouring off the bridge
        show = t > 4.0 and (t % 40.0) < 30.0
        if show:
            start = cv.x0 + (2 - cv.x0) % 6            # every 6th column, as on the stage
            for i, x0 in enumerate(range(start, cv.x1 - 2, 6)):
                col = S(RAINBOW[(i + int(t * 2.0)) % len(RAINBOW)], 1)
                flow = int(t * 6) % 2
                for k, (dx, dy, ch) in enumerate(((1, 1, "\\"), (2, 2, "\\"), (2, 3, "|"),
                                                  (3, 4, ":" if flow else "."))):
                    if RIVER_TOP - 1 + dy <= RIVER_BOT + 1:
                        cv.put(x0 + dx, BRIDGE + dy, ch, col)
        pat = "-_-_"
        for x in cv.xs():
            cv.put(x, 23, pat[x % len(pat)], S(245))

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        for dy, row in enumerate((" .-. ", "(   )", " `-' ")):
            cv.text(50, 2 + dy, row, S(230, 1))
        self.draw_city(cv, t)
        self.draw_lotte(cv, t)
        grow = clamp(t / 3.0, 0.0, 1.0)
        for (x, y, ch, col) in self.hill:
            if (y - HILL_TOP) <= grow * (BRIDGE - HILL_TOP):
                if ch == "$":
                    cv.put(x, y, " ", S(col), True)        # opaque: hides the city
                else:
                    cv.put(x, y, ch, S(col))
        self.draw_n_tower(cv, t)
        self.draw_river(cv, t)

    def depth_items(self):
        return [(p.base, lambda cv, p=p: p.draw(cv, self.t)) for p in self.props]

    def hideouts(self):
        return self.props
