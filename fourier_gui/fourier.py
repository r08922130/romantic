# -*- coding: utf-8 -*-
"""
fourier.py - complex Fourier series of a closed outline (epicycles)
===================================================================

    outline = tree_outline()              closed curve, complex points
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
#  The Christmas tree outline (x right, y down; about 2.4 units tall)
# ---------------------------------------------------------------------
STAR_CY, STAR_R, STAR_r = -1.10, 0.16, 0.065
TIERS = [(-0.72, 0.34), (-0.30, 0.52), (0.14, 0.70), (0.60, 0.90)]  # (bottom y, half width)
TRUNK_W, TRUNK_H = 0.11, 0.24


def tree_outline():
    """Closed outline: a five-pointed star on top, four tiers of branches
    with drooping tips, a scalloped bottom, the trunk. Returns complex points
    (the last one connects back to the first)."""
    pts = []
    # the star, starting at its bottom inner corner and going round once
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        rad = STAR_r if k % 2 == 0 else STAR_R
        pts.append(complex(rad * math.cos(a), STAR_CY + rad * math.sin(a)))
    # the right side, tier by tier
    right = []
    x0, y0 = 0.035, STAR_CY + STAR_r + 0.03
    right.append(complex(x0, y0))
    for i, (yb, w) in enumerate(TIERS):
        for s in range(1, 13):                       # slightly concave branch edge
            u = s / 12.0
            right.append(complex(x0 + (w - x0) * u ** 1.25, y0 + (yb - y0) * u))
        right.append(complex(w + 0.03, yb + 0.035))  # the drooping branch tip
        last = i == len(TIERS) - 1
        inner = TRUNK_W if last else w * 0.42
        for s in range(1, 13):                       # the tier's lower edge
            u = s / 12.0
            x = w + (inner - w) * u
            if last:                                 # scalloped hem
                y = yb + 0.035 * abs(math.sin(math.pi * 3 * u))
            else:
                y = yb - 0.07 * u + 0.025 * math.sin(math.pi * u)
            right.append(complex(x, y))
        x0, y0 = inner, (yb + 0.02 if last else yb - 0.07)
    trunk_top = right[-1].imag
    right += [complex(TRUNK_W, trunk_top + TRUNK_H)]
    left = [complex(-z.real, z.imag) for z in reversed(right)]
    return pts + right + [complex(0, trunk_top + TRUNK_H)] + left


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
        tw = [cmath.exp(-2j * math.pi * k / N) for k in range(N)]
        coeffs = []
        for k in range(N):
            acc = 0j
            for j, z in enumerate(samples):
                acc += z * tw[(k * j) % N]
            coeffs.append((freq_of(k, N), acc / N))
    return sorted(coeffs, key=lambda c: c[0])


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


def max_error(coeffs, samples):
    """Largest distance between the reconstruction and the samples."""
    N = len(samples)
    return max(abs(evaluate(coeffs, k / float(N)) - z) for k, z in enumerate(samples))
