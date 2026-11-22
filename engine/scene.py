# -*- coding: utf-8 -*-
"""
scene.py - BaseScene: the life cycle every scene shares
=======================================================

A scene is "a stage + its decorations". The base class runs the part of the
story that is the same everywhere:

    cats walk in  ->  play freely  ->  gather in their seats  ->  the greeting
    is typed out and hearts float up  ->  back to free play  ->  (repeat)

and draws in a fixed order:

    draw_background()  ->  props + cats sorted by depth  ->  particles
    ->  greeting banner  ->  draw_foreground()

A concrete scene only fills in the hooks it needs (all optional):

    build(rng)          create decorations (rng = a seeded random.Random)
    update_scene(dt)    animate decorations
    draw_background(cv) sky / backdrop / centrepiece, behind everything
    depth_items()       [(foot_y, draw_fn), ...] things cats walk in front
                        of / behind (painter's algorithm by foot row)
    draw_foreground(cv) anything on top of the cats
    hideouts()          objects (cx, w, h) a playful cat may hide behind
    on_key(k)           extra keys
    on_view(view)       the window size changed: view = (x0, y0, x1, y1), the
                        visible world (see engine/render.py "Window size");
                        add scenery for the margins of a wide window here

Full-width things (ground, sea, ...) are drawn over cv.xs(); self.view is
the visible world, self.ROAM the columns the cats may walk in.

and class attributes (see below) for timing, floor lanes, seats, the cats'
accessory, colours of the greeting and default settings.

Scenes must not import each other; they only use the `engine` package.
"""
import random

from . import cats as catlib
from .effects import Banner, Fx, HEART_RAMP, SPARK_RAMP, Z_RAMP
from .render import CH, CW, clamp


class BaseScene:
    # ---- identity (a scene is found by `name`) ----
    name = None
    title = ""
    label = ""                           # short name for menus (any language)
    order = 50                           # position in menus / --list-scenes

    # ---- stage geometry: the "world" interface engine/cats.py relies on ----
    CW, CH = CW, CH
    CX = CW // 2                         # centre column (seats, gazing)
    FLOOR_MIN, FLOOR_MAX = 25.0, 26.0    # cats' front walking lane (foot row)
    BACK_Y = 23.3                        # lane *behind* the props
    GAZE = None                          # (x, half_w, y, h): where a calm cat
                                         # "looks", sparkles appear there
    HEART_RAMP, Z_RAMP, SPARK_RAMP = HEART_RAMP, Z_RAMP, SPARK_RAMP

    ROAM_MARGIN = 45                     # how far past the stage cats may roam
                                         # in a wide window


    # ---- timing ----
    INTRO_END = 0.0                     # no surprise before this
    SEED = 11                            # layout seed for build(rng)

    # ---- seats for the surprise: alternate left / right of CX ----
    SEAT_INNER = 12                      # columns from CX to the first seat
    SEAT_STEP = 19                       # extra columns per seat further out
    SEAT_ROWS = (25.8, 24.9)             # alternating foot rows (depth)

    # ---- hearts floating up while the greeting is shown ----
    HEART_SPAWN = (14, 21.0)             # (half width around CX, start row)

    # ---- per-scene look of the greeting & cats ----
    BANNER = {}                          # kwargs for effects.Banner (colours)
    CAT_ACCESSORY = None                 # cats.Accessory worn in this scene

    # ---- default settings for this scene (settings.json / CLI override) ----
    SETTINGS = {}

    def __init__(self, cfg):
        self.cfg = cfg
        self.heart = cfg.heart
        self.view = (0, 0, self.CW, self.CH)
        self.ROAM = (0, self.CW)
        self.t = 0.0
        self.phase = "free"
        self.build(random.Random(self.SEED))
        self.fx = Fx()
        self.banner = Banner(cfg.greeting, cfg.wish, self.heart, self.CW, **self.BANNER)
        self.cats = catlib.load_cats(cfg.cats, self, accessory=self.CAT_ACCESSORY,
                                     only=getattr(cfg, "only_cats", None))
        self.next_surprise = max(cfg.surprise_at,
                                 max(c.enter_at for c in self.cats) + 8.0)
        self.hold_t0 = 0.0
        self.heart_clock = 0.0
        if cfg.skip_intro:
            self.skip_intro()

    # ------------------------------------------------------------------
    #  hooks (override what you need)
    # ------------------------------------------------------------------
    def build(self, rng):
        pass

    def update_scene(self, dt):
        pass

    def draw_background(self, cv):
        pass

    def depth_items(self):
        return []

    def draw_foreground(self, cv):
        pass

    def hideouts(self):
        return []

    def on_key(self, k):
        pass

    def on_view(self, view):
        pass

    def margin_columns(self):
        """Visible columns outside the stage (a wide window), left and right."""
        x0, _y0, x1, _y1 = self.view
        return [x for x in range(x0, x1) if x < 0 or x >= self.CW]

    def set_view(self, view):
        """Called (by draw) when the window, and so the visible world, changes."""
        view = tuple(view)
        if view == self.view:
            return
        self.view = view
        x0, _y0, x1, _y1 = view
        self.ROAM = (max(x0, -self.ROAM_MARGIN), min(x1, self.CW + self.ROAM_MARGIN))
        self.on_view(view)
    # ------------------------------------------------------------------
    #  shared story
    # ------------------------------------------------------------------
    def skip_intro(self):
        self.t = max(self.INTRO_END, max(c.enter_at for c in self.cats) + 1.0)
        n = len(self.cats)
        for i, c in enumerate(self.cats):
            lo, hi = c.bounds()
            c.place(clamp(12 + (i + 0.5) * (self.CW - 24) / n, lo, hi), c.lane())
            c.next()
        self.next_surprise = self.t + self.cfg.surprise_at

    def seats(self):
        """Seats for the surprise: alternating left / right of CX."""
        out = []
        per_side = (len(self.cats) + 1) // 2
        step = self.SEAT_STEP if per_side <= 2 else 20.0 / (per_side - 1)  # squeeze 3+
        for k, c in enumerate(self.cats):
            idx, left = k // 2, k % 2 == 0
            off = self.SEAT_INNER + idx * step
            lo, hi = c.bounds()
            x = clamp(self.CX - off if left else self.CX + off, lo, hi)
            y = self.SEAT_ROWS[idx % len(self.SEAT_ROWS)]
            out.append((c, x, y, 1 if left else -1))
        return out

    def trigger_surprise(self):
        if self.phase == "free" and all(c.visible for c in self.cats):
            self.phase = "gather"
            for c, x, y, face in self.seats():
                c.to_final(x, y, face)

    def farewell(self):
        """Printed in the normal terminal after quitting."""
        return (self.cfg.greeting + " " + self.heart).strip()

    def update(self, dt):
        self.t += dt
        t = self.t
        self.update_scene(dt)
        for c in self.cats:
            if not c.visible and t >= c.enter_at:
                c.enter()
        for c in self.cats:
            if c.visible:
                c.update(dt)
        self.fx.update(dt)
        self.banner.update(dt)

        if self.phase == "free":
            if t >= self.next_surprise and t >= self.INTRO_END:
                self.trigger_surprise()
        elif self.phase == "gather":
            if all(c.state == "final" and c.st > 1.0 for c in self.cats):
                self.phase = "hold"
                self.hold_t0 = t
                self.banner.show()
        elif self.phase == "hold":
            self.heart_clock -= dt
            if self.heart_clock <= 0:
                self.heart_clock = 0.45
                hw, hy = self.HEART_SPAWN
                self.fx.emit(self.CX + random.uniform(-hw, hw), hy, random.uniform(-0.6, 0.6),
                             random.uniform(-3.2, -2.2), 4.2, self.heart, self.HEART_RAMP, 1.2)
            if (not self.cfg.stay) and t - self.hold_t0 > self.cfg.hold:
                self.banner.hide()
                self.phase = "free"
                self.next_surprise = t + self.cfg.every
                for c in self.cats:
                    c.next()

    def draw(self, cv):
        t = self.t
        if hasattr(cv, "view"):
            self.set_view(cv.view())
        cv.clear()
        self.draw_background(cv)
        objs = [(y, 0, fn) for (y, fn) in self.depth_items()]
        objs += [(c.y, 1, c.draw) for c in self.cats if c.visible]
        objs.sort(key=lambda o: (o[0], o[1]))
        for _y, _kind, fn in objs:
            fn(cv)
        self.fx.draw(cv, t)
        self.banner.draw(cv, t)
        self.draw_foreground(cv)
