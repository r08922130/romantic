# -*- coding: utf-8 -*-
"""
taipei101.py - Taipei101Scene: New Year's Eve fireworks at Taipei 101
=====================================================================

    python main.py --scene taipei101

Taipei 101 (eight stacked "bamboo" segments) glows in its colour of the day
over the city at night. Ten seconds before the surprise a big countdown
10, 9, ... 1 appears and the tower's segments flash one by one. At zero it
is midnight: fireworks shoot sideways out of every segment, rockets burst
all over the sky, the new year appears in big digits, and the cats sit down
for "Happy New Year, My Love!". The cats wear little party hats.
"""
import datetime
import math
import random

from engine.cats import Accessory
from engine.effects import FIREWORK_RAMPS, Fireworks, Starfield
from engine.render import CW, S, lay_out
from engine.scene import BaseScene
from engine.sprites import Art, Prop, sym

CX = CW // 2
TOP = 0                                    # row of the spire tip (behind the banner)


def coming_year(today=None):
    d = today or datetime.date.today()
    return d.year if d.month == 1 else d.year + 1


YEAR = str(coming_year())

# ---------------------------------------------------------------------
#  The tower, top to bottom:
#    the spire, the stepped crown (floors 91-101),
#    8 segments that flare OUT towards their top - the "bamboo" sawtooth
#    silhouette: a lit eave row (11 wide) over a narrower glass row (9),
#    the tapering base with the gold ruyi ornament, and the mall podium.
# ---------------------------------------------------------------------
SEGMENTS = 8
CROWN = 3                                   # rows above the segments: spire + crown
TOWER_ROWS = [
    sym("", "|"),          # spire tip (aviation light)
    sym("", "|"),          # spire
    sym("_", "|"),         # spire foot  _|_
    sym("[", "#"),         # crown       [#]
    sym("[:", ":"),        # crown       [:::]
]
for _ in range(SEGMENTS):
    TOWER_ROWS += [sym("\\====", "="),      # \=========/   eaves, widest
                   sym(" \\:::", ":")]      #  \:::::::/    glass, narrower
TOWER_ROWS += [
    sym("/:::(", "@"),     # /:::(@):::\     base top + ruyi ornament
    sym("/:::::", ":"),    # /:::::::::::\
    sym("/______", "_"),   # /_____________\
]
SEG_DY0 = 5                                 # TOWER_ROWS index of the first segment
SEG_ROW0 = TOP + SEG_DY0                    # canvas row of the first segment's eaves
BASE_DY0 = SEG_DY0 + SEGMENTS * 2
PODIUM_HALF = 13                            # the mall around the tower's feet
DAY_COLOURS = (196, 208, 226, 46, 33, 63, 129)   # Mon..Sun, as the real tower does
DAY_DIM = {196: 124, 208: 166, 226: 178, 46: 34, 33: 25, 63: 61, 129: 91}

# 3 x 5 block digits for the countdown and the year
FONT = {
    "0": ["###", "# #", "# #", "# #", "###"], "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", "###", "#  ", "###"], "3": ["###", "  #", "###", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"], "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"], "7": ["###", "  #", "  #", "  #", "  #"],
    "8": ["###", "# #", "###", "# #", "###"], "9": ["###", "# #", "###", "  #", "###"],
}


def big_text(cv, x, y, text, colour_of):
    for i, d in enumerate(text):
        for dy, row in enumerate(FONT.get(d, FONT["0"])):
            for dx, ch in enumerate(row):
                if ch != " ":
                    cv.put(x + i * 4 + dx, y + dy, "#", colour_of(i))


BALLOONS = Art([" O o ",
                "O  O ",
                " \\|/ ",
                "  |  ",
                "  |  "],
               mask=[" R Y ", "B  P ", "", "", ""],
               palette={"R": S(196, 1), "Y": S(226, 1), "B": S(45, 1), "P": S(213, 1)},
               default=S(250))
CHAMPAGNE = Art([" \\|/ ",
                 "  #  ",
                 " _#_ ",
                 "|***|",
                 "'---'"],
                mask=[" YYY ", "  G  ", " WGW ", "WIIIW", "WWWWW"],
                palette={"Y": S(226, 1), "G": S(28, 1), "W": S(250), "I": S(195, 1)})

PARTY_HAT = Accessory("party_hat", [(1, -1, "{Y}*"), (0, 0, "{P}/{Y}:{P}\\")],
                      palette={"P": S(201, 1), "Y": S(226, 1)})


class Taipei101Scene(BaseScene):
    name = "taipei101"
    title = "Taipei 101: New Year's Eve countdown and fireworks"
    label = "台北 101 跨年煙火"
    order = 50

    INTRO_END = 8.0
    GAZE = (CX, 5, 5, 14)
    CAT_ACCESSORY = PARTY_HAT
    BANNER = {"ramp": (226, 220, 214, 231, 214, 220), "wish_colour": 229}
    SETTINGS = {
        "greeting": "Happy New Year, My Love!",
        "wish": "Let's count down to every new year together.",
        "surprise_at": 60.0,
    }
    COUNTDOWN = 10.0

    def build(self, rng):
        self.sky = Starfield(rng, n=22, height=9)
        self.city = []
        x = 0
        while x < CW:
            w = rng.randint(4, 8)
            if x < CX + PODIUM_HALF + 2 and x + w > CX - PODIUM_HALF - 2:   # tower + mall
                x = CX + PODIUM_HALF + 2
                continue
            self.city.append((x, w, rng.randint(3, 9), rng.uniform(0, 6.28)))
            x += w + rng.choice((0, 1))
        self.city_end = x
        self.city_extra = []
        self.windows = [rng.uniform(0, 6.28) for _ in range(97)]
        self.props = [Prop(BALLOONS, 14, 24), Prop(CHAMPAGNE, 60, 24)]
        self.fireworks = None
        self.next_burst = 0.0
        self.next_jet = 0.0
        self.midnight = None            # time the show started

    def on_view(self, view):
        """A wide window: the city goes on to both edges."""
        x0, _y0, x1, _y1 = view
        rng = random.Random(10)
        make = lambda r: (r.randint(4, 8), r.choice((0, 1)), (r.randint(3, 9), r.uniform(0, 6.28)))
        self.city_extra = [(x, w, h, ph) for (x, w, (h, ph)) in
                           lay_out(rng, 0, x0, make, leftwards=True) +
                           lay_out(rng, self.city_end, x1, make)]

    # ---------------- timing ----------------
    def countdown(self):
        """Seconds left (10..1) while the countdown is on screen, else None."""
        if self.phase != "free" or self.t < self.INTRO_END - 2:
            return None
        left = self.next_surprise - self.t
        if 0.0 < left <= self.COUNTDOWN:
            return int(math.ceil(left))
        return None

    def showing(self):
        return self.phase in ("gather", "hold")

    def update_scene(self, dt):
        if self.fireworks is None:
            self.fireworks = Fireworks(self.fx)
        t = self.t
        x0, _y0, x1, _y1 = self.view
        reach = min(x1 - CX, CX - x0) - 6                  # wide window: wider show
        if self.showing():
            if self.midnight is None:
                self.midnight = t
                for k in range(5):                         # the big opening volley
                    self.fireworks.burst(random.uniform(x0 + 8, x1 - 8), random.uniform(3, 9))
            if t > self.next_burst:                        # rockets all over the sky
                self.next_burst = t + random.uniform(0.25, 0.7)
                side = random.choice((-1, 1))
                self.fireworks.launch(CX + side * random.uniform(12, max(36, reach)), 22,
                                      random.uniform(2.5, 9.0))
            if t > self.next_jet:                          # sparks out of the segments
                self.next_jet = t + 0.06
                seg = random.randrange(SEGMENTS)
                y = SEG_ROW0 + seg * 2           # out of the eaves
                ramp = random.choice(FIREWORK_RAMPS)
                for side in (-1, 1):
                    for _ in range(2):
                        self.fx.emit(CX + side * 6, y, side * random.uniform(7, 14),
                                     random.uniform(-1.5, 1.5), random.uniform(0.4, 0.8),
                                     random.choice("*+-"), ramp)
        else:
            self.midnight = None
            if random.random() < dt * 0.08 and t > self.INTRO_END:   # a rare early one
                self.fireworks.launch(random.uniform(x0 + 5, x1 - 5), 22, random.uniform(3, 7))
        self.fireworks.update(dt)

    # ---------------- drawing ----------------
    def tower_colour(self, dx, dy, ch):
        t = self.t
        if dy == 0:                                        # aviation light on the spire
            return S(196, 1) if int(t * 1.5) % 2 == 0 else S(88)
        if ch == "@":                                      # the gold ruyi ornament
            return S(231 if int(t * 2) % 5 == 0 else 220, 1)
        glass = ch == ":"
        seg = (dy - SEG_DY0) // 2 if SEG_DY0 <= dy < BASE_DY0 else -1
        if t < 3.0:                                        # lights not on yet
            return S(237 if glass else 243)
        cd = self.countdown()
        if cd is not None and seg >= 0:                    # countdown: segments flash in turn
            lit = int((self.COUNTDOWN - (self.next_surprise - t)) * 2) % SEGMENTS
            if seg == lit:
                return S(231, 1)
            return S(237 if glass else 242)
        if self.showing() and seg >= 0:                    # midnight: rainbow chase
            return S(DAY_COLOURS[int(seg + t * 6) % len(DAY_COLOURS)], 0 if glass else 1)
        day = DAY_COLOURS[datetime.date.today().weekday()]
        if glass:                                          # the facade glows the day colour,
            k = (dy * 11 + dx * 3) % len(self.windows)     # a few offices still lit
            if math.sin(t * 0.4 + self.windows[k]) > 0.85:
                return S(230)
            return S(DAY_DIM.get(day, day))
        if dy <= 2:
            return S(252, 1)                               # silver spire
        return S(day, 1)

    def draw_city(self, cv, t):
        for (x, w, h, ph) in self.city + self.city_extra:
            top = 22 - h + 1
            for y in range(top, 23):
                for xx in range(x, x + w):
                    if y == top:
                        cv.put(xx, y, "_", S(240))
                    elif xx in (x, x + w - 1):
                        cv.put(xx, y, "|", S(238))
                    else:
                        on = (y - top) % 2 == 0 and math.sin(t * 0.3 + ph + xx * 1.9) > -0.1
                        cv.put(xx, y, "." if on else " ", S(222 if on else 236), True)

    def draw_podium(self, cv, t):
        """The low shopping mall wrapped around the tower's feet."""
        x0, x1 = CX - PODIUM_HALF, CX + PODIUM_HALF
        for x in range(x0, x1 + 1):
            cv.put(x, 20, "_", S(246))
            for y in (21, 22):
                edge = x in (x0, x1)
                win = (x - x0) % 2 == 1 and math.sin(t * 0.5 + x * 0.7 + y) > -0.3
                cv.put(x, y, "|" if edge else ("." if win else " "),
                       S(244) if edge else S(229 if win else 236), True)

    def draw_background(self, cv):
        t = self.t
        self.sky.draw(cv, t)
        self.draw_city(cv, t)
        self.draw_podium(cv, t)
        pat = "=-=-"
        for x in cv.xs():
            cv.put(x, 23, pat[x % len(pat)], S(242))
        for dy, row in enumerate(TOWER_ROWS):
            x0 = CX - len(row) // 2
            for dx, ch in enumerate(row):
                if ch != " ":
                    cv.put(x0 + dx, TOP + dy, ch, self.tower_colour(dx, dy, ch))
        cd = self.countdown()
        if cd is not None:                                 # 10 .. 1, big, left of the tower
            txt = str(cd)
            pulse = (self.next_surprise - t) % 1.0
            col = S(231, 1) if pulse > 0.7 else S(226, 1)
            big_text(cv, 18 - len(txt) * 2, 6, txt, lambda i: col)
        if self.showing() and self.midnight is not None and t - self.midnight > 1.0:
            big_text(cv, 52, 4, YEAR,
                     lambda i: S(DAY_COLOURS[int(i + t * 4) % len(DAY_COLOURS)], 1))
        if self.fireworks is not None:
            self.fireworks.draw(cv)

    def depth_items(self):
        return [(p.base, lambda cv, p=p: p.draw(cv, self.t)) for p in self.props]

    def hideouts(self):
        return self.props
