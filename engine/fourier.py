# -*- coding: utf-8 -*-
"""
fourier.py - Fourier epicycles: rotating circles that draw a closed outline
===========================================================================

A reusable effect (nothing here knows about Christmas):

    shape   = [(x, y), ...]            a closed outline in stage cells
    samples = resample(to_square(shape), 256)   evenly spaced by arc length
    coeffs  = dft(samples)             [(n, c_n)] for n = -N/2 .. N/2-1
    z(t)    = sum c_n * exp(i 2 pi n t),   t in [0, 1)

Each term c_n exp(i 2 pi n t) is a rotating vector (radius |c_n|, n turns
per period, starting angle arg c_n); placed head to tail, the tip of the last
one traces the outline. Keeping only the lowest frequencies (truncate) gives
a smoother approximation; with every term the samples come back exactly.

Terminal cells are about twice as tall as they are wide, so the maths runs
in "square" units (x, y * ASPECT) and only drawing converts back - circles
then look round on screen.

    FourierPrelude(shape, terms=100)   the animation: circles appear, the tip
        draws the outline, the trace stays, circles fade out (.done), then the
        trace fades while the scene carries on (.finished).

The coefficients are computed once per (shape, samples) and cached; a frame
only adds up `terms` rotating vectors.
"""
import cmath
import math

from .render import S

ASPECT = 2.0               # a terminal cell is about twice as tall as wide
TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------
#  The maths
# ---------------------------------------------------------------------
def to_square(points, aspect=ASPECT):
    """Stage cells (column, row) -> complex numbers in square units."""
    return [complex(x, y * aspect) for (x, y) in points]


def from_square(z, aspect=ASPECT):
    """Complex number in square units -> (column, row) as floats."""
    return z.real, z.imag / aspect


def resample(path, n):
    """n points evenly spaced by arc length along the CLOSED polyline `path`
    (complex numbers). Corners are kept in the right place along the curve,
    long straight edges no longer get fewer samples than short ones."""
    pts = list(path)
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    seg = [abs(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)]
    total = sum(seg)
    if total <= 0:
        raise ValueError("the outline has no length")
    out, i, acc = [], 0, 0.0
    for k in range(n):
        target = total * k / float(n)
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        u = (target - acc) / seg[i] if seg[i] else 0.0
        out.append(pts[i] + (pts[i + 1] - pts[i]) * u)
    return out


def freq_of(k, n):
    """DFT index k (0 .. n-1) -> signed frequency: indices above n/2 are the
    negative frequencies k - n (they turn the other way)."""
    return k if k < (n + 1) // 2 else k - n


def dft(samples):
    """c_n = 1/N sum_k z_k exp(-i 2 pi n k / N), returned as [(n, c_n)] with
    signed frequencies n (see freq_of), sorted by n.
    Uses NumPy's FFT when it is installed, plain Python otherwise."""
    N = len(samples)
    try:
        import numpy as np
        f = np.fft.fft(np.array(samples, dtype=complex)) / N
        coeffs = [(freq_of(k, N), complex(f[k])) for k in range(N)]
    except ImportError:
        tw = [cmath.exp(-2j * math.pi * k / N) for k in range(N)]   # twiddles
        coeffs = []
        for k in range(N):
            acc = 0j
            for j, z in enumerate(samples):
                acc += z * tw[(k * j) % N]
            coeffs.append((freq_of(k, N), acc / N))
    return sorted(coeffs, key=lambda c: c[0])


def truncate(coeffs, terms):
    """Keep the `terms` LOWEST frequencies (0, 1, -1, 2, -2, ...): the best
    approximation with that many circles."""
    by_freq = sorted(coeffs, key=lambda c: (abs(c[0]), -c[0]))
    return by_freq[:max(1, min(terms, len(coeffs)))]


def evaluate(coeffs, t):
    """z(t) = sum c_n exp(i 2 pi n t)."""
    return sum(c * cmath.exp(2j * math.pi * n * t) for n, c in coeffs)


def chain(coeffs, t):
    """The rotating vectors head to tail: [z_0, z_1, ...] where z_0 is the
    fixed centre (the n = 0 term) and the last one is the drawing tip."""
    out = []
    z = 0j
    for n, c in coeffs:
        z += c * cmath.exp(2j * math.pi * n * t)
        out.append(z)
    return out


def max_error(coeffs, samples):
    """Largest distance between the reconstruction and the samples (square
    units) - how well `coeffs` reproduce the outline."""
    N = len(samples)
    return max(abs(evaluate(coeffs, k / float(N)) - z) for k, z in enumerate(samples))


_CACHE = {}


def coefficients(shape, samples=256, aspect=ASPECT):
    """DFT of `shape` (stage cells) resampled to `samples` points - cached."""
    key = (tuple(shape), samples, aspect)
    if key not in _CACHE:
        pts = resample(to_square(shape, aspect), samples)
        _CACHE[key] = (pts, dft(pts))
    return _CACHE[key]


# ---------------------------------------------------------------------
#  Drawing helpers
# ---------------------------------------------------------------------
def line_char(dx, dy):
    """A character for a short piece of line going (dx, dy) in cells."""
    if dx == 0 and dy == 0:
        return "*"
    a = math.degrees(math.atan2(-dy * ASPECT, dx)) % 180.0    # screen angle 0..180
    if a < 22.5 or a >= 157.5:
        return "-"
    if a < 67.5:
        return "/"
    if a < 112.5:
        return "|"
    return "\\"


def raster(points, smooth=0):
    """Polyline of (column, row) floats -> the cells it passes through, in
    order, each with a character that follows the line: [(x, y, ch)].
    smooth = how many points before / after to look at for the direction
    (a staircase of single cells should still read as '/' or '\\')."""
    cells, seen = [], set()
    prev = None
    last = len(points) - 1
    for i, (x, y) in enumerate(points):
        cell = (int(round(x)), int(round(y)))
        if prev is not None and cell != prev:
            # step cell by cell between prev and cell (Bresenham-like)
            x0, y0 = prev
            x1, y1 = cell
            n = max(abs(x1 - x0), abs(y1 - y0))
            if smooth:
                a, b = points[max(0, i - smooth)], points[min(last, i + smooth)]
                ch = line_char(b[0] - a[0], b[1] - a[1])
            else:
                ch = line_char(x1 - x0, y1 - y0)
            for s in range(1, n + 1):
                c = (x0 + int(round((x1 - x0) * s / float(n))),
                     y0 + int(round((y1 - y0) * s / float(n))))
                if c not in seen:
                    seen.add(c)
                    cells.append((c[0], c[1], ch))
        elif prev is None:
            seen.add(cell)
            cells.append((cell[0], cell[1], "*"))
        prev = cell
    return cells


# ---------------------------------------------------------------------
#  The effect
# ---------------------------------------------------------------------
class FourierPrelude:
    """Epicycles drawing `shape` (a closed outline in stage cells).

    Timeline (seconds): APPEAR circles fade in and turn; DRAW the tip draws
    one full period; HOLD the finished outline stays; FADE circles and
    vectors fade out -> .done (the scene starts); TRAIL the outline fades
    while the scene goes on -> .finished.
    """
    APPEAR, DRAW, HOLD, FADE, TRAIL = 1.5, 10.0, 1.5, 1.5, 5.0
    SAMPLES = 256              # outline samples (= DFT size)
    PATH_POINTS = 1200         # points of the reconstructed outline we draw
    MAX_CIRCLES = 60           # only the biggest circles are drawn

    TRAIL_RAMP = (46, 46, 40, 34, 28, 22, 236)
    CIRCLE_RAMP = (67, 61, 60, 238, 236)

    def __init__(self, shape, terms=100, aspect=ASPECT, label=True):
        self.aspect = aspect
        self.samples, self.all_coeffs = coefficients(shape, self.SAMPLES, aspect)
        self.terms = max(1, min(int(terms), len(self.all_coeffs)))
        self.coeffs = truncate(self.all_coeffs, self.terms)
        # drawing order: the fixed centre (n = 0) first, then by size
        self.coeffs.sort(key=lambda c: (c[0] != 0, -abs(c[1])))
        self.error = max_error(self.coeffs, self.samples) / aspect   # in rows
        path = [from_square(evaluate(self.coeffs, k / float(self.PATH_POINTS)), aspect)
                for k in range(self.PATH_POINTS + 1)]
        self.trail = raster(path, smooth=12)      # the whole outline, in drawing order
        self.label = label
        self.time = 0.0

    # ---- timeline ----
    @property
    def total(self):
        return self.APPEAR + self.DRAW + self.HOLD + self.FADE

    @property
    def done(self):
        """Circles gone: the scene can start."""
        return self.time >= self.total

    @property
    def finished(self):
        """The trace has faded too: nothing left to draw."""
        return self.time >= self.total + self.TRAIL

    def param(self):
        """Curve parameter t: negative while the circles appear (they turn,
        nothing is drawn yet), 0..1 while drawing, then it keeps turning."""
        return (self.time - self.APPEAR) / self.DRAW

    def drawn(self):
        """How much of the outline has been drawn (0..1)."""
        return min(1.0, max(0.0, self.param()))

    def update(self, dt):
        self.time += dt

    # ---- drawing ----
    def draw(self, cv):
        t = self.time
        p = self.param()
        # the trace
        n = int(len(self.trail) * self.drawn())
        after = t - self.total
        if after > 0:
            k = min(len(self.TRAIL_RAMP) - 1, int(after / self.TRAIL * len(self.TRAIL_RAMP)))
        else:
            k = 0
        trail_st = S(self.TRAIL_RAMP[k], 1 if k < 2 else 0)
        for (x, y, ch) in self.trail[:n]:
            cv.put(x, y, ch, trail_st)
        if self.done:
            return
        # circles and vectors (faded in at the start, out at the end)
        fade_in = min(1.0, t / self.APPEAR)
        fade_out = 1.0 - max(0.0, (t - self.APPEAR - self.DRAW - self.HOLD) / self.FADE)
        alpha = min(fade_in, fade_out)
        ci = min(len(self.CIRCLE_RAMP) - 1, int((1.0 - alpha) * len(self.CIRCLE_RAMP)))
        circle_st, vector_st = S(self.CIRCLE_RAMP[ci]), S(250 if alpha > 0.5 else 244)
        pts = chain(self.coeffs, p)
        a = self.aspect
        for i in range(1, min(len(pts), self.MAX_CIRCLES + 1)):
            centre, r = pts[i - 1], abs(self.coeffs[i][1])
            if r < 0.6:                                   # too small to see
                break
            steps = max(10, int(TWO_PI * r * 0.9))
            for s in range(steps):
                z = centre + r * cmath.exp(1j * TWO_PI * s / steps)
                cv.put(int(round(z.real)), int(round(z.imag / a)), ".", circle_st)
        for i in range(1, min(len(pts), self.MAX_CIRCLES + 1)):   # vectors on top
            x0, y0 = from_square(pts[i - 1], a)
            x1, y1 = from_square(pts[i], a)
            for (x, y, ch) in raster([(x0, y0), (x1, y1)])[1:]:
                cv.put(x, y, ch, vector_st)
        tx, ty = from_square(pts[-1], a)
        cv.put(int(round(tx)), int(round(ty)), "@", S(226, 1))   # the drawing tip
        if self.label and alpha > 0.3:
            cv.text(max(cv.x0, 0) + 1, cv.y1 - 1,
                    "Fourier epicycles: %d terms" % self.terms, S(240))
