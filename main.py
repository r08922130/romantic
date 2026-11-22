#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - 工程師的浪漫 (An Engineer's Romance)
=============================================
Terminal ASCII love-letter animations, one scene at a time.
Python 3, standard library only. Windows Terminal / PowerShell, macOS, Linux.

    python main.py                      # the default scene (christmas)
    python main.py --scene christmas
    python main.py --list-scenes

    python main.py --menu               # pick the scene + tick the cats
    python main.py --with 摸摸,逗逗      # only these cats

Keys:  q / Esc / Ctrl+C = quit    s = surprise now    n = next scene

Layout
------
  engine/   shared: render (Canvas), effects (Fx, Starfield, Banner),
            cats (skins, accessories, personalities), scene (BaseScene),
            manager (SceneManager), settings, terminal (the one main loop)
  scenes/   one file per scene - christmas.py, demo.py, ...
  skins/    what each cat looks like (*.cat files)
  cats.json which cats appear;  settings.json greeting & timing per scene
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import cats as catlib            # noqa: E402
from engine import settings as settings_mod  # noqa: E402
from engine import terminal                  # noqa: E402
from engine.manager import SceneManager      # noqa: E402

PROJECT_NAME = "工程師的浪漫"     # 工程師的浪漫


def build_parser():
    ap = argparse.ArgumentParser(
        description=PROJECT_NAME + " - terminal ASCII animation for someone you love. "
                    "Defaults come from settings.json; options given here win.")
    ap.add_argument("--menu", action="store_true",
                    help="start with a menu: pick the scene and tick the cats")
    ap.add_argument("--scene", help="which scene to play (default: christmas)")
    ap.add_argument("--with", dest="with_cats", metavar="NAMES",
                    help="only these cats, comma separated (names from cats.json), "
                         "e.g. --with 摸摸,逗逗")
    ap.add_argument("--list-scenes", dest="list_scenes", action="store_true",
                    help="list the available scenes and exit")
    ap.add_argument("--settings", default=None,
                    help="settings file (default: settings.json next to this script)")
    ap.add_argument("--greeting", help="big greeting line")
    ap.add_argument("--wish", help="your own sweet words (second line)")
    ap.add_argument("--surprise-at", type=float, dest="surprise_at",
                    help="seconds until the first surprise")
    ap.add_argument("--every", type=float, help="seconds between surprises afterwards")
    ap.add_argument("--hold", type=float, help="seconds the greeting stays on screen")
    ap.add_argument("--stay", action="store_true", default=None,
                    help="keep the greeting on screen forever")
    ap.add_argument("--skip-intro", action="store_true", default=None, dest="skip_intro",
                    help="skip the opening sequence")
    ap.add_argument("--ascii", action="store_true", help="use <3 instead of the heart symbol")
    ap.add_argument("--fourier", dest="fourier", action="store_true", default=None,
                    help="open with Fourier epicycles drawing the outline (christmas)")
    ap.add_argument("--no-fourier", dest="fourier", action="store_false", default=None,
                    help="skip the Fourier epicycles opening")
    ap.add_argument("--fourier-terms", dest="fourier_terms", type=int, metavar="N",
                    help="Fourier terms (circles) for the opening, e.g. 20, 50, 100, 200")

    ap.add_argument("--fps", type=int)
    ap.add_argument("--cats", help="cat config file (default: cats.json)")
    ap.add_argument("--preview-skin", dest="preview_skin", metavar="NAME_OR_FILE",
                    help="print every pose of one skin and exit (for drawing new cats)")
    ap.add_argument("--preview-cats", dest="preview_cats", action="store_true",
                    help="print the skins of every cat in the config and exit")
    ap.add_argument("--snapshot", type=float, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--seed", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--size", default=None, help=argparse.SUPPRESS)   # snapshot: COLSxLINES
    return ap


def make_manager(args):
    top, per_scene = settings_mod.load_file(
        args.settings or os.path.join(HERE, "settings.json"),
        required=args.settings is not None)
    cli = {k: getattr(args, k, None) for k in settings_mod.DEFAULTS if k != "scene"}
    if cli.get("cats"):
        cli["cats"] = os.path.abspath(cli["cats"])
    manager = SceneManager("scenes", top, per_scene, cli, ascii_heart=args.ascii)
    manager.check_settings()
    name = args.scene or top.get("scene") or settings_mod.DEFAULTS["scene"]
    manager.get(name)          # unknown scene -> friendly error now
    return manager, name


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        manager, name = make_manager(args)
        if args.list_scenes:
            for n in manager.names():
                cls = manager.get(n)
                print("%-12s %s%s" % (n, cls.title, "   (default)" if n == name else ""))
            return
        cfg = manager.settings_for(name)
        if args.with_cats:
            manager.only_cats = catlib.select_cats(
                cfg.cats, [n for n in args.with_cats.split(",") if n.strip()])
        if args.preview_skin or args.preview_cats:
            terminal.enable_vt()
            acc = manager.get(name).CAT_ACCESSORY
            if args.preview_skin:
                _c, skins_dir = catlib.read_config(cfg.cats)
                skins = [catlib.load_skin(args.preview_skin, skins_dir)]
            else:
                skins = catlib.config_skins(cfg.cats)
            color = sys.stdout.isatty()
            for skin in skins:
                print("\n".join(catlib.preview_skin(skin, color, acc)))
                print()
            return
        if args.snapshot is not None:
            size = None
            if args.size:
                size = tuple(int(v) for v in args.size.lower().split("x"))
            print("\n".join(terminal.snapshot(manager, name, args.snapshot, args.seed, size)))
            return

        if args.menu:
            from engine.menu import Menu
            picked = terminal.run_menu(Menu(manager, cfg.cats, name, PROJECT_NAME, manager.only_cats))
            if picked is None:
                return                                   # quit from the menu
            name, manager.only_cats = picked
            cfg = manager.settings_for(name)
        manager.create(name)     # build once up front so config errors show plainly
    except (catlib.ConfigError, catlib.SkinError) as e:
        if args.menu:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        print("Config problem:\n  %s" % e)
        sys.exit(1)
    terminal.run(manager, name, cfg.fps, title=PROJECT_NAME)


if __name__ == "__main__":
    main()
