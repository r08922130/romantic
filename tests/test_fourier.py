# -*- coding: utf-8 -*-
"""Fourier epicycles opening (engine/fourier.py) and how scenes use it."""
import cmath
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import fourier as F                  # noqa: E402
from engine import terminal                      # noqa: E402
from engine.manager import SceneManager          # noqa: E402
from engine.render import Canvas                 # noqa: E402

CATS = os.path.join(ROOT, "cats.json")


def manager(**cli):
    cli.setdefault("cats", CATS)
    return SceneManager("scenes", {}, {}, cli)


def christmas(**cli):
    random.seed(2)
    return manager(**cli).create("christmas")


class MathTests(unittest.TestCase):
    def test_resample_is_even_by_arc_length(self):
        # a long edge and a short one: equal spacing all the way round
        pts = F.resample([0j, 30 + 0j, 30 + 2j, 0 + 2j], 64)
        steps = [abs(pts[(i + 1) % 64] - pts[i]) for i in range(64)]
        self.assertLess(max(steps) - min(steps), 1e-9 + 64 / 64.0 * 0.0 + 1e-6)

    def test_signed_frequencies(self):
        self.assertEqual([F.freq_of(k, 8) for k in range(8)], [0, 1, 2, 3, -4, -3, -2, -1])
        self.assertEqual([F.freq_of(k, 7) for k in range(7)], [0, 1, 2, 3, -3, -2, -1])

    def test_dft_finds_a_known_rotation(self):
        # z(t) = 3 + 5 exp(i 2 pi 2 t) + 1.5 exp(-i 2 pi t)
        N = 32
        z = [3 + 5 * cmath.exp(2j * math.pi * 2 * k / N) + 1.5 * cmath.exp(-2j * math.pi * k / N)
             for k in range(N)]
        c = dict(F.dft(z))
        self.assertAlmostEqual(abs(c[0] - 3), 0, places=9)
        self.assertAlmostEqual(abs(c[2] - 5), 0, places=9)
        self.assertAlmostEqual(abs(c[-1] - 1.5), 0, places=9)
        self.assertLess(sum(abs(v) for n, v in c.items() if n not in (0, 2, -1)), 1e-9)

    def test_every_term_gives_the_samples_back(self):
        shape = christmas().fourier_shape()
        pts, coeffs = F.coefficients(shape, 256)
        self.assertLess(F.max_error(coeffs, pts), 1e-9)

    def test_more_terms_fit_better(self):
        pts, coeffs = F.coefficients(christmas().fourier_shape(), 256)
        errs = [F.max_error(F.truncate(coeffs, n), pts) / F.ASPECT for n in (20, 50, 100, 200)]
        self.assertEqual(errs, sorted(errs, reverse=True))
        self.assertLess(errs[2], 0.25)                    # 100 terms: within a quarter row
        self.assertLess(errs[3], 0.1)

    def test_truncate_keeps_the_lowest_frequencies(self):
        _pts, coeffs = F.coefficients(christmas().fourier_shape(), 256)
        self.assertEqual(sorted(n for n, _c in F.truncate(coeffs, 5)), [-2, -1, 0, 1, 2])

    def test_coefficients_come_from_the_outline(self):
        shape = christmas().fourier_shape()
        _p, a = F.coefficients(shape, 128)
        moved = [(x + 3, y) for (x, y) in shape]               # shift right 3 columns
        _p, b = F.coefficients(moved, 128)
        self.assertAlmostEqual(dict(b)[0].real - dict(a)[0].real, 3.0, places=6)
        wide = [(x * 1.5, y) for (x, y) in shape]
        _p, c = F.coefficients(wide, 128)
        self.assertNotAlmostEqual(abs(dict(c)[1]), abs(dict(a)[1]), places=3)

    def test_chain_tip_is_the_curve(self):
        _pts, coeffs = F.coefficients(christmas().fourier_shape(), 256)
        some = F.truncate(coeffs, 50)
        for t in (0.0, 0.13, 0.5, 0.77):
            self.assertAlmostEqual(abs(F.chain(some, t)[-1] - F.evaluate(some, t)), 0, places=9)


class PreludeTests(unittest.TestCase):
    def test_off_by_default_and_scene_unchanged(self):
        self.assertIsNone(christmas().prelude)
        a = terminal.snapshot(manager(), "christmas", 30.0, seed=4)
        b = terminal.snapshot(manager(fourier=False), "christmas", 30.0, seed=4)
        self.assertEqual(a, b)

    def test_trace_is_the_tree(self):
        sc = christmas(fourier=True)
        p = sc.prelude
        self.assertEqual(p.terms, 100)
        tree_edges = set()
        for (y, h, _c) in sc.tree.rows:
            tree_edges |= {(sc.CX - h, y), (sc.CX + h, y)}
        trace = {(x, y) for (x, y, _ch) in p.trail}
        near = sum(1 for (x, y) in tree_edges
                   if any((x + dx, y + dy) in trace for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
        self.assertGreater(near / float(len(tree_edges)), 0.95)   # every edge is traced

    def test_scene_waits_then_runs_as_before(self):
        sc = christmas(fourier=True, fourier_terms=50)
        cv = Canvas()
        frames = 0
        while not sc.prelude.done:
            sc.update(1 / 30.0)
            frames += 1
            if not sc.prelude.done:
                self.assertEqual(sc.t, 0.0)               # the scene's clock waits
            if frames == int((sc.prelude.APPEAR + sc.prelude.DRAW * 0.5) * 30):
                sc.draw(cv)
                self.assertIn("@", "\n".join(cv.plain_rows()))     # the drawing tip
        terminal.simulate(sc, 30.0)
        self.assertIsNone(sc.prelude)                     # the trace has faded away
        self.assertGreater(sc.t, 29.0)
        sc.draw(cv)
        self.assertIn("/", "\n".join(cv.plain_rows()))
        terminal.simulate(sc, 120.0)
        self.assertIn(sc.phase, ("gather", "hold", "free"))

    def test_skip_intro_skips_it(self):
        self.assertIsNone(christmas(fourier=True, skip_intro=True).prelude)

    def test_scenes_without_an_outline_ignore_it(self):
        random.seed(1)
        self.assertIsNone(manager(fourier=True).create("osaka").prelude)

    def test_terms_setting(self):
        for n in (20, 50, 100, 200):
            self.assertEqual(christmas(fourier=True, fourier_terms=n).prelude.terms, n)


if __name__ == "__main__":
    unittest.main()
