# -*- coding: utf-8 -*-
"""
build_ascii_html.py - the web version of the ASCII animation:  web/ascii.html
============================================================================

    python tools/build_ascii_html.py            (a few minutes: every scene x every cat choice)

Writes web/ascii.html (the player) and web/ascii/<scene>.js (one data file per
scene, loaded when the scene is chosen). No Python, server or internet is
needed to watch it: open web/index.html or web/ascii.html in a browser.

How: the real engine (the same code as main.py) plays every scene in a
COLS x ROWS "window" and every frame is recorded.

  * once WITHOUT cats: the background (sky, scenery, snow, greeting ...)
  * once for every choice of cats (1 to MAX_CATS of the cats in cats.json):
    only the cells that differ from the background are kept (an "overlay")

so the page can let you tick the cats, like the menu of main.py. For the
background to stay the same whatever cats are chosen, the cats draw their
random numbers from their own generator while recording, and so do the
greeting's hearts (which start once the cats have gathered).

Frames store only the cells that changed since the previous frame; every
recording is zlib-compressed and base64-encoded.
"""
import base64
import itertools
import json
import os
import random
import sys
import time
import types
import zlib
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import main as M                                   # noqa: E402
import engine.cats as catlib                       # noqa: E402
import engine.effects as fxlib                     # noqa: E402
import engine.scene as scenelib                    # noqa: E402
from engine.render import view_canvas              # noqa: E402

TEMPLATE = os.path.join(ROOT, "tools", "ascii_web_template.html")
WEB = os.path.join(ROOT, "web")

COLS, ROWS = 120, 34            # the "terminal window" every scene is recorded in
FPS = 15                        # recorded frames per second (the engine steps at 30)
STEP = 2                        # engine updates per recorded frame
MAX_CATS = 3                    # like the menu of main.py
SKIP = ("demo",)                # the architecture demo is not part of the web page
WIDE = "\x01"                   # the right half of a wide (CJK / emoji) character
CLEAR = "\x02"                  # overlay: no cat here, show the background
EXTRA = 10.0                    # seconds recorded after the greeting's hold time


def jump_before(name):
    """Where the '驚喜' button jumps to, in seconds before the surprise."""
    return 11.0 if name == "taipei101" else 1.0      # Taipei 101: its 10 s countdown


# ---------------------------------------------------------------------
#  Recording with the cats' randomness kept apart
# ---------------------------------------------------------------------
def _rng(seed):
    r = random.Random(seed)
    return types.SimpleNamespace(uniform=r.uniform, choice=r.choice, randint=r.randint,
                                 random=r.random, Random=random.Random)


class Recording:
    """While active: cats and the greeting's hearts use their own random
    numbers (also inside Fx.emit), and an empty cat choice means no cats."""

    def __enter__(self):
        self.saved = (catlib.random, scenelib.random, fxlib.random, fxlib.Fx.emit,
                      catlib.load_cats)
        load, emit = catlib.load_cats, fxlib.Fx.emit
        rec = self

        def load_cats(path, world, accessory=None, only=None):
            return [] if only == [] else load(path, world, accessory=accessory, only=only)

        def routed_emit(fx, *a, **k):
            if sys._getframe(1).f_globals.get("__name__") == "engine.scene":   # the hearts
                saved = fxlib.random
                fxlib.random = rec.hearts
                try:
                    return emit(fx, *a, **k)
                finally:
                    fxlib.random = saved
            return emit(fx, *a, **k)

        catlib.load_cats = load_cats
        fxlib.Fx.emit = routed_emit
        return self

    def __exit__(self, *exc):
        (catlib.random, scenelib.random, fxlib.random, fxlib.Fx.emit,
         catlib.load_cats) = self.saved

    def start(self, seed=1):
        random.seed(seed)
        self.cats = _rng(seed + 6)
        self.hearts = _rng(seed + 10)
        catlib.random = self.cats
        scenelib.random = self.hearts

    def watch_cats(self, scene):
        """Inside a cat's update / enter, Fx.emit draws from the cats' numbers too."""
        rec = self
        for c in scene.cats:
            for meth in ("update", "enter"):
                f = getattr(c, meth)

                def wrapped(*a, _f=f, **k):
                    saved = fxlib.random
                    fxlib.random = rec.cats
                    try:
                        return _f(*a, **k)
                    finally:
                        fxlib.random = saved
                setattr(c, meth, wrapped)


def play(manager, name, only, seconds, rec):
    """Every frame of scene `name` with cats `only`: lists of (char, style)."""
    rec.start()
    manager.only_cats = only
    scene = manager.create(name)
    rec.watch_cats(scene)
    cv = view_canvas(COLS, ROWS, scene.CW, scene.CH)
    scene.set_view(cv.view())
    for _f in range(int(seconds * FPS)):
        for _ in range(STEP):
            scene.update(1.0 / (FPS * STEP))
        cv.clear()
        scene.draw(cv)
        yield [(c or WIDE, st) for c, st in zip(cv.ch, cv.st)]


def diff(prev, cur, gap=3):
    """The changed cells as a flat list [start, chars, [style, ...], start, ...];
    changes up to `gap` cells apart are joined into one run."""
    out = []
    n = len(cur)
    i = 0
    while i < n:
        if cur[i] == prev[i]:
            i += 1
            continue
        j = i + 1
        last = i
        while j < n and j - last <= gap:
            if cur[j] != prev[j]:
                last = j
            j += 1
        run = cur[i:last + 1]
        out += [i, "".join(c for c, _s in run), [s for _c, s in run]]
        i = last + 1
    return out


def pack(obj):
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(zlib.compress(data, 9)).decode("ascii")


def combos(n_cats):
    return [list(c) for k in range(1, MAX_CATS + 1)
            for c in itertools.combinations(range(n_cats), k)]


def make_manager():
    return M.make_manager(M.build_parser().parse_args([]))


def record_scene(name, choices=None):
    """Background + one overlay per cat choice for scene `name`."""
    manager, _default = make_manager()
    cfg = manager.settings_for(name)
    cats = catlib.read_config(cfg.cats)[0]["cats"]
    seconds = cfg.surprise_at + cfg.hold + EXTRA
    styles = {None: 0}

    def coded(frame):
        out = []
        for c, st in frame:
            if st not in styles:
                styles[st] = len(styles)
            out.append((c, styles[st]))
        return out

    with Recording() as rec:
        bg_frames, prev, bg = [], [(" ", 0)] * (COLS * ROWS), []
        for frame in play(manager, name, [], seconds, rec):
            cur = coded(frame)
            bg_frames.append(diff(prev, cur))
            bg.append(cur)
            prev = cur
        overlays = {}
        for only in (choices if choices is not None else combos(len(cats))):
            frames, prev = [], [(CLEAR, 0)] * (COLS * ROWS)
            for k, frame in enumerate(play(manager, name, only, seconds, rec)):
                cur = [c if c != b else (CLEAR, 0) for c, b in zip(coded(frame), bg[k])]
                frames.append(diff(prev, cur))
                prev = cur
            overlays[",".join(map(str, only))] = pack(frames)
    cls = manager.get(name)
    return {"name": name, "label": cls.label or cls.title, "title": cls.title,
            "seconds": seconds, "surprise": max(0.0, cfg.surprise_at - jump_before(name)),
            "styles": [-1 if s is None else s for s in sorted(styles, key=styles.get)],
            "bg": pack(bg_frames), "overlays": overlays}


def _job(name):
    t0 = time.time()
    return record_scene(name), time.time() - t0


# ---------------------------------------------------------------------
#  Writing the page
# ---------------------------------------------------------------------
def build(web=WEB, names=None, choices=None, workers=None):
    manager, default = make_manager()
    cfg = manager.settings_for(default)
    cats = catlib.read_config(cfg.cats)[0]["cats"]
    names = [n for n in (names or manager.names()) if n not in SKIP]
    os.makedirs(os.path.join(web, "ascii"), exist_ok=True)
    if choices is not None or workers == 1:
        results = [(record_scene(n, choices), 0.0) for n in names]
    else:
        with Pool(min(len(names), workers or os.cpu_count() or 2)) as pool:
            results = pool.map(_job, names)
    scenes = []
    for rec, secs in results:
        data = {k: rec.pop(k) for k in ("styles", "bg", "overlays")}
        data["name"] = rec["name"]
        path = os.path.join(web, "ascii", rec["name"] + ".js")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("ASCII_SCENE(%s);\n" % json.dumps(data, separators=(",", ":")))
        scenes.append(rec)
        print("  %-10s %5.1f s x %2d cat choices  %5d KB  (%.0f s)"
              % (rec["name"], rec["seconds"], len(data["overlays"]),
                 os.path.getsize(path) // 1024, secs))
    page = {"cols": COLS, "rows": ROWS, "fps": FPS, "wide": WIDE, "clear": CLEAR,
            "stage": manager.get(default).CW, "default": default, "maxCats": MAX_CATS,
            "cats": [{"name": c["name"], "skin": c.get("skin", ""),
                      "on": c.get("enabled", True)} for c in cats],
            "scenes": scenes}
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(page, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = os.path.join(web, "ascii.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html.replace("/*DATA*/", data, 1))
    return out


if __name__ == "__main__":
    t0 = time.time()
    path = build()
    print("wrote %s and web/ascii/*.js  (%.0f s)" % (path, time.time() - t0))
