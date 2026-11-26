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


class OneStrokeTests(unittest.TestCase):
    """The whole picture as ONE closed curve with ONE Fourier series."""

    @classmethod
    def setUpClass(cls):
        import onestroke as O
        cls.O = O
        cls.m = O.OneStroke(1000)

    def test_fft_equals_dft(self):
        N = 128
        z = [complex(math.sin(k * 0.37), (k % 7) - 3) for k in range(N)]
        slow = [sum(z[j] * cmath.exp(-2j * math.pi * k * j / N) for j in range(N)) for k in range(N)]
        self.assertLess(max(abs(a - b) for a, b in zip(F.fft(z), slow)), 1e-9)

    def test_reconstruct_equals_evaluate(self):
        kept = F.truncate(self.m.coeffs, 300)
        curve = F.reconstruct(kept, 1024)
        for k in (0, 17, 512, 1000):
            self.assertAlmostEqual(abs(curve[k] - F.evaluate(kept, k / 1024.0)), 0, places=9)

    def test_one_curve_has_every_part(self):
        labels = set(self.m.labels)
        for need in ("tree", "star", "trunk", "ground", "string"):
            self.assertIn(need, labels)
        self.assertEqual(sum(1 for l in labels if l.startswith("garland")), 3)
        self.assertGreaterEqual(sum(1 for l in labels if l.startswith("orn")), 10)
        for g in range(len(F.GIFTS)):
            for part in ("box%d", "ribbon%d", "bow%d"):
                self.assertIn(part % g, labels)

    def test_the_path_is_continuous(self):
        path = self.m.path
        steps = [abs(path[i + 1] - path[i]) for i in range(len(path) - 1)]
        self.assertLess(max(steps), 2.2)          # the longest is the ground back to the start
        self.assertLess(sorted(steps)[-2], 0.5)   # every other step is short: no jumps

    def test_one_series_draws_everything(self):
        m = self.m
        self.assertLess(F.max_error(m.coeffs, m.samples), 1e-9)              # all 2048 terms: exact
        errs = [F.max_error(F.truncate(m.coeffs, n), m.samples) for n in (200, 500, 1000, 1500)]
        self.assertEqual(errs, sorted(errs, reverse=True))
        self.assertLess(errs[2], 0.01)          # 1000 terms: within 1% of a tree unit

    def test_each_part_fills_from_its_stretch(self):
        for label, part in self.m.parts.items():
            if part["fill"]:
                self.assertGreaterEqual(len(self.m.part_points(label)), 3, label)


class CatTests(unittest.TestCase):
    def test_each_cat_is_one_continuous_curve(self):
        import catart as C
        for name in C.CATS:
            path, labels, parts = C.cat_stroke(name)
            self.assertEqual(len(path), len(labels))
            self.assertEqual(path[0], path[-1])                       # closed
            self.assertEqual(set(labels), set(parts))                 # every part is drawn
            steps = [(abs(path[i] - path[i - 1]), labels[i]) for i in range(1, len(path))]
            total = sum(s for s, _l in steps)
            links = sum(s for s, l in steps if l == "link")
            self.assertLess(links, 0.06 * total, name)                # hardly any joins
            self.assertLess(max(s for s, l in steps if l == "link"), 0.1, name)

    def test_one_series_draws_each_cat(self):
        import catart as C
        for name in C.CATS:
            path, labels, parts = C.cat_stroke(name)
            samples, labs = C.resample_detail(path, labels)
            self.assertEqual(len(samples), C.SAMPLES)
            for label, part in parts.items():
                if part["fill"]:
                    self.assertGreaterEqual(labs.count(label), 8, label)
            coeffs = F.dft(samples)
            self.assertLess(F.max_error(coeffs, samples), 1e-9)       # all terms: exact
            self.assertLess(F.max_error(F.truncate(coeffs, 2000), samples), 0.01)


class WebPageTests(unittest.TestCase):
    def test_page_holds_the_one_stroke(self):
        import json
        import tempfile
        import build_html as B
        out = os.path.join(tempfile.mkdtemp(), "fourier.html")
        html = open(B.build(out), encoding="utf-8").read()
        self.assertNotIn("/*DATA*/", html)
        start = html.index("const DATA = ") + len("const DATA = ")
        data = json.loads(html[start:html.index(";</script>", start)])
        self.assertNotIn("parts", data)                       # only the one stroke
        one = data["one"]
        self.assertEqual(len(one["pts"]), 2 * len(one["lab"]))
        self.assertEqual(set(one["names"]), set(one["parts"]))
        self.assertEqual([c["name"] for c in data["cats"]], ["box", "lying", "tabby", "sitting"])
        for cat in data["cats"]:
            self.assertEqual(len(cat["pts"]), 2 * len(cat["lab"]))
            self.assertEqual(set(cat["names"]), set(cat["parts"]))


class WindowTests(unittest.TestCase):
    def test_window_runs(self):
        import tkinter as tk
        import app as A
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            root.geometry("700x600")
            a = A.App(root, 1000, 4.0)
            a.paused = True
            for t in (0.5, 6.0, 30.0, 60.0):
                a.time = t
                a.render()
            root.update()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
