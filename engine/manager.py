# -*- coding: utf-8 -*-
"""
manager.py - SceneManager: find, choose and switch scenes
=========================================================

Every module in the `scenes` package is imported and every BaseScene
subclass with a `name` is registered automatically. Adding a scene therefore
means adding ONE file to scenes/ - nothing else has to be edited.
"""
import importlib
import pkgutil

from . import settings as settings_mod
from .cats import ConfigError
from .scene import BaseScene


class SceneManager:
    def __init__(self, package="scenes", top=None, per_scene=None, cli=None,
                 ascii_heart=False):
        self.registry = {}         # name -> scene class
        self.broken = {}           # module name -> error (shown if requested)
        self.top = top or {}
        self.per_scene = per_scene or {}
        self.cli = cli or {}
        self.ascii_heart = ascii_heart
        self.only_cats = None      # positions in cats.json chosen in the menu / --with
        self.discover(package)

    # ---------- registration ----------
    def register(self, cls):
        if not cls.name:
            raise ValueError("%s has no `name`" % cls.__name__)
        self.registry[cls.name.lower()] = cls
        return cls

    def discover(self, package):
        pkg = importlib.import_module(package)
        for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda i: i.name):
            if info.name.startswith("_"):
                continue
            try:
                mod = importlib.import_module("%s.%s" % (package, info.name))
            except Exception as e:          # one broken scene must not break the rest
                self.broken[info.name] = e
                continue
            for obj in vars(mod).values():
                if (isinstance(obj, type) and issubclass(obj, BaseScene)
                        and obj is not BaseScene and obj.__module__ == mod.__name__
                        and obj.name):
                    self.register(obj)

    # ---------- choosing ----------
    def names(self):
        return sorted(self.registry, key=lambda n: (self.registry[n].order, n))

    def get(self, name):
        key = (name or "").lower()
        if key in self.registry:
            return self.registry[key]
        if key in self.broken:
            raise ConfigError("scene '%s' failed to load: %s" % (name, self.broken[key]))
        raise ConfigError("unknown scene '%s' (available: %s)" % (name, ", ".join(self.names())))

    def check_settings(self):
        for name in self.per_scene:
            if name not in self.registry and name not in self.broken:
                raise ConfigError("settings.json \"scenes\" has unknown scene '%s' "
                                  "(available: %s)" % (name, ", ".join(self.names())))

    def settings_for(self, name):
        cfg = settings_mod.resolve(self.get(name), self.top, self.per_scene,
                                   self.cli, self.ascii_heart)
        cfg.only_cats = self.only_cats
        return cfg

    def create(self, name):
        cls = self.get(name)
        return cls(self.settings_for(name))

    # ---------- switching ----------
    def next_name(self, current):
        names = self.names()
        if current not in names:
            return names[0]
        return names[(names.index(current) + 1) % len(names)]
