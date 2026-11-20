# -*- coding: utf-8 -*-
"""People (the two of you) walking around with the cats."""
import json
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import cats as catlib            # noqa: E402
from engine import terminal                  # noqa: E402
from engine.manager import SceneManager      # noqa: E402
from engine.menu import Menu                 # noqa: E402
from engine.render import Canvas, text_width  # noqa: E402

CATS = os.path.join(ROOT, "cats.json")
SKINS = os.path.join(ROOT, "skins")


def people(scene):
    return [c for c in scene.cats if getattr(c, "is_person", False)]


def manager(**cli):
    cli.setdefault("cats", CATS)
    return SceneManager("scenes", {}, {}, cli)


class PeopleTests(unittest.TestCase):
    def test_cats_json_has_the_two_of_you(self):
        cfg, _d = catlib.read_config(CATS)
        self.assertEqual([p["skin"] for p in cfg["people"]], ["boyfriend", "girlfriend"])
        sc = manager().create("christmas")
        self.assertEqual(len(people(sc)), 2)
        self.assertEqual(len(sc.cats) - 2, len([c for c in cfg["cats"]
                                                if c.get("enabled", True)]))

    def test_skins_draw_inside_their_box(self):
        for name in ("boyfriend", "girlfriend"):
            skin = catlib.load_skin(name, SKINS)
            out = "\n".join(catlib.preview_skin(skin, False))
            self.assertNotIn("WARNING", out, name)
            self.assertIn("-- peace", out)                    # the peace sign pose
            self.assertIn("(o)-(o)", out)                     # glasses

    def test_every_scene_runs_with_people(self):
        for name in manager().names():
            with self.subTest(scene=name):
                random.seed(3)
                sc = manager().create(name)
                cv = Canvas(sc.CW, sc.CH)
                for _ in range(int(200 * 30)):
                    sc.update(1 / 30.0)
                    if sc.phase == "hold":
                        break
                sc.draw(cv)
                self.assertTrue(all(text_width(r) <= cv.w for r in cv.plain_rows()))

    def test_people_stand_together_in_the_middle_at_the_surprise(self):
        random.seed(5)
        sc = manager(stay=True).create("christmas")
        terminal.simulate(sc, 160.0)
        self.assertEqual(sc.phase, "hold")
        a, b = sorted(people(sc), key=lambda p: p.x)
        self.assertLess(abs((a.x + b.x) / 2.0 - sc.CX), 2.0)
        self.assertEqual((a.face, b.face), (1, -1))           # facing each other
        for c in sc.cats:
            if c not in (a, b):
                self.assertGreater(abs(c.x - sc.CX), 12)      # cats beside them

    def test_people_do_their_things(self):
        random.seed(7)
        sc = manager(skip_intro=True, surprise_at=500.0).create("christmas")
        seen = set()
        for _ in range(int(240 * 30)):
            sc.update(1 / 30.0)
            for p in people(sc):
                seen.add(p.state)
        self.assertTrue({"peace", "stroll", "pair"} <= seen, seen)

    def test_only_people_and_limits(self):
        m = manager()
        m.only_people = [1]
        sc = m.create("osaka")
        self.assertEqual([p.skin.name for p in people(sc)], ["girlfriend"])
        m.only_people = []
        self.assertEqual(people(m.create("osaka")), [])
        cfg, _d = catlib.read_config(CATS)
        cfg["people"] = cfg["people"] * 2
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cats.json")
            cfg["skins_dir"] = SKINS
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with self.assertRaises(catlib.ConfigError):        # at most 2 people
                SceneManager("scenes", {}, {}, {"cats": path}).create("christmas")

    def test_menu_ticks_people(self):
        m = manager()
        mn = Menu(m, CATS, "christmas", "x")
        self.assertEqual(mn.people_checked, {0, 1})
        mn.cursor = [i for i, it in enumerate(mn.items) if it[0] == "person"][0]
        mn.handle(" ")                                        # untick "me"
        result = mn.handle("\r")
        self.assertEqual(result[0], "start")
        self.assertEqual(result[3], [1])
        cv = Canvas()
        mn.draw(cv, 1.0)
        text = "\n".join(cv.plain_rows())
        self.assertIn("人物", text)
        self.assertIn("(o)-(o)", text)                        # preview of the person


if __name__ == "__main__":
    unittest.main()
