# -*- coding: utf-8 -*-
"""
onestroke.py - the whole picture as ONE closed curve (a one-stroke drawing)
===========================================================================

    path, labels, parts = one_stroke()

The tree, the star, the garlands, the ornaments, the trunk, the ground and
the presents are joined into a single closed path, so ONE Fourier series
(one chain of circles) draws everything:

  ground (left)  -> the presents on the left: box, horizontal ribbon (there
                    and back), bow (a figure eight), vertical ribbon (down and
                    back up) ...
  trunk (up)     -> the tree outline from the left side of the hem, up the
                    left side, round the star at the apex, down the right side;
                    on the way: every garland (along its top, back along its
                    bottom, where ornaments hang on strings) and ornaments
                    hanging from the branch tips
  trunk (down)   -> the presents on the right -> along the ground back to the
                    start.

Excursions go out and come back along the same line, so the joins are drawn
twice on top of each other and look like single strings.

Every point carries a label (which part it belongs to) so the trace can be
coloured part by part, and each part can be filled from its own stretch of
the reconstructed curve.
"""
import math

import fourier as F

STRING = 0.07                      # length of an ornament's string


class Builder:
    def __init__(self):
        self.pts, self.labels = [], []
        self.parts = {}            # label -> {"colour", "fill", "width"}

    def part(self, label, colour, fill=True, width=1.8):
        self.parts.setdefault(label, {"colour": colour, "fill": fill, "width": width})
        return label

    def add(self, points, label):
        for z in points:
            self.pts.append(z)
            self.labels.append(label)

    def go(self, z, label):
        self.add([z], label)


def ornament_at(kind, attach, size):
    """An ornament hanging with its top at `attach`: its outline starting and
    ending at that top point."""
    shape = F.ornament_outline(kind, 0.0, 0.0, size)
    top = min(range(len(shape)), key=lambda i: (shape[i].imag, abs(shape[i].real)))
    shift = attach - shape[top]
    loop = [z + shift for z in shape[top:] + shape[:top]]
    return loop + [loop[0]]


def edge_x(outline, y, side):
    """Where the tree's outer edge crosses height y on the left (-1) or right
    (+1) side."""
    xs = []
    n = len(outline)
    for i in range(n):
        a, b = outline[i], outline[(i + 1) % n]
        if (a.imag - y) * (b.imag - y) <= 0 and a.imag != b.imag:
            u = (y - a.imag) / (b.imag - a.imag)
            x = a.real + (b.real - a.real) * u
            if x * side > 0:
                xs.append(x)
    return min(xs) if side < 0 else max(xs)


# where the ornaments go: on garland g at position u (0 = left .. 1 = right)
GARLAND_ORNAMENTS = {0: [(0.55, "heart", 0.06, "#ff6fa8")],
                     1: [(0.30, "bauble", 0.045, "#4dc3ff"), (0.70, "candy", 0.075, "#ff4040")],
                     2: [(0.25, "heart", 0.055, "#ff6fa8"), (0.62, "bell", 0.05, "#ffcc33")]}
# hanging from the branch tips of tiers 0..2: (kind, size, colour)
TIP_ORNAMENTS = [("bauble", 0.04, "#ff4040"), ("bell", 0.05, "#ffcc33"),
                 ("bauble", 0.045, "#b56bff")]
GARLAND_Y = [(-0.62, -0.46), (-0.14, 0.02), (0.24, 0.38)]     # (y at left end, y at right end)


def garland_loop(b, gi, left, right, sag, thick=0.035):
    """Along the garland's top edge, back along its bottom edge (ornaments
    hang from it on strings); starts and ends at its left end."""
    label = b.part("garland%d" % gi, "#ffd54a")
    mid = (left + right) / 2 + complex(0, 2 * sag)

    def at(u, off=0.0):
        return (1 - u) ** 2 * left + 2 * u * (1 - u) * mid + u * u * right + complex(0, off)

    b.add([at(s / 30.0) for s in range(31)], label)                 # top edge, left -> right
    hang = sorted(GARLAND_ORNAMENTS.get(gi, []), reverse=True)
    s = 30
    for (u, kind, size, colour) in hang + [(0.0, None, 0, None)]:
        while s / 30.0 > u:                                          # bottom edge, right -> left
            b.go(at(s / 30.0, thick), label)
            s -= 1
        if kind is None:
            break
        p = at(u, thick)
        b.go(p, label)
        string = b.part("string", "#9aa6c4", fill=False, width=1.0)
        end = p + complex(0, STRING)
        b.go(end, string)
        ol = "orn_g%d_%.2f" % (gi, u)
        b.part(ol, colour)
        b.add(ornament_at(kind, end, size), ol)
        b.go(end, string)
        b.go(p, label)
    b.go(at(0.0, thick), label)
    b.go(left, label)


def tree_part(b, outline):
    """From the left side of the hem, up the left edge, round the star, down
    the right edge to the right side of the hem - with the garlands and the
    branch-tip ornaments on the way."""
    tree = b.part("tree", "#2fbf5f", width=2.4)
    n = len(outline)
    half = n // 2
    # hem points next to the trunk
    i_left = min(range(half, n), key=lambda i: abs(outline[i].real + F.TRUNK_W) + abs(outline[i].imag - F.TIERS[-1][0]) * 3)
    i_right = min(range(1, half), key=lambda i: abs(outline[i].real - F.TRUNK_W) + abs(outline[i].imag - F.TIERS[-1][0]) * 3)
    order = list(range(i_left, n)) + list(range(0, i_right + 1))
    tips = {}
    for k, (yb, w) in enumerate(F.TIERS[:3]):
        for side in (-1, 1):
            tip = complex(side * (w + 0.03), yb + 0.035)
            idx = min(range(n), key=lambda i: abs(outline[i] - tip))
            tips[idx] = (k, side)
    # garlands start on the left edge where it crosses their height
    garlands = {}
    for gi, (yl, yr) in enumerate(GARLAND_Y):
        xl, xr = edge_x(outline, yl, -1) + 0.03, edge_x(outline, yr, 1) - 0.03
        left = complex(xl, yl)
        idx = min(range(half, n), key=lambda i: abs(outline[i] - left))
        garlands[idx] = (gi, left, complex(xr, yr))
    for i in order:
        z = outline[i]
        b.go(z, tree)
        if i == 0:                                                   # the apex: the star
            star = b.part("star", "#ffd54a")
            s = F.star_outline()
            b.add(s + [s[0]], star)
            b.go(z, tree)
        if i in garlands:
            gi, left, right = garlands[i]
            garland_loop(b, gi, left, right, 0.05)
            b.go(z, tree)
        if i in tips:
            k, side = tips[i]
            kind, size, colour = TIP_ORNAMENTS[k]
            string = b.part("string", "#9aa6c4", fill=False, width=1.0)
            end = z + complex(0, STRING)
            b.go(end, string)
            ol = b.part("orn_tip%d%s" % (k, "L" if side < 0 else "R"), colour)
            b.add(ornament_at(kind, end, size), ol)
            b.go(end, string)
            b.go(z, tree)
    return outline[i_left], outline[i_right]


def gift(b, gi, x, w, h, box, ribbon):
    """Walking right along the ground: up the box's left side (the horizontal
    ribbon there and back), along the top (the bow, the vertical ribbon down
    and back), down the right side."""
    G = F.GROUND_Y
    x0, x1, y0, ym = x - w / 2, x + w / 2, G - h, G - h / 2
    bl = b.part("box%d" % gi, box)
    rl = b.part("ribbon%d" % gi, ribbon, fill=False, width=3.0)
    bowl = b.part("bow%d" % gi, ribbon)
    b.go(complex(x0, G), bl)
    b.go(complex(x0, ym), bl)
    b.add([complex(x0 + (x1 - x0) * s / 8.0, ym) for s in range(1, 9)], rl)   # ribbon across
    b.add([complex(x1 - (x1 - x0) * s / 8.0, ym) for s in range(1, 9)], rl)   # ... and back
    b.go(complex(x0, y0), bl)
    b.go(complex(x, y0), bl)
    centre = complex(x, y0 - 0.035)
    b.go(centre, bowl)
    bow = F.bow_outline(x, y0 - 0.035, w * 0.28, 0.07)
    b.add(bow + [bow[0]], bowl)
    b.go(complex(x, y0), bl)
    b.add([complex(x, y0 + h * s / 8.0) for s in range(1, 9)], rl)            # ribbon down
    b.add([complex(x, G - h * s / 8.0) for s in range(1, 9)], rl)             # ... and up
    b.go(complex(x1, y0), bl)
    b.go(complex(x1, G), bl)


def one_stroke():
    """-> (points, labels, parts): the whole picture as one closed path."""
    b = Builder()
    G = F.GROUND_Y
    ground = b.part("ground", "#c9d4ee", fill=False, width=1.4)
    trunk = b.part("trunk", "#8b5a2b")
    gifts = sorted(F.GIFTS)
    b.go(complex(-1.05, G), ground)
    for gi, spec in enumerate(gifts):
        if spec[0] < 0:
            gift(b, gi, *spec)
            b.go(complex(spec[0] + spec[1] / 2, G), ground)
    b.go(complex(-F.TRUNK_W, G), trunk)
    outline = F.tree_outline()
    start = len(b.pts)
    hem_l, hem_r = tree_part(b, outline)
    b.pts.insert(start, complex(-F.TRUNK_W, hem_l.imag))          # the trunk's left side, up
    b.labels.insert(start, trunk)
    b.go(complex(F.TRUNK_W, hem_r.imag), trunk)
    b.go(complex(F.TRUNK_W, G), trunk)
    for gi, spec in enumerate(gifts):
        if spec[0] > 0:
            b.go(complex(spec[0] - spec[1] / 2, G), ground)
            gift(b, gi, *spec)
    b.go(complex(1.05, G), ground)
    # back along the ground to the start (drawn over the same line)
    b.go(complex(-1.05, G), ground)
    return b.pts, b.labels, b.parts


def resample_labelled(points, labels, n):
    """Like fourier.resample, also giving each sample the label of the piece
    of path it lies on."""
    pts = list(points) + [points[0]]
    seg = [abs(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)]
    total = sum(seg)
    out, lab, i, acc = [], [], 0, 0.0
    for k in range(n):
        target = total * k / float(n)
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        u = (target - acc) / seg[i] if seg[i] else 0.0
        out.append(pts[i] + (pts[i + 1] - pts[i]) * u)
        lab.append(labels[(i + 1) % len(labels)])       # the part this piece leads into
    return out, lab


# ---------------------------------------------------------------------
#  The model the window uses
# ---------------------------------------------------------------------
class OneStroke:
    """The one-stroke picture: samples with labels, ONE set of Fourier
    coefficients (computed once), the reconstruction for the chosen number
    of terms, and which stretch of it belongs to which part."""
    SAMPLES = 2048
    CURVE = 8192                       # points of the reconstruction we draw (2^13)

    def __init__(self, terms=1000):
        self.path, path_labels, self.parts = one_stroke()
        self.samples, self.labels = resample_labelled(self.path, path_labels, self.SAMPLES)
        self.coeffs = F.dft(self.samples)
        self.order = "size"
        self.set_terms(terms)

    def set_terms(self, terms):
        self.terms = max(1, min(int(terms), len(self.coeffs)))
        kept = F.truncate(self.coeffs, self.terms)
        self.chain_coeffs = F.by_size(kept) if self.order == "size" else F.by_frequency(kept)
        self.error = F.max_error(kept, self.samples)
        m = self.CURVE
        self.curve = F.reconstruct(kept, m)
        self.curve.append(self.curve[0])
        self.curve_labels = [self.labels[min(self.SAMPLES - 1, k * self.SAMPLES // m)]
                             for k in range(m + 1)]
        # consecutive stretches of the same part: (label, first, last) indices
        self.runs = []
        start = 0
        for k in range(1, m + 2):
            if k == m + 1 or self.curve_labels[k] != self.curve_labels[start]:
                self.runs.append((self.curve_labels[start], start, min(k, m)))
                start = k

    def set_order(self, order):
        self.order = order
        self.set_terms(self.terms)

    def part_points(self, label):
        """The reconstructed curve's points for one part, in order - its fill."""
        return [z for z, l in zip(self.curve, self.curve_labels) if l == label]
