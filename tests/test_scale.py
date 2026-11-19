# -*- coding: utf-8 -*-
"""Three sizes: a big window draws the scene 1.5x / 2x bigger (same font)."""
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import cats as catlib                 # noqa: E402
from engine import terminal                       # noqa: E402
from engine.manager import SceneManager           # noqa: E402
from engine.render import (CH, CW, SCALES, pick_scale, scaled,  # noqa: E402
                           stage_size, text_width, view_canvas)

CATS = os.path.join(ROOT, "cats.json")
SKINS = os.path.join(ROOT, "skins")


def manager(**cli):
    cli.setdefault("cats", CATS)
    return SceneManager("scenes", {}, {}, cli)


def run(name, size, seconds=60.0, seed=5, **cli):
    random.seed(seed)
    sc = manager(skip_intro=True, **cli).create(name)
    k = pick_scale(size[0], size[1], sc.MAX_SCALE)
    cv = view_canvas(size[0], size[1], sc.CW, sc.CH, k=k)
    sc.set_scale(k)
    sc.set_view(cv.view())
    terminal.simulate(sc, seconds)
    sc.draw(cv)
    return sc, cv


class PickScaleTests(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(stage_size(1), (CW, CH))
        self.assertEqual(stage_size(1.5), (117, 41))
        self.assertEqual(stage_size(2), (156, 54))

    def test_the_biggest_size_that_fits(self):
        self.assertEqual(pick_scale(CW, CH, 2), 1)
        self.assertEqual(pick_scale(116, 60, 2), 1)
        self.assertEqual(pick_scale(117, 41, 2), 1.5)
        self.assertEqual(pick_scale(200, 45, 2), 1.5)
        self.assertEqual(pick_scale(156, 54, 2), 2)
        self.assertEqual(pick_scale(156, 48, 2), 2)     # a few rows of sky may go
        self.assertEqual(pick_scale(320, 88, 2), 2)

    def test_never_bigger_than_the_scene_allows(self):
        self.assertEqual(pick_scale(320, 88, 1), 1)
        self.assertEqual(pick_scale(320, 88, 1.5), 1.5)

    def test_scaled_positions(self):
        for v in (0, 3, 25.4, 25.5, 26.6):
            self.assertEqual(scaled(v, 1), int(round(v)))
        self.assertEqual(scaled(25, 2), 51)              # bottom half of cell 25
        self.assertEqual(scaled(0, 2), 1)


class BigSceneTests(unittest.TestCase):
    def test_christmas_is_drawn_bigger(self):
        for size, k in (((120, 41), 1.5), ((160, 54), 2), ((300, 80), 2)):
            with self.subTest(size=size):
                sc, cv = run("christmas", size)
                self.assertEqual((sc.k, cv.k), (k, k))
                rows = cv.plain_rows()
                self.assertEqual(len(rows), size[1])
                self.assertTrue(all(text_width(r) <= size[0] for r in rows))
                ground = rows[int(23 * k) + cv.oy]
                self.assertEqual(len(ground), size[0])          # edge to edge
                half = max(h for _y, h, _c in sc.tree.rows)
                self.assertGreaterEqual(half, 15 * k)           # a bigger tree

    def test_bigger_cats_stay_on_the_floor_and_in_the_window(self):
        sc, cv = run("christmas", (160, 54), seconds=150.0)
        for c in sc.cats:
            skin = c.skin.at(2)
            self.assertEqual(skin.scale, 2)
            foot = cv.py(c.y - c.z - c.lift)
            self.assertLess(foot + cv.oy, cv.h)
            self.assertGreaterEqual(c.x * 2 - skin.width / 2.0, cv.x0 - 2)
            self.assertLessEqual(c.x * 2 + skin.width / 2.0, cv.x1 + 2)

    def test_greeting_and_hats_at_2x(self):
        sc, cv = run("christmas", (160, 54), seconds=140.0, stay=True)
        self.assertEqual(sc.phase, "hold")
        text = "\n".join(cv.plain_rows())
        self.assertIn("Merry", text)
        self.assertIn("/######\\", text)                   # the big Santa hat

    def test_resizing_switches_size_and_back(self):
        random.seed(2)
        m = manager()
        sc = m.create("christmas")
        terminal.simulate(sc, 30.0)
        for size in ((160, 54), (120, 41), (CW, CH), (160, 54)):
            k = pick_scale(size[0], size[1], sc.MAX_SCALE)
            cv = view_canvas(size[0], size[1], sc.CW, sc.CH, k=k)
            sc.draw(cv)
            sc.update(0.1)
            self.assertEqual(sc.k, k)
        a = terminal.snapshot(m, "christmas", 30.0, seed=4)
        b = terminal.snapshot(m, "christmas", 30.0, seed=4, size=(CW, CH))
        self.assertEqual(a, b)

    def test_scenes_without_big_art_stay_normal_size(self):
        for name in manager().names():
            with self.subTest(scene=name):
                sc, cv = run(name, (200, 60))
                self.assertLessEqual(sc.k, sc.MAX_SCALE)
                self.assertEqual(len(cv.plain_rows()), 60)


class BigSkinTests(unittest.TestCase):
    def test_every_skin_has_every_size(self):
        for f in sorted(os.listdir(SKINS)):
            if not f.endswith(".cat"):
                continue
            skin = catlib.load_skin(f[:-4], SKINS)
            for k in SCALES[1:]:
                with self.subTest(skin=f, k=k):
                    big = skin.at(k)
                    self.assertEqual(big.scale, k)
                    self.assertEqual(big.palette, skin.palette)      # same colours
                    self.assertAlmostEqual(big.height / float(skin.height), k, delta=0.25)
                    self.assertAlmostEqual(big.width / float(skin.width), k, delta=0.4)

    def test_big_drawings_fit_their_box(self):
        for f in sorted(os.listdir(SKINS)):
            if f.endswith(".cat"):
                skin = catlib.load_skin(f[:-4], SKINS)
                out = "\n".join(catlib.preview_skin(skin, False))
                self.assertNotIn("WARNING", out, f)

    def test_scale_section_errors(self):
        bad = "name: x\nsize: 5 2\n@head\n|o\n@pose stand\n@layer 0 0\n|a\n" \
              "@pose sit\n@layer 0 0\n|b\n@scale 2\npalette: O=1\n"
        with self.assertRaises(catlib.SkinError):
            catlib.parse_skin(bad, "x", "x.cat", None)
        missing = "name: x\nsize: 5 2\n@head\n|o\n@pose stand\n@layer 0 0\n|a\n" \
                  "@pose sit\n@layer 0 0\n|b\n@scale 2\nsize: 10 4\n"
        with self.assertRaises(catlib.SkinError):
            catlib.parse_skin(missing, "x", "x.cat", None)

    def test_a_skin_without_big_drawings_still_works(self):
        text = "name: x\nsize: 5 2\n@head\n|o\n@pose stand\n@layer 0 0\n|a\n" \
               "@pose sit\n@layer 0 0\n|b\n"
        skin = catlib.parse_skin(text, "x", "x.cat", None)
        self.assertIs(skin.at(2), skin)


if __name__ == "__main__":
    unittest.main()
