# -*- coding: utf-8 -*-
"""
build_ascii_html.py - write the web version of the ASCII animation:  ../ascii.html
================================================================================

    python tools/build_ascii_html.py

One self-contained HTML file (no Python, no server, no internet needed):
double-click it to open it in a browser, or send it to someone.

How: every scene is played by the real engine (the same code as main.py),
with a fixed random seed, in a COLS x ROWS "window", and every frame is
recorded. Only the cells that changed since the previous frame are stored,
the whole scene is zlib-compressed and written into the page (base64). The
page (ascii_web_template.html) unpacks a scene when it is chosen and plays
the frames back on a <canvas>, with the terminal's 256 colours.

The cats are the ones cats.json turns on; greetings and timing come from
settings.json. Run this again after changing scenes, cats or settings.
"""
import base64
import json
import os
import random
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import main as M                                   # noqa: E402
from engine.render import view_canvas              # noqa: E402

TEMPLATE = os.path.join(ROOT, "tools", "ascii_web_template.html")
OUT = os.path.join(ROOT, "ascii.html")

COLS, ROWS = 120, 34            # the "terminal window" every scene is recorded in
FPS = 15                        # recorded frames per second (the engine steps at 30)
STEP = 2                        # engine updates per recorded frame
SKIP = ("demo",)                # the architecture demo is not part of the web page
WIDE = "\x01"                   # marks the right half of a wide (CJK / emoji) character
EXTRA = 6.0                     # seconds recorded after the greeting goes away


def jump_before(name):
    """Where the '驚喜' button jumps to, in seconds before the surprise."""
    return 11.0 if name == "taipei101" else 1.0      # Taipei 101: its 10 s countdown


def record(manager, name, seed=1):
    """Play scene `name` and return its frames as runs of changed cells."""
    random.seed(seed)
    scene = manager.create(name)
    cfg = manager.settings_for(name)
    seconds = cfg.surprise_at + cfg.hold + EXTRA
    cv = view_canvas(COLS, ROWS, scene.CW, scene.CH)
    scene.set_view(cv.view())
    styles = {None: 0}
    prev = [(" ", 0)] * (COLS * ROWS)
    frames = []
    for _f in range(int(seconds * FPS)):
        for _ in range(STEP):
            scene.update(1.0 / (FPS * STEP))
        cv.clear()
        scene.draw(cv)
        cur = []
        for c, st in zip(cv.ch, cv.st):
            if st not in styles:
                styles[st] = len(styles)
            cur.append((c or WIDE, styles[st]))
        frames.append(diff(prev, cur))
        prev = cur
    order = sorted(styles, key=styles.get)
    return {"name": name, "label": type(scene).label or type(scene).title,
            "title": type(scene).title, "seconds": seconds,
            "surprise": max(0.0, cfg.surprise_at - jump_before(name)),
            "styles": [-1 if s is None else s for s in order],
            "frames": frames}


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


def build(out=OUT, names=None):
    args = M.build_parser().parse_args([])
    manager, default = M.make_manager(args)
    scenes = []
    for name in names or manager.names():
        if name in SKIP:
            continue
        t0 = time.time()
        rec = record(manager, name)
        packed = pack({"styles": rec.pop("styles"), "frames": rec.pop("frames")})
        rec["data"] = packed
        scenes.append(rec)
        print("  %-10s %5.1f s recorded, %4d KB  (%.1f s)"
              % (name, rec["seconds"], len(packed) * 3 // 4 // 1024, time.time() - t0))
    page = {"cols": COLS, "rows": ROWS, "fps": FPS, "wide": WIDE, "stage": manager.get(default).CW,
            "default": default, "scenes": scenes}
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(page, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*DATA*/", data, 1)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return out


if __name__ == "__main__":
    path = build()
    print("wrote %s (%d KB)" % (path, os.path.getsize(path) // 1024))
