# -*- coding: utf-8 -*-
"""The start menu (scene radio list + cat checkboxes) and cat selection."""
import os
import random
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import cats as catlib            # noqa: E402
from engine.manager import SceneManager      # noqa: E402
from engine.menu import Menu                 # noqa: E402
from engine.render import Canvas, text_width  # noqa: E402

CATS = os.path.join(ROOT, "cats.json")


def only_cats(scene):
    """The scene's cats, without the people walking with them."""
    return [c for c in scene.cats if not getattr(c, "is_person", False)]


def menu(**kw):
    m = SceneManager("scenes", {}, {}, {"cats": CATS})
    return m, Menu(m, CATS, kw.pop("scene", "christmas"), "工程師的浪漫", **kw)


class MenuTests(unittest.TestCase):
    def test_defaults_follow_cats_json(self):
        _m, mn = menu()
        cfg, _d = catlib.read_config(CATS)
        enabled = [i for i, c in enumerate(cfg["cats"]) if c.get("enabled", True)]
        self.assertEqual(mn.selection(), ("christmas", enabled))

    def test_pick_scene_and_tick_cats(self):
        m, mn = menu()
        osaka = m.names().index("osaka")
        for _ in range(osaka):
            mn.handle("down")
        mn.handle(" ")                                  # choose Osaka
        self.assertEqual(mn.scene, "osaka")
        first_cat = len(m.names())
        while mn.cursor != first_cat:
            mn.handle("down")
        mn.handle(" ")                                  # untick cat 0
        mn.handle("down")
        mn.handle("down")
        mn.handle(" ")                                  # tick cat 2
        result = mn.handle("\r")
        self.assertEqual(result[0], "start")
        self.assertEqual(result[1], "osaka")
        self.assertNotIn(0, result[2])
        self.assertIn(2, result[2])

    def test_cannot_start_without_cats(self):
        _m, mn = menu()
        mn.handle("a")                                  # ticks cleared
        self.assertEqual(mn.checked, set())
        self.assertIsNone(mn.handle("\r"))
        self.assertGreater(mn.warn, 0)
        mn.handle("a")                                  # the first 3 ticked
        self.assertEqual(mn.checked, {0, 1, 2})
        self.assertEqual(mn.handle("\r")[0], "start")

    def test_at_most_three_cats(self):
        m, mn = menu()
        self.assertEqual(catlib.MAX_CATS, 3)
        mn.handle("a")
        mn.handle("a")                                  # 0, 1, 2 ticked
        mn.cursor = len(m.names()) + 3                  # on the 4th cat
        mn.handle(" ")
        self.assertEqual(mn.checked, {0, 1, 2})         # refused
        self.assertIn("3", mn.warn_text)
        mn.cursor = len(m.names()) + 1
        mn.handle(" ")                                  # untick one ...
        mn.cursor = len(m.names()) + 3
        mn.handle(" ")                                  # ... then the 4th fits
        self.assertEqual(mn.checked, {0, 2, 3})
        _m, mn = menu(only=[0, 1, 2, 3, 4])             # too many passed in: clipped
        self.assertEqual(len(mn.checked), 3)

    def test_quit_and_wraparound(self):
        _m, mn = menu()
        mn.handle("up")
        self.assertEqual(mn.items[mn.cursor][0], "start")   # wraps to the bottom
        self.assertEqual(mn.handle("q"), ("quit",))

    def test_draw_fits_and_shows_everything(self):
        m, mn = menu()
        cv = Canvas()
        mn.draw(cv, 1.0)
        rows = cv.plain_rows()
        self.assertTrue(all(text_width(r) <= cv.w for r in rows))
        text = "\n".join(rows)
        for n in m.names():
            self.assertIn(n, text)
        for c in mn.cats:
            self.assertIn(c["name"], text)

    def test_preview_wears_the_chosen_scenes_accessory(self):
        m, mn = menu()
        cv = Canvas()
        mn.draw(cv, 1.0)
        self.assertIn("/#\\.@", "\n".join(cv.plain_rows()))     # Santa hat
        mn.scene = "demo"
        mn.draw(cv, 1.0)
        self.assertIn(">o<", "\n".join(cv.plain_rows()))        # bow


class CatSelectionTests(unittest.TestCase):
    def test_only_cats_overrides_enabled(self):
        m = SceneManager("scenes", {}, {}, {"cats": CATS})
        cfg, _d = catlib.read_config(CATS)
        last3 = list(range(len(cfg["cats"])))[-3:]
        m.only_cats = last3                                  # even disabled ones
        random.seed(1)
        sc = m.create("christmas")
        self.assertEqual([c.name for c in only_cats(sc)], [cfg["cats"][i]["name"] for i in last3])
        m.only_cats = [last3[-1]]
        self.assertEqual(len(only_cats(m.create("tokyo"))), 1)
        m.only_cats = [0, 1, 2, 3]
        with self.assertRaises(catlib.ConfigError):          # 4 is too many
            m.create("christmas")

    def test_select_by_name(self):
        cfg, _d = catlib.read_config(CATS)
        names = [c["name"] for c in cfg["cats"]]
        self.assertEqual(catlib.select_cats(CATS, [names[2], names[0]]), [2, 0])
        with self.assertRaises(catlib.ConfigError):
            catlib.select_cats(CATS, ["no-such-cat"])

    def test_with_option_on_the_command_line(self):
        cfg, _d = catlib.read_config(CATS)
        names = [c["name"] for c in cfg["cats"]]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, "main.py", "--with", ",".join(names[:3]),
                            "--snapshot", "1", "--skip-intro"],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = subprocess.run([sys.executable, "main.py", "--with", ",".join(names[:4]),
                            "--snapshot", "1"],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertIn("at most 3", p.stdout)
        p = subprocess.run([sys.executable, "main.py", "--with", ",".join(names[:2]),
                            "--snapshot", "1", "--skip-intro"],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = subprocess.run([sys.executable, "main.py", "--with", "nobody", "--snapshot", "1"],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertIn("no cat called", p.stdout)


class MenuLoopTests(unittest.TestCase):
    """terminal.run_menu with scripted keys instead of a real keyboard."""

    def run_keys(self, keys):
        import io
        from engine import terminal

        class FakeKeys:
            def __init__(self):
                self.q = list(keys)

            def poll(self):
                return self.q.pop(0) if self.q else "q"

            def close(self):
                pass

        old_keys, old_out = terminal.Keys, sys.stdout
        terminal.Keys, sys.stdout = FakeKeys, io.StringIO()
        try:
            _m, mn = menu()
            return terminal.run_menu(mn), sys.stdout.getvalue()
        finally:
            terminal.Keys, sys.stdout = old_keys, old_out

    def test_enter_starts_with_the_selection(self):
        picked, out = self.run_keys(["down", " ", chr(13)])
        self.assertEqual(picked[0], _second_scene())
        self.assertIn(chr(27) + "]0;", out)                # window title set

    def test_quit_restores_the_screen(self):
        picked, out = self.run_keys(["q"])
        self.assertIsNone(picked)
        self.assertTrue(out.endswith(chr(27) + "[?1049l"))


def _second_scene():
    return SceneManager("scenes", {}, {}, {"cats": CATS}).names()[1]


class PosixKeyParsingTests(unittest.TestCase):
    """Mac / Linux keys arrive as raw bytes; arrows are ESC [ A..D."""

    class Src:
        def __init__(self, data, later=b""):
            self.buf, self.later = data, later

        def more(self, wait=0.03):
            if self.later:
                self.buf += self.later
                self.later = b""
                return True
            return False

    def keys(self, data, later=b""):
        from engine.terminal import parse_key
        src = self.Src(data, later)
        out = []
        while src.buf or src.later:
            out.append(parse_key(src))
        return out

    def test_arrows_are_not_escape(self):
        self.assertEqual(self.keys(b"\x1b[B"), ["down"])
        self.assertEqual(self.keys(b"\x1b[A\x1b[B\x1b[C\x1b[D"), ["up", "down", "right", "left"])
        self.assertEqual(self.keys(b"\x1bOA"), ["up"])

    def test_arrow_split_across_reads(self):
        self.assertEqual(self.keys(b"\x1b", b"[B"), ["down"])

    def test_plain_keys_and_esc(self):
        self.assertEqual(self.keys(b" \nQ"), [" ", "\n", "q"])
        self.assertEqual(self.keys(b"\x1b"), ["\x1b"])
        self.assertEqual(self.keys("摸".encode("utf-8")), ["摸"])


if __name__ == "__main__":
    unittest.main()
