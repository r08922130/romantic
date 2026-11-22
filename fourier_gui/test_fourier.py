# -*- coding: utf-8 -*-
"""Tests for the Fourier maths of the GUI.   python fourier_gui/test_fourier.py"""
import cmath
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fourier as F          # noqa: E402


def setup():
    pts = F.resample(F.tree_outline(), 512)
    return pts, F.dft(pts)


PTS, COEFFS = setup()
HEIGHT = max(z.imag for z in PTS) - min(z.imag for z in PTS)


class FourierTests(unittest.TestCase):
    def test_outline_is_a_closed_symmetric_tree(self):
        o = F.tree_outline()
        self.assertGreater(len(o), 100)
        top = min(o, key=lambda z: z.imag)
        self.assertAlmostEqual(top.real, 0.0, places=9)               # the star's top point
        xs = sorted(round(z.real, 6) for z in o)
        self.assertEqual(xs, sorted(-x for x in xs))                  # left / right mirror

    def test_resample_even_by_arc_length(self):
        n = len(PTS)
        o = F.tree_outline() + [F.tree_outline()[0]]
        spacing = sum(abs(o[i + 1] - o[i]) for i in range(len(o) - 1)) / n   # perimeter / n
        steps = [abs(PTS[(i + 1) % n] - PTS[i]) for i in range(n)]
        # every step is one spacing along the curve; only a chord across a
        # corner is a little shorter than that
        self.assertLess(max(steps), spacing * 1.0001)
        self.assertGreater(sorted(steps)[n // 5], spacing * 0.99)

    def test_signed_frequencies(self):
        self.assertEqual([F.freq_of(k, 6) for k in range(6)], [0, 1, 2, -3, -2, -1])

    def test_dft_of_known_rotations(self):
        N = 64
        z = [2 - 1j + 4 * cmath.exp(2j * math.pi * 3 * k / N)
             + 0.5j * cmath.exp(-2j * math.pi * 5 * k / N) for k in range(N)]
        c = dict(F.dft(z))
        self.assertAlmostEqual(abs(c[0] - (2 - 1j)), 0, places=9)
        self.assertAlmostEqual(abs(c[3] - 4), 0, places=9)
        self.assertAlmostEqual(abs(c[-5] - 0.5j), 0, places=9)

    def test_all_terms_reproduce_the_samples(self):
        self.assertLess(F.max_error(COEFFS, PTS), 1e-9)

    def test_error_shrinks_with_more_terms(self):
        errs = [F.max_error(F.truncate(COEFFS, n), PTS) for n in (20, 50, 100, 200)]
        self.assertEqual(errs, sorted(errs, reverse=True))
        self.assertLess(errs[3] / HEIGHT, 0.01)            # 200 terms: within 1% of the height

    def test_truncate_keeps_lowest_frequencies(self):
        self.assertEqual(sorted(n for n, _c in F.truncate(COEFFS, 7)), [-3, -2, -1, 0, 1, 2, 3])

    def test_drawing_orders_give_the_same_tip(self):
        kept = F.truncate(COEFFS, 100)
        for t in (0.0, 0.31, 0.9):
            a = F.chain(F.by_size(kept), t)[-1]
            b = F.chain(F.by_frequency(kept), t)[-1]
            self.assertAlmostEqual(abs(a - b), 0, places=9)
            self.assertAlmostEqual(abs(a - F.evaluate(kept, t)), 0, places=9)

    def test_coefficients_follow_the_outline(self):
        shifted = F.dft([z + (1 + 2j) for z in PTS])
        self.assertAlmostEqual(abs(dict(shifted)[0] - dict(COEFFS)[0] - (1 + 2j)), 0, places=9)
        scaled = F.dft([z * 2 for z in PTS])
        self.assertAlmostEqual(abs(dict(scaled)[1]), 2 * abs(dict(COEFFS)[1]), places=9)


class SceneTests(unittest.TestCase):
    """Every decoration and present has its own Fourier series too."""

    def test_every_shape_has_its_own_series(self):
        shapes = F.scene_shapes()
        groups = [s[0] for s in shapes]
        for g in ("tree", "top", "garlands", "ornaments", "gifts"):
            self.assertIn(g, groups)
        self.assertEqual(groups.count("ornaments"), len(F.ORNAMENTS))
        self.assertEqual(groups.count("gifts"), 4 * len(F.GIFTS))       # box, 2 ribbons, bow
        for group, name, outline, colour, samples, cap in shapes:
            with self.subTest(shape=name):
                pts = F.resample(outline, samples)
                coeffs = F.dft(pts)
                self.assertLess(F.max_error(coeffs, pts), 1e-9)       # exact with every term
                size = max(abs(z - pts[0]) for z in pts)
                kept = F.truncate(coeffs, cap or 100)
                self.assertLess(F.max_error(kept, pts) / size, 0.1)   # recognisable

    def test_ornament_kinds(self):
        kinds = {k for k, *_rest in F.ORNAMENTS}
        self.assertEqual(kinds, {"bauble", "heart", "bell", "candy"})

    def test_timeline_draws_groups_in_order(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import app as A
        m = A.Model(terms=50, seconds=8.0)
        starts = {}
        for d in m.drawings:
            starts.setdefault(d.group, d.start)
            self.assertEqual(d.start, starts[d.group])               # a group starts together
        order = [g for g, _share in A.GROUPS]
        times = [starts[g] for g in order]
        self.assertEqual(times, sorted(times))
        self.assertGreater(m.done, m.draw_end)
        self.assertTrue(all(d.terms <= 50 for d in m.drawings))


if __name__ == "__main__":
    unittest.main()
