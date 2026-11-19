# -*- coding: utf-8 -*-
"""
Automated checks for the scene architecture.

    python -m unittest discover -s tests -v
"""
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import cats as catlib            # noqa: E402
from engine import settings as settings_mod  # noqa: E402
from engine import terminal                  # noqa: E402
from engine.manager import SceneManager      # noqa: E402
from engine.render import Canvas, text_width  # noqa: E402
from engine.scene import BaseScene           # noqa: E402

import golden                                # noqa: E402

CATS = golden.CATS


def manager(**cli):
    cli.setdefault("cats", CATS)
    return SceneManager("scenes", {}, {}, cli)


def code_only(path):
    """Source text without comments and string literals (docstrings)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for tok in tokenize.generate_tokens(f.readline):
            if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                out.append(tok.string)
    return " ".join(out)


# ---------------------------------------------------------------------
class ChristmasRegression(unittest.TestCase):
    """The Christmas animation must not change (chars + colours, frame by frame)."""

    @classmethod
    def setUpClass(cls):
        with open(golden.OUT, encoding="utf-8") as f:
            cls.gold = json.load(f)

    def check(self, key, skip):
        now = golden.capture(skip_intro=skip)
        for t, want in self.gold[key].items():
            got = now[t]
            self.assertEqual(got["chars"], want["chars"], "characters differ at t=%ss" % t)
            self.assertEqual(got["styles_sha256"], want["styles_sha256"],
                             "colours differ at t=%ss" % t)

    def test_full_story_unchanged(self):
        self.check("normal", False)

    def test_skip_intro_unchanged(self):
        self.check("skip_intro", True)

    def test_story_beats(self):
        """Tree, star, presents, both cats and the greeting all show up."""
        g = self.gold["normal"]
        early, tree, full, surprise = (g["1"]["chars"], g["14"]["chars"],
                                       g["30"]["chars"], g["85"]["chars"])
        self.assertNotIn("\\|/", "".join(early))                 # no star yet
        self.assertIn("\\|/", "".join(tree))                     # star on top
        self.assertIn("[==#==]", "".join(full))                  # presents
        self.assertIn("/#\\.@", "".join(full))                   # Santa hats
        self.assertIn("Christmas, My Love!", surprise[0])  # greeting (snow may sit in a gap)
        self.assertIn("feels like Christmas.", surprise[1])


# ---------------------------------------------------------------------
class SceneManagerTests(unittest.TestCase):
    def test_discovers_scenes(self):
        m = manager()
        self.assertIn("christmas", m.names())
        self.assertIn("demo", m.names())

    def test_default_scene_is_christmas(self):
        self.assertEqual(settings_mod.DEFAULTS["scene"], "christmas")

    def test_unknown_scene_is_a_friendly_error(self):
        with self.assertRaises(catlib.ConfigError) as cm:
            manager().get("wedding")
        self.assertIn("available", str(cm.exception))

    def test_next_scene_cycles(self):
        m = manager()
        seen = set()
        name = "christmas"
        for _ in range(len(m.names())):
            name = m.next_name(name)
            seen.add(name)
        self.assertEqual(seen, set(m.names()))

    def test_every_scene_runs_and_fits_the_canvas(self):
        m = manager()
        for name in m.names():
            with self.subTest(scene=name):
                random.seed(1)
                sc = m.create(name)
                cv = Canvas(sc.CW, sc.CH)
                for _ in range(int(150 * 30)):        # 150 s: intro, play, surprise
                    sc.update(1 / 30.0)
                sc.draw(cv)
                rows = cv.plain_rows()
                self.assertEqual(len(rows), sc.CH)
                self.assertTrue(all(text_width(r) <= sc.CW for r in rows))
                self.assertTrue(all(c.visible for c in sc.cats))

    def test_surprise_reaches_hold(self):
        m = manager()
        for name in m.names():
            with self.subTest(scene=name):
                random.seed(2)
                sc = m.create(name)
                for _ in range(int((sc.INTRO_END + 40) * 30)):
                    sc.update(1 / 30.0)
                sc.trigger_surprise()
                for _ in range(30 * 30):
                    sc.update(1 / 30.0)
                    if sc.phase == "hold":
                        break
                self.assertEqual(sc.phase, "hold")

    def test_new_scene_needs_only_a_new_file(self):
        """Drop a module into a scenes package -> it is registered. No other edits."""
        tmp = tempfile.mkdtemp()
        try:
            pkg = os.path.join(tmp, "extra_scenes")
            os.mkdir(pkg)
            open(os.path.join(pkg, "__init__.py"), "w").close()
            with open(os.path.join(pkg, "sunset.py"), "w", encoding="utf-8") as f:
                f.write("from engine.scene import BaseScene\n"
                        "class SunsetScene(BaseScene):\n"
                        "    name = 'sunset'\n"
                        "    SETTINGS = {'greeting': 'Sunset!'}\n")
            with open(os.path.join(pkg, "broken.py"), "w", encoding="utf-8") as f:
                f.write("this is not python\n")
            sys.path.insert(0, tmp)
            m = SceneManager("extra_scenes", {}, {}, {"cats": CATS})
            self.assertEqual(m.names(), ["sunset"])     # broken one skipped, not fatal
            sc = m.create("sunset")
            self.assertEqual(sc.cfg.greeting, "Sunset!")
            with self.assertRaises(catlib.ConfigError):
                m.get("broken")
        finally:
            sys.path.remove(tmp)
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------
class IsolationTests(unittest.TestCase):
    """The shared engine knows nothing about any holiday; scenes don't depend
    on each other."""
    HOLIDAY = re.compile(r"(?i)tree|gift|snow|present|santa|christmas|wedding|qixi|valentine")

    def test_engine_has_no_holiday_logic(self):
        for fn in os.listdir(os.path.join(ROOT, "engine")):
            if fn.endswith(".py"):
                with self.subTest(file=fn):
                    code = code_only(os.path.join(ROOT, "engine", fn))
                    self.assertIsNone(self.HOLIDAY.search(code), "holiday logic in engine/%s" % fn)

    def test_engine_does_not_import_scenes(self):
        for fn in os.listdir(os.path.join(ROOT, "engine")):
            if fn.endswith(".py"):
                code = code_only(os.path.join(ROOT, "engine", fn))
                self.assertNotRegex(code, r"\bimport scenes\b|\bfrom scenes\b")

    def test_scenes_do_not_import_each_other(self):
        for fn in os.listdir(os.path.join(ROOT, "scenes")):
            if fn.endswith(".py") and not fn.startswith("_"):
                with self.subTest(file=fn):
                    code = code_only(os.path.join(ROOT, "scenes", fn))
                    self.assertNotRegex(code, r"\bscenes\b")

    def test_one_main_loop(self):
        """Only engine/terminal.py writes frames to the terminal."""
        for d in ("scenes", "engine"):
            for fn in os.listdir(os.path.join(ROOT, d)):
                if fn.endswith(".py") and fn != "terminal.py":
                    code = code_only(os.path.join(ROOT, d, fn))
                    self.assertNotIn("stdout", code, "%s/%s writes to the terminal" % (d, fn))
                    self.assertNotIn("sleep", code, "%s/%s has its own loop timing" % (d, fn))


# ---------------------------------------------------------------------
class CatTests(unittest.TestCase):
    def skins(self):
        d = os.path.join(ROOT, "skins")
        return [catlib.load_skin(f[:-4], d) for f in sorted(os.listdir(d)) if f.endswith(".cat")]

    def test_all_skins_load_and_stay_in_their_box(self):
        for skin in self.skins():
            with self.subTest(skin=skin.name):
                lines = catlib.preview_skin(skin, color=False)
                self.assertFalse([ln for ln in lines if "WARNING" in ln])

    def test_accessory_is_per_scene(self):
        m = manager()
        hats = {}
        for name in m.names():
            sc = m.create(name)
            acc = sc.CAT_ACCESSORY
            hats[name] = acc.name if acc else None
            for c in sc.cats:
                self.assertIs(c.accessory, acc)
        self.assertEqual(hats["christmas"], "santa_hat")
        self.assertNotEqual(hats["demo"], "santa_hat")

    def test_skin_without_anchor_wears_nothing(self):
        skin = catlib.load_skin("tabby", os.path.join(ROOT, "skins"))
        acc = catlib.Accessory("x", [(0, 0, "{Z}XYZ")], {"Z": 1})
        plain = skin.cells("sit", 0, 0, ("o", "o"), 1)
        worn = skin.cells("sit", 0, 0, ("o", "o"), 1, acc)
        self.assertEqual(len(worn), len(plain) + 3)
        skin.anchors.clear()
        skin._cache.clear()
        self.assertEqual(skin.cells("sit", 0, 0, ("o", "o"), 1, acc), plain)

    def test_two_personalities_kept(self):
        random.seed(3)
        sc = manager().create("christmas")
        kinds = sorted(type(c).__name__ for c in sc.cats)
        self.assertEqual(kinds, ["CalmCat", "PlayfulCat"])
        calm = [c for c in sc.cats if isinstance(c, catlib.CalmCat)][0]
        playful = [c for c in sc.cats if isinstance(c, catlib.PlayfulCat)][0]
        self.assertGreater(playful.enter_speed(), calm.enter_speed())
        self.assertGreater(calm.W, playful.W)            # the calm one is the round one

    def test_playful_cat_uses_scene_hideouts(self):
        random.seed(4)
        demo = manager().create("demo")
        self.assertEqual(demo.hideouts(), [])
        cat = [c for c in demo.cats if isinstance(c, catlib.PlayfulCat)][0]
        cat.place(20, 25.5)
        cat.begin_peek()                                 # nothing to hide behind -> runs
        self.assertEqual(cat.state, "run")


# ---------------------------------------------------------------------
class SettingsTests(unittest.TestCase):
    def write(self, data):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.addCleanup(os.remove, path)
        return path

    def test_precedence(self):
        top, per = settings_mod.load_file(self.write({
            "hold": 5, "wish": "top wish",
            "scenes": {"christmas": {"hold": 9}}}), True)
        m = SceneManager("scenes", top, per, {"cats": CATS})
        xmas = m.settings_for("christmas")
        demo = m.settings_for("demo")
        self.assertEqual(xmas.hold, 9.0)                   # scenes.christmas beats top
        self.assertEqual(demo.hold, 5.0)                   # top beats scene default
        self.assertEqual(xmas.wish, "top wish")            # top beats scene default
        self.assertEqual(xmas.greeting, "Merry Christmas, My Love!")   # scene default
        m.cli["hold"] = 1.0
        self.assertEqual(m.settings_for("christmas").hold, 1.0)        # CLI wins

    def test_bad_settings_are_reported(self):
        for data, words in [({"holdd": 1}, "unknown setting"),
                            ({"hold": "long"}, "should be a number"),
                            ({"scenes": {"christmas": {"scene": "demo"}}}, "unknown setting"),
                            ({"scenes": []}, "must be an object")]:
            with self.subTest(data=data):
                with self.assertRaises(catlib.ConfigError) as cm:
                    settings_mod.load_file(self.write(data), True)
                self.assertIn(words, str(cm.exception))

    def test_unknown_scene_block(self):
        top, per = settings_mod.load_file(self.write({"scenes": {"weding": {}}}), True)
        with self.assertRaises(catlib.ConfigError):
            SceneManager("scenes", top, per, {"cats": CATS}).check_settings()

    def test_shipped_settings_file_is_valid(self):
        top, per = settings_mod.load_file(os.path.join(ROOT, "settings.json"), True)
        SceneManager("scenes", top, per, {}).check_settings()


# ---------------------------------------------------------------------
class CommandLineTests(unittest.TestCase):
    def run_py(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable] + list(args), cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout

    def test_default_equals_scene_christmas(self):
        common = ["--cats", CATS, "--snapshot", "40", "--seed", "7"]
        a = self.run_py("main.py", *common)
        b = self.run_py("main.py", "--scene", "christmas", *common)
        self.assertEqual(a[0], 0)
        self.assertEqual(a, b)
        self.assertIn("[==#==]", a[1])

    def test_list_and_errors(self):
        code, out = self.run_py("main.py", "--list-scenes")
        self.assertEqual(code, 0)
        self.assertIn("christmas", out)
        code, out = self.run_py("main.py", "--scene", "nope")
        self.assertEqual(code, 1)
        self.assertIn("unknown scene", out)

    def test_preview_uses_scene_accessory(self):
        _c, xmas = self.run_py("main.py", "--preview-skin", "tabby")
        _c, demo = self.run_py("main.py", "--scene", "demo", "--preview-skin", "tabby")
        self.assertIn("/#\\.@", xmas)
        self.assertIn(">o<", demo)
        self.assertNotIn("/#\\", demo)


if __name__ == "__main__":
    unittest.main()
