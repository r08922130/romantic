# -*- coding: utf-8 -*-
"""
fourier.py - complex Fourier series of a closed outline (epicycles)
===================================================================

    outline = tree_outline()              closed curve, complex points
                                          (also the star, ornaments, bow;
                                          onestroke.py joins them into one)
    samples = resample(outline, 512)      evenly spaced by arc length
    coeffs  = dft(samples)                [(n, c_n)], n = -N/2 .. N/2-1
    z(t)    = sum c_n exp(i 2 pi n t),    t in [0, 1)

Each term c_n exp(i 2 pi n t) is a rotating vector: radius |c_n|, n turns
per period (negative n turns clockwise), starting angle arg c_n. Put head
to tail, the tip of the last one traces the outline. Keeping only the
lowest frequencies (truncate) gives a smoother approximation; with all N
terms the samples come back exactly.

Standard library only; NumPy's FFT is used when it happens to be installed.
"""
import cmath
import math


# ---------------------------------------------------------------------
#  The shapes (x right, y down; the tree is about 2 units tall).
#  onestroke.py joins them into one closed curve with one Fourier series.
# ---------------------------------------------------------------------
STAR_CY, STAR_R, STAR_r = -1.10, 0.16, 0.065
APEX_Y = -0.99
TIERS = [(-0.72, 0.34), (-0.30, 0.52), (0.14, 0.70), (0.60, 0.90)]  # (bottom y, half width)
TRUNK_W, TRUNK_H = 0.11, 0.26
GROUND_Y = TIERS[-1][0] + TRUNK_H              # where the trunk and the presents stand


def tree_outline():
    """The tree: four tiers of branches with drooping tips and a scalloped
    hem, symmetric. Starts at the apex, goes down the right side, along the
    hem and back up the left side."""
    right = [complex(0.0, APEX_Y)]
    x0, y0 = 0.0, APEX_Y
    for i, (yb, w) in enumerate(TIERS):
        for s in range(1, 13):                       # slightly concave branch edge
            u = s / 12.0
            right.append(complex(x0 + (w - x0) * u ** 1.25, y0 + (yb - y0) * u))
        right.append(complex(w + 0.03, yb + 0.035))  # the drooping branch tip
        last = i == len(TIERS) - 1
        inner = 0.0 if last else w * 0.42
        for s in range(1, 13):                       # the tier's lower edge
            u = s / 12.0
            x = w + (inner - w) * u
            if last:                                 # scalloped hem
                y = yb + 0.035 * abs(math.sin(math.pi * 3 * u))
            else:
                y = yb - 0.07 * u + 0.025 * math.sin(math.pi * u)
            right.append(complex(x, y))
        x0, y0 = inner, yb - 0.07
    left = [complex(-z.real, z.imag) for z in reversed(right[1:-1])]
    return right + left


def star_outline(cx=0.0, cy=STAR_CY, R=STAR_R, r=STAR_r):
    """A five-pointed star (10 corners)."""
    return [complex(cx + (r if k % 2 == 0 else R) * math.cos(math.pi / 2 + k * math.pi / 5),
                    cy + (r if k % 2 == 0 else R) * math.sin(math.pi / 2 + k * math.pi / 5))
            for k in range(10)]


def bauble_outline(cx, cy, r):
    """A round bauble with its little cap on top."""
    cap = 0.38 * r
    a0 = math.asin(cap / r)                         # where the cap meets the ball
    pts = [complex(cx - cap, cy - r * 1.28), complex(cx + cap, cy - r * 1.28)]
    for s in range(41):                             # the ball, the long way round
        a = -math.pi / 2 + a0 + s / 40.0 * (2 * math.pi - 2 * a0)
        pts.append(complex(cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def heart_outline(cx, cy, size):
    """The classic heart curve."""
    pts = []
    for s in range(64):
        t = s / 64.0 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(complex(cx + x / 17.0 * size, cy - y / 17.0 * size))
    return pts


def bell_outline(cx, cy, size):
    """A bell: knob on top, flared body, a rim and the clapper."""
    pts = [complex(cx, cy - size * 1.05)]
    side = []
    for s in range(13):                             # the right side, flaring out
        u = s / 12.0
        y = cy - size * 0.85 + u * size * 1.55
        x = cx + size * (0.32 + 0.42 * u ** 2.2)
        side.append(complex(x, y))
    rim_y = cy + size * 0.70
    right = side + [complex(cx + size * 0.82, rim_y + size * 0.10),
                    complex(cx + size * 0.12, rim_y + size * 0.10)]
    clapper = [complex(cx + size * 0.12 * math.cos(a), rim_y + size * 0.10 + size * 0.16 * math.sin(a))
               for a in [k * math.pi / 8 for k in range(9)]]          # half circle below
    left = [complex(2 * cx - z.real, z.imag) for z in reversed(right)]
    return pts + right + clapper[1:-1] + left


def stroke_outline(center, w):
    """A closed outline around a thick stroke along the polyline `center`
    (round ends) - for the candy cane."""
    n = len(center)
    normals = []
    for i in range(n):
        a, b = center[max(0, i - 1)], center[min(n - 1, i + 1)]
        d = b - a
        normals.append(d / abs(d) * 1j)
    left = [center[i] + normals[i] * w for i in range(n)]
    right = [center[i] - normals[i] * w for i in reversed(range(n))]
    end = [center[-1] + normals[-1] * w * cmath.exp(-1j * math.pi * k / 8) for k in range(1, 8)]
    start = [center[0] - normals[0] * w * cmath.exp(-1j * math.pi * k / 8) for k in range(1, 8)]
    return left + end + right + start


def candy_cane_outline(cx, cy, size):
    """A candy cane: a straight stem and a hook at the top."""
    c = [complex(cx, cy + size * (0.9 - 1.4 * s / 10.0)) for s in range(11)]
    top = c[-1].imag
    hook_r = size * 0.28
    c += [complex(cx + hook_r - hook_r * math.cos(a), top - hook_r * math.sin(a))
          for a in [k * math.pi / 12 for k in range(1, 13)]]
    c += [complex(cx + 2 * hook_r, top + size * 0.18 * s / 3.0) for s in range(1, 4)]
    return stroke_outline(c, size * 0.09)


def bow_outline(cx, cy, a, b):
    """A ribbon bow: a figure-eight lying on its side."""
    return [complex(cx + a * math.sin(t), cy + b * math.sin(t) * math.cos(t))
            for t in [k / 64.0 * 2 * math.pi for k in range(64)]]


# ---------------------------------------------------------------------
#  The presents under the tree
# ---------------------------------------------------------------------
GIFTS = [  # (centre x, width, height, box colour, ribbon colour)
    (-0.66, 0.34, 0.26, "#d83a3a", "#ffd54a"),
    (-0.30, 0.22, 0.17, "#2f7de1", "#ffffff"),
    (0.32, 0.30, 0.22, "#8b4fd8", "#ffd54a"),
    (0.66, 0.22, 0.16, "#e8a23a", "#d83a3a"),
]


def ornament_outline(kind, x, y, size):
    return {"heart": heart_outline, "bauble": bauble_outline, "bell": bell_outline,
            "candy": candy_cane_outline}[kind](x, y, size)


# ---------------------------------------------------------------------
#  Sampling and the transform
# ---------------------------------------------------------------------
def resample(path, n):
    """n points evenly spaced by arc length along the closed polyline."""
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
    """DFT index k -> signed frequency: indices above n/2 are k - n."""
    return k if k < (n + 1) // 2 else k - n


def dft(samples):
    """c_n = 1/N sum_k z_k exp(-i 2 pi n k / N) -> [(n, c_n)] sorted by n."""
    N = len(samples)
    try:
        import numpy as np
        f = np.fft.fft(np.array(samples, dtype=complex)) / N
        coeffs = [(freq_of(k, N), complex(f[k])) for k in range(N)]
    except ImportError:
        if N & (N - 1) == 0:                          # a power of two: our own FFT
            f = fft(samples)
            return sorted(((freq_of(k, N), f[k] / N) for k in range(N)), key=lambda c: c[0])
        tw = [cmath.exp(-2j * math.pi * k / N) for k in range(N)]
        coeffs = []
        for k in range(N):
            acc = 0j
            for j, z in enumerate(samples):
                acc += z * tw[(k * j) % N]
            coeffs.append((freq_of(k, N), acc / N))
    return sorted(coeffs, key=lambda c: c[0])


def fft(z):
    """Radix-2 FFT (len(z) a power of two): sum_k z_k exp(-i 2 pi n k / N)
    for every n, in O(N log N) - plain Python."""
    a = list(z)
    n = len(a)
    j = 0
    for i in range(1, n):                             # bit-reversed order
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        w_step = cmath.exp(-2j * math.pi / size)
        half = size // 2
        ws = [w_step ** k for k in range(half)]
        for start in range(0, n, size):
            for k in range(half):
                u = a[start + k]
                v = a[start + k + half] * ws[k]
                a[start + k] = u + v
                a[start + k + half] = u - v
        size *= 2
    return a


def truncate(coeffs, terms):
    """The `terms` lowest frequencies (0, 1, -1, 2, -2, ...)."""
    by_freq = sorted(coeffs, key=lambda c: (abs(c[0]), -c[0]))
    return by_freq[:max(1, min(terms, len(coeffs)))]


def by_size(coeffs):
    """Drawing order: the fixed centre (n = 0) first, then biggest first."""
    return sorted(coeffs, key=lambda c: (c[0] != 0, -abs(c[1])))


def by_frequency(coeffs):
    """Drawing order: 0, 1, -1, 2, -2, ..."""
    return sorted(coeffs, key=lambda c: (abs(c[0]), -c[0]))


def evaluate(coeffs, t):
    return sum(c * cmath.exp(2j * math.pi * n * t) for n, c in coeffs)


def chain(coeffs, t):
    """Heads of the rotating vectors, head to tail; the last is the tip."""
    out, z = [], 0j
    for n, c in coeffs:
        z += c * cmath.exp(2j * math.pi * n * t)
        out.append(z)
    return out


def reconstruct(coeffs, m):
    """z(k / m) for k = 0 .. m-1 - the curve at m evenly spaced times. With
    m a power of two (and every |n| < m/2) this is one inverse FFT instead of
    m times len(coeffs) rotations."""
    if m & (m - 1) == 0 and all(abs(n) < m // 2 for n, _c in coeffs):
        a = [0j] * m
        for n, c in coeffs:
            a[n % m] += c.conjugate()
        return [v.conjugate() for v in fft(a)]       # inverse transform via conjugates
    return [evaluate(coeffs, k / float(m)) for k in range(m)]


def max_error(coeffs, samples):
    """Largest distance between the reconstruction and the samples."""
    N = len(samples)
    return max(abs(a - z) for a, z in zip(reconstruct(coeffs, N), samples))
