# -*- coding: utf-8 -*-
"""
pohang.py - PohangScene: sunrise at Homigot and the Guryongpo street
====================================================================

    python main.py --scene pohang

Right: the Hand of Harmony (상생의 손) rises out of the sea at Homigot, the
sun comes up and ends up "held" above its fingers, gulls sit on the
fingertips, the Homigot lighthouse blinks on the rocks.
Left: Guryongpo's old Japanese-style wooden houses and the long stone stairs
up the hill - where "When the Camellia Blooms" (동백꽃 필 무렵) was filmed,
with the "Camellia" bar sign. Camellia bushes drop whole red blossoms, which
stay on the ground for a while. The cats wear a camellia flower.
"""
import math
import random

from engine.cats import Accessory
from engine.effects import Starfield
from engine.render import CH, CW, S, clamp, hash01, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop

CX = CW // 2
SEA_TOP, SEA_BOT = 14, 22           # horizon .. last sea row (ground is row 23)
HAND_X, HAND_Y = 52, 9              # top-left of the hand art
SUN_CX = HAND_X + 10                # the sun rises right behind the hand
STAIRS_CX = 17
RED = (160, 196, 124, 197)          # camellia reds


def solid(rows):
    """Spaces enclosed by the drawing become '$' (opaque), so the sky or sea
    does not show through. The bottom edge counts as closed (the wrist stands
    in the water)."""
    w = max(len(r) for r in rows)
    g = [list(r.ljust(w)) for r in rows]
    h = len(g)
    seen = set()
    stack = [(x, 0) for x in range(w)] + [(0, y) for y in range(h)] + \
            [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or (x, y) in seen or g[y][x] != " ":
            continue
        seen.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return ["".join("$" if (c == " " and (x, y) not in seen) else c
                    for x, c in enumerate(row)).rstrip() for y, row in enumerate(g)]


# ---------------------------------------------------------------------
#  The Hand of Harmony: a bronze right hand, fingers up, thumb out
# ---------------------------------------------------------------------
HAND = Art(solid([
    "          _",
    "     _   | |   _",
    "    | |  | |  | |",
    "    | |  | |  | |  _",
    " _  | |  | |  | | | |",
    "\\ \\ | |  | |  | | | |",
    " \\ \\| |__| |__| |/ /",
    "  \\  '    '    '  /",
    "   \\             /",
    "    \\           /",
    "     |         |",
    "     |         |",
]), charmap={"'": S(94)}, default=S(172, 1))
# where gulls stand: (left column, top row) of the index, middle and little finger
FINGERTIPS = [(HAND_X + 4, HAND_Y + 1), (HAND_X + 10, HAND_Y), (HAND_X + 18, HAND_Y + 3)]
SUN = ["   .---.", " .'     '.", "(         )"]

LIGHTHOUSE = Art([" _^_",
                  " |o|",
                  " |=|",
                  " | |",
                  " |=|",
                  "/___\\",
                  "~^^^^~"],
                 mask=["", " WLW", " W W", " W W", " W W", "WWWWW", "RRRRRR"],
                 palette={"W": S(255, 1), "L": S(228, 1), "R": S(240)}, default=S(250))

# ---------------------------------------------------------------------
#  Guryongpo: old Japanese-style wooden houses and the stone stairs
# ---------------------------------------------------------------------
HOUSE_ROWS = [
    "  _________",
    " /_/_/_/_/_\\",
    "/___________\\",
    " |[+][+][+]|",
    " |=========|",
    "/___________\\",
    " |[]  ||  []|",
    " |    ||    |",
    " |____||____|",
]
HOUSE_MASK = ["RRRRRRRRRRRRR", "RRRRRRRRRRRRR", "RRRRRRRRRRRRR", " WLLLLLLLLLW",
              " WBBBBBBBBBW", "RRRRRRRRRRRRR", " WLLWWWWWWLLW", " WWWWWWWWWWWW", " WWWWWWWWWWWW"]
HOUSE = Art(solid(HOUSE_ROWS), mask=HOUSE_MASK,
            palette={"R": S(243), "W": S(130), "L": S(222, 1), "B": S(137)})

BUSH = Art(solid([" .&@&&.",
                  "&@&&&@&&",
                  "&&&@&&@&",
                  "`&@&&&&'"]),
           charmap={"&": S(28), ".": S(22), "`": S(22), "'": S(22), "@": S(196, 1)})

CAMELLIA = Accessory("camellia", [(0, 0, "{G}~{R}@{G}~")],
                     palette={"G": S(34, 1), "R": S(196, 1)})


class FallingCamellias:
    """Camellias drop as whole flowers - straight down, then lie on the
    ground a while before they fade."""

    def __init__(self):
        self.falling = []          # [x, y, vy, land_row]
        self.ground = []           # [x, y, age]

    def drop(self, x, y):
        self.falling.append([x, y, random.uniform(2.5, 4.0), random.choice((24, 25, 26))])

    def update(self, dt):
        for f in self.falling:
            f[1] += f[2] * dt
            f[0] += math.sin(f[1] * 2.0) * 0.6 * dt
            if f[1] >= f[3]:
                self.ground.append([f[0], f[3], 0.0])
        self.falling = [f for f in self.falling if f[1] < f[3]]
        for g in self.ground:
            g[2] += dt
        self.ground = [g for g in self.ground if g[2] < 30.0][-40:]

    def draw(self, cv, t):
        for (x, y, _vy, _l) in self.falling:
            cv.put(int(x), int(y), "@" if int(t * 6 + x) % 2 else "o", S(196, 1))
        for (x, y, age) in self.ground:
            cv.put(int(x), int(y), "@" if age < 20 else "o", S(160 if age < 20 else 52))


class PohangScene(BaseScene):
    name = "pohang"
    title = "Pohang: Homigot sunrise and Guryongpo's camellias"
    label = "韓國浦項"
    order = 35

    INTRO_END = 10.0
    GAZE = (HAND_X + 10, 8, HAND_Y, 9)
    CAT_ACCESSORY = CAMELLIA
    BANNER = {"ramp": (203, 209, 215, 222, 215, 209), "wish_colour": 223}
    SETTINGS = {
        "greeting": "Every sunrise is for you, My Love!",
        "wish": "Like the camellias, I fall for you again and again.",
        "surprise_at": 60.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=26, height=7)
        self.clouds = [(rng.uniform(-10, CW), rng.randint(9, 12), rng.randint(6, 14),
                        rng.uniform(0.2, 0.5)) for _ in range(6)]
        self.windows = [rng.uniform(0, 6.28) for _ in range(12)]
        self.houses = [0, 21]                       # x of each house (stairs between)
        self.extra_houses = []
        self.bushes = [Prop(BUSH, 3, 24), Prop(BUSH, 34, 24), Prop(BUSH, 68, 24)]
        self.camellias = FallingCamellias()
        self.next_drop = 2.0
        self.gulls = [[rng.uniform(0, CW), rng.uniform(2, 8), rng.choice((-1, 1)) * rng.uniform(3, 5),
                       rng.uniform(0, 6.28)] for _ in range(3)]
        self.floor = [(x, y, rng.choice(".,'"), rng.choice((240, 244, 246)))
                      for y in range(24, CH) for x in range(CW) if rng.random() < 0.06]
        self.floor_extra = []

    def on_view(self, view):
        """A wide window: more houses up the hill on the left, more sea on the right."""
        x0, _y0, _x1, _y1 = view
        make = lambda r: (13, r.randint(1, 4), None)
        self.extra_houses = [x for (x, _w, _d) in lay_out(random.Random(7), -2, x0, make,
                                                         leftwards=True)]
        self.floor_extra = [(x, y, ".,'"[int(hash01(x, y, 2) * 3)], (240, 244, 246)[int(hash01(x, y, 3) * 3)])
                            for y in range(24, CH) for x in self.margin_columns()
                            if hash01(x, y, 1) < 0.06]

    # ---------------- animation ----------------
    def sun_top(self):
        """The sun's top row: rises out of the sea and ends above the hand."""
        u = clamp((self.t - 1.0) / 22.0, 0.0, 1.0)
        u = 1 - (1 - u) ** 2
        return SEA_TOP + 1 - u * (SEA_TOP + 1 - 3)

    def update_scene(self, dt):
        t = self.t
        if t > self.next_drop:
            self.next_drop = t + random.uniform(0.8, 2.2)
            b = random.choice(self.bushes)
            self.camellias.drop(b.x + random.uniform(1, b.w - 1), b.base - b.h + 1)
        self.camellias.update(dt)
        x0, _y0, x1, _y1 = self.view
        for g in self.gulls:
            g[0] += g[2] * dt
            g[1] += math.sin(t * 0.8 + g[3]) * 0.4 * dt
            if g[0] < x0 - 4 or g[0] > x1 + 4:
                g[2] = -g[2]

    # ---------------- drawing ----------------
    def draw_sky(self, cv):
        t = self.t
        top = self.sun_top()
        warm = clamp((SEA_TOP + 1 - top) / 8.0, 0.0, 1.0)      # 0 before sunrise .. 1
        if warm < 0.8:
            self.sky.draw(cv, t)
        # the glow along the horizon
        for y in range(SEA_TOP - 3, SEA_TOP):
            for x in cv.xs():
                d = abs(x - SUN_CX) / 40.0 + (SEA_TOP - 1 - y) * 0.25
                if hash01(x, y, 11) < 0.35 * warm * (1.2 - d):
                    cv.put(x, y, "-" if y == SEA_TOP - 1 else ".",
                           S((202, 208, 209, 216)[min(3, int(d * 3))]))
        # pink and gold cloud streaks drifting
        for (x, y, w, sp) in self.clouds:
            cx = (x + t * sp) % (cv.x1 - cv.x0 + 20) + cv.x0 - 10
            col = (217, 216, 223)[y % 3] if warm > 0.3 else 60
            cv.text(int(cx), y, "_.-" + "~" * (w - 6) + "-._", S(col))
        # the sun (the sea is drawn over its lower part while it rises)
        st = S((196, 202, 208, 214, 220)[min(4, int(warm * 4.99))], 1)
        y0 = int(round(top))
        for dy, row in enumerate(SUN):
            if y0 + dy < SEA_TOP:
                cv.text(SUN_CX - 5, y0 + dy, row, st)
        if warm > 0.9:
            for i, (dx, dy) in enumerate(((-8, 1), (8, 1), (-6, -1), (6, -1), (0, -2))):
                if math.sin(t * 2.0 + i) > 0.2:
                    cv.put(SUN_CX + dx, y0 + 1 + dy, "*" if i % 2 else "+", S(229, 1))

    def draw_village(self, cv):
        t = self.t
        def hill_y(x):                                         # a smooth ridge
            if x >= 0:
                return 5.0 + x * 0.26 + 0.8 * math.sin(x * 0.15)
            return 5.0 + 0.8 * math.sin(x * 0.15)

        for x in range(min(cv.x0, 0), 36):                     # the hill behind
            yf = hill_y(x)
            top = int(yf)
            frac = yf - top
            if hill_y(x + 1) < yf:                             # going up: mirror it
                frac = 1.0 - frac
            cv.put(x, top, "`--."[min(3, int(frac * 4))], S(71))
            for y in range(top + 1, SEA_BOT + 1):              # little pines on it
                tree = hash01(x, y, 21) < 0.12
                cv.put(x, y, "^" if tree else " ", S(28 if y % 2 else 22), True)
        # the stone stairs up the hill, camellias painted on the side walls
        for y in range(5, 23):
            half = 1 + (y - 5) // 5
            for dx in range(-half, half + 1):
                cv.put(STAIRS_CX + dx, y, "=" if y % 2 else "_", S(250 if y % 2 else 246))
            for side in (-half - 1, half + 1):
                paint = (y * 3 + side) % 5 == 0
                cv.put(STAIRS_CX + side, y, "@" if paint else "|", S(196, 1) if paint else S(244))
        # the wooden houses (windows lit for the early morning)
        for i, hx in enumerate(self.houses + self.extra_houses):
            HOUSE.draw(cv, hx, 23 - HOUSE.h, lambda dx, dy, ch, st, i=i: self.window(i, dx, ch, st))
        on = math.sin(t * 3.0) > -0.3
        cv.text(self.houses[1] + 2, 23 - HOUSE.h + 4, "Camellia", S(204 if on else 168, 1))

    def window(self, i, dx, ch, st):
        if ch == "+":
            ph = self.windows[(i * 3 + dx) % len(self.windows)]
            return S(229 if math.sin(self.t * 0.5 + ph) > -0.5 else 178, 1)
        return st

    def draw_sea(self, cv):
        t = self.t
        top = self.sun_top()
        for y in range(SEA_TOP, SEA_BOT + 1):
            for x in cv.xs():
                v = math.sin(x * 0.4 + t * 1.4 + y * 1.1) + math.sin(x * 0.15 - t * 0.8)
                if v > 1.0:
                    cv.put(x, y, "~", S(31 if y > 18 else 25))
                elif v > 0.2:
                    cv.put(x, y, "-", S(24))
        if top < SEA_TOP:                                     # the sun's path on the water
            for y in range(SEA_TOP, SEA_BOT + 1):
                spread = 1 + (y - SEA_TOP) // 3
                for dx in range(-spread, spread + 1):
                    if math.sin(t * 3.0 + y * 1.7 + dx * 2.3) > 0.1:
                        cv.put(SUN_CX + dx, y, "=" if dx == 0 else "~", S(214 if abs(dx) < 2 else 208))

    def draw_hand(self, cv):
        t = self.t
        top = self.sun_top()
        lit = top < SEA_TOP - 2

        def glint(dx, dy, ch, st):
            if lit and ch in "|_" and math.sin(t * 1.5 - dy * 0.6 + dx * 0.3) > 0.85:
                return S(220, 1)
            return st
        HAND.draw(cv, HAND_X, HAND_Y, glint)
        for x in range(HAND_X + 3, HAND_X + 18):              # waves around the wrist
            if math.sin(x * 1.3 + t * 3.0) > 0.0:
                cv.put(x, SEA_BOT - 1, "~", S(255, 1))
        # gulls resting on the fingertips, looking around
        for i, (fx, fy) in enumerate(FINGERTIPS):
            look = int(t * 0.7 + i * 1.3) % 3
            cv.text(fx, fy - 1, ("o>", "<o", "o>")[look], S(255, 1))
        LIGHTHOUSE.draw(cv, CW - 6, SEA_BOT - LIGHTHOUSE.h + 1,
                        lambda dx, dy, ch, st: S(228 if math.sin(t * 2.5) > 0 else 238, 1)
                        if ch == "o" else st)

    def draw_background(self, cv):
        t = self.t
        self.draw_sky(cv)
        for (x, y, _vx, ph) in self.gulls:                  # gulls flying
            cv.text(int(x) - 1, int(y), "\\v/" if math.sin(t * 6 + ph) > 0 else "-v-", S(252))
        self.draw_sea(cv)
        self.draw_village(cv)
        self.draw_hand(cv)
        pat = "_.-'-._.='"                                   # the stone promenade
        for x in cv.xs():
            cv.put(x, 23, pat[x % len(pat)], S(245))
        for (x, y, c, col) in self.floor + self.floor_extra:
            cv.put(x, y, c, S(col))
        self.camellias.draw(cv, t)

    def depth_items(self):
        return [(b.base, lambda cv, b=b: b.draw(cv)) for b in self.bushes]

    def hideouts(self):
        return self.bushes
