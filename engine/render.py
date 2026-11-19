# -*- coding: utf-8 -*-
"""
render.py - the shared, holiday-agnostic drawing layer
======================================================

  Canvas      a character grid. A scene draws everything into it, then the
              whole frame goes to the terminal in ONE write() (no flicker).
  S / ansi    256-colour styles: an int, colour | 256 for bold.
  text_width / fit / put_text   wide-character (CJK / emoji) aware text.

  view_canvas a Canvas the size of the terminal window (see "Window size")
  hash01 / lay_out   helpers for filling the margins of a wide window

Nothing in here knows about trees, snow or any particular scene.

Window size
-----------
Every scene is laid out on a 78 x 27 "stage" (world coordinates 0..77,
0..26). The canvas is as big as the terminal window and looks at the world
through an offset: the stage stays centred left/right and sits on the bottom
of the window, so a bigger window shows more sky above and more scenery
left and right (world x < 0 or >= 78, y < 0). A smaller window (down to
MIN_W x MIN_H) crops the stage's edges and the top of its sky instead.

Scenes draw full-width things over cv.xs() (the visible world columns)
instead of range(CW).

Three sizes (cv.k)
------------------
A big window does not just show more scenery: when the whole stage fits
1.5x or 2x bigger (see pick_scale), it is DRAWN bigger, with its own
larger art (bigger tree, bigger cats ...), the font staying the same.

Everything still *moves* in stage units (a cat at x = 30.5 on row 25.8);
only drawing changes. A canvas has a scale k (1, 1.5 or 2), and its
coordinates are "pixels" of the k-times bigger stage (sw x sh cells):
    cv.px(x) / cv.py(y)   a stage position -> its cell on this canvas
A scene says how big it can be drawn with MAX_SCALE (see engine/scene.py).
"""
import math
import unicodedata
import zlib

CW, CH = 78, 27            # the stage every scene is laid out on (columns x rows)
MIN_W, MIN_H = 64, 24      # the smallest window a scene still runs in (cropped)
SCALES = (1, 1.5, 2)       # how much bigger a scene may be drawn (see pick_scale)
RESET = "\x1b[0m"


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


# ---------------------------------------------------------------------
#  Styles / colours  (256-colour ANSI)
# ---------------------------------------------------------------------
def S(n, bold=0):
    return n | (256 if bold else 0)


_ANSI = {}


def ansi(st):
    s = _ANSI.get(st)
    if s is None:
        s = "\x1b[0;%s38;5;%dm" % ("1;" if st & 256 else "", st & 255)
        _ANSI[st] = s
    return s


# ---------------------------------------------------------------------
#  Text helpers
# ---------------------------------------------------------------------
def char_width(c):
    """Terminal columns a character takes (CJK / emoji = 2)."""
    return 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1


def text_width(s):
    return sum(char_width(c) for c in s)


def fit(s, width):
    """Shorten s (with '...') so it fits in `width` terminal columns."""
    if text_width(s) <= width:
        return s
    out = ""
    for c in s:
        if text_width(out + c) > width - 3:
            break
        out += c
    return out + "..."


# ---------------------------------------------------------------------
#  Canvas
# ---------------------------------------------------------------------
class Canvas:
    """w x h cells. World (x, y) is drawn at cell (x + ox, y + oy).
    k = how many times bigger the stage is drawn; it is then sw x sh cells."""

    def __init__(self, w=CW, h=CH, ox=0, oy=0, k=1):
        self.w, self.h = w, h
        self.ox, self.oy = ox, oy
        self.k = k
        self.sw, self.sh = stage_size(k)
        # the visible part of the world
        self.x0, self.x1 = -ox, w - ox
        self.y0, self.y1 = -oy, h - oy
        self.ch = []
        self.st = []
        self.clear()

    def xs(self):
        """The visible world columns (range(CW) for a standard 78 x 27 window)."""
        return range(self.x0, self.x1)

    def view(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def px(self, x):
        """Stage column x (a float is fine) -> the cell column on this canvas."""
        return scaled(x, self.k)

    def py(self, y):
        """Stage row y -> the cell row on this canvas."""
        return scaled(y, self.k)

    def clear(self):
        self.ch = [" "] * (self.w * self.h)
        self.st = [None] * (self.w * self.h)

    def put(self, x, y, c, st, solid=False):
        x += self.ox
        y += self.oy
        if 0 <= x < self.w and 0 <= y < self.h and (solid or c != " "):
            i = y * self.w + x
            self.ch[i] = c
            self.st[i] = st

    def text(self, x, y, s, st):
        for i, c in enumerate(s):
            self.put(x + i, y, c, st)

    def put_text(self, x, y, text, colour_of):
        """Draw text, giving wide (Chinese / Japanese / emoji) characters 2
        cells. colour_of(i, ch) -> style. Returns the column after the text."""
        for i, c in enumerate(text):
            st = colour_of(i, c)
            self.put(x, y, c, st)
            if char_width(c) == 2:
                # 2nd half of a wide char: same style, so no colour code is
                # emitted between two Chinese characters
                self.put(x + 1, y, "", st, True)
                x += 2
            else:
                x += 1
        return x

    def rows(self):
        """Each row as an ANSI-coloured string (only colour changes emitted)."""
        out = []
        w = self.w
        for y in range(self.h):
            parts = []
            cur = None
            base = y * w
            for x in range(w):
                c = self.ch[base + x]
                if c != " ":
                    st = self.st[base + x]
                    if st != cur:
                        parts.append(ansi(st))
                        cur = st
                parts.append(c)
            if cur is not None:
                parts.append(RESET)
            out.append("".join(parts))
        return out

    def frame(self, cols, lines):
        """The whole canvas, centred in a cols x lines terminal, as ONE string
        of absolute cursor moves + rows."""
        left = (cols - self.w) // 2 + 1
        top = (lines - self.h) // 2 + 1
        return "".join("\x1b[%d;%dH%s" % (top + i, left, row)
                       for i, row in enumerate(self.rows()))

    def plain_rows(self):
        return ["".join(self.ch[y * self.w:(y + 1) * self.w]).rstrip()
                for y in range(self.h)]


def scaled(v, k):
    """A stage position (column or row) -> its cell when drawn k times bigger
    (the middle of stage cell v lands in the middle of its k x k block)."""
    if k == 1:
        return int(round(v))
    return int(math.floor((v + 0.5) * k))


def stage_size(k, w=CW, h=CH):
    """The stage drawn k times bigger: (columns, rows)."""
    return int(math.ceil(w * k)), int(math.ceil(h * k))


def pick_scale(cols, lines, max_scale=1):
    """The biggest scale (<= max_scale) at which the stage fits a cols x lines
    window. A few rows of sky may be cut, as at the normal size."""
    best = 1
    for k in SCALES:
        sw, sh = stage_size(k)
        if k <= max_scale and cols >= sw and lines >= sh - round(3 * k):
            best = k
    return best


def view_canvas(cols, lines, w=CW, h=CH, min_w=MIN_W, min_h=MIN_H, k=1):
    """A canvas filling a cols x lines window: the w x h stage (drawn k times
    bigger) centred left/right and standing on the bottom edge. None if the
    window is smaller than min_w x min_h."""
    if cols < min_w or lines < min_h:
        return None
    sw, sh = stage_size(k, w, h)
    return Canvas(cols, lines, (cols - sw) // 2, lines - sh, k)


# ---------------------------------------------------------------------
#  Margin helpers (scenery outside the 78 x 27 stage)
# ---------------------------------------------------------------------
def hash01(x, y, seed=0):
    """A repeatable 'random' number in [0, 1) for a cell, without any state."""
    return (zlib.crc32(b"%d,%d,%d" % (x, y, seed)) & 0xFFFFFF) / float(0x1000000)


def lay_out(rng, start, stop, make, leftwards=False):
    """Lay pieces side by side from `start` rightwards up to `stop` (or, with
    leftwards=True, from `start` leftwards down to `stop`); nothing if there
    is no room. make(rng) -> (width, gap, data). Returns [(x, width, data)]."""
    out = []
    x = start
    if not leftwards:
        while x < stop:
            w, gap, data = make(rng)
            out.append((x, w, data))
            x += w + gap
    else:
        while x > stop:
            w, gap, data = make(rng)
            x -= w + gap
            out.append((x + gap, w, data))
    return out
