# -*- coding: utf-8 -*-
"""Any window size: wide windows show more scenery, small ones crop."""
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import terminal                       # noqa: E402
from engine.manager import SceneManager           # noqa: E402
from engine.render import (CH, CW, MIN_H, MIN_W, lay_out,  # noqa: E402
                           text_width, view_canvas)

CATS = os.path.join(ROOT, "cats.json")
SIZES = [(MIN_W, MIN_H), (CW, CH), (100, 30), (160, 40), (300, 70)]


def manager(**cli):
    cli.setdefault("cats", CATS)
    return SceneManager("scenes", {}, {}, cli)


def run(name, size, seconds=40.0, seed=5, **cli):
    random.seed(seed)
    m = manager(skip_intro=True, **cli)
    sc = m.create(name)
    cv = view_canvas(size[0], size[1], sc.CW, sc.CH)
    sc.set_view(cv.view())
    terminal.simulate(sc, seconds)
    sc.draw(cv)
    return sc, cv


class WindowSizeTests(unittest.TestCase):
    def test_every_scene_runs_at_every_size(self):
        for name in manager().names():
            for size in SIZES:
                with self.subTest(scene=name, size=size):
                    sc, cv = run(name, size)
                    rows = cv.plain_rows()
                    self.assertEqual(len(rows), size[1])
                    self.assertTrue(all(text_width(r) <= size[0] for r in rows))

    def test_standard_size_is_unchanged(self):
        m = manager()
        for name in m.names():
            with self.subTest(scene=name):
                a = terminal.snapshot(m, name, 30.0, seed=4)
                b = terminal.snapshot(m, name, 30.0, seed=4, size=(CW, CH))
                self.assertEqual(a, b)

    def test_wide_window_fills_the_ground_edge_to_edge(self):
        for name in manager().names():
            with self.subTest(scene=name):
                sc, cv = run(name, (200, 40))
                ground = cv.plain_rows()[23 + cv.oy]          # world row 23
                self.assertNotEqual(ground[:3].strip(), "")
                self.assertEqual(len(ground), 200)

    def test_wide_window_has_stars_and_scenery_in_the_margins(self):
        sc, cv = run("christmas", (220, 50))
        rows = cv.plain_rows()
        left = [r[:cv.ox] for r in rows[:cv.oy + 17]]
        self.assertTrue(any(c != " " for r in left for c in r))   # stars / snow
        sc, cv = run("tokyo", (220, 40))
        rows = cv.plain_rows()
        self.assertTrue(any("|" in r[:cv.ox] for r in rows))      # office blocks

    def test_cats_stay_in_the_window(self):
        for size in [(MIN_W, MIN_H), (240, 40)]:
            sc, cv = run("christmas", size, seconds=150.0)
            for c in sc.cats:
                self.assertGreaterEqual(c.x - c.W / 2.0, cv.x0 - 1)
                self.assertLessEqual(c.x + c.W / 2.0, cv.x1 + 1)

    def test_small_window_keeps_the_greeting_on_screen(self):
        sc, cv = run("christmas", (MIN_W, MIN_H), seconds=140.0, stay=True)
        self.assertEqual(sc.phase, "hold")
        text = "\n".join(cv.plain_rows()[:3])
        self.assertIn("Merry", text)

    def test_too_small(self):
        self.assertIsNone(view_canvas(MIN_W - 1, 30))
        self.assertIsNone(view_canvas(100, MIN_H - 1))
        with self.assertRaises(ValueError):
            terminal.snapshot(manager(), "christmas", 1.0, size=(40, 20))

    def test_maximize_leaves_windows_terminal_alone(self):
        old = dict(os.environ)
        try:
            os.environ["WT_SESSION"] = "x"
            os.environ.pop("ROMANCE_CONHOST", None)
            self.assertIsNone(terminal.maximize_window())  # cannot resize it
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_launchers_maximise_the_window(self):
        with open(os.path.join(ROOT, "run.bat"), "rb") as f:
            bat = f.read()
        bat.decode("ascii")                                    # cmd.exe needs ASCII
        self.assertEqual(bat.count(b"\n"), bat.count(b"\r\n"))  # and CRLF
        self.assertIn(b"--maximize", bat)
        self.assertIn(b"conhost.exe", bat)
        with open(os.path.join(ROOT, "run.command"), "rb") as f:
            cmd = f.read()
        self.assertNotIn(b"\r\n", cmd)
        self.assertIn(b"zoomed", cmd)
        self.assertNotIn(b"fontSize", cmd)                     # the font is left alone
        self.assertIn(b"trap restore_window EXIT", cmd)

    def test_lay_out(self):
        rng = random.Random(1)
        make = lambda r: (5, 1, None)        # noqa: E731
        right = lay_out(rng, 78, 100, make)
        self.assertEqual([x for x, _w, _d in right], [78, 84, 90, 96])
        left = lay_out(rng, 0, -20, make, leftwards=True)
        self.assertEqual([x for x, _w, _d in left], [-5, -11, -17, -23])
        self.assertEqual(lay_out(rng, 78, 78, make), [])
        self.assertEqual(lay_out(rng, 0, 7, make, leftwards=True), [])


if __name__ == "__main__":
    unittest.main()
