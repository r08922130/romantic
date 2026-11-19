# -*- coding: utf-8 -*-
"""
settings.py - settings.json + command line -> one settings object per scene
===========================================================================

Precedence (later wins):

    DEFAULTS below
    < the scene's own SETTINGS        (e.g. its greeting, its timing)
    < settings.json top level         (applies to every scene)
    < settings.json "scenes": {"<name>": {...}}   (only that scene)
    < command-line options
"""
import os
from types import SimpleNamespace

from .cats import ConfigError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "scene": "christmas",
    "greeting": "",
    "wish": "",
    "heart": "♥",
    "surprise_at": 70.0,
    "every": 75.0,
    "hold": 30.0,
    "stay": False,
    "skip_intro": False,
    "fps": 30,
    "cats": "cats.json",
}

_TYPE_NAMES = {"str": "text", "float": "number", "int": "whole number", "bool": "true or false"}


def _check(where, data, allow_scene):
    out = {}
    for k, v in data.items():
        if k.startswith("_"):            # "_comment" etc.
            continue
        if k not in DEFAULTS or (k == "scene" and not allow_scene):
            known = [n for n in DEFAULTS if allow_scene or n != "scene"]
            raise ConfigError("%s: unknown setting \"%s\" (known: %s)"
                              % (where, k, ", ".join(known)))
        want = type(DEFAULTS[k])
        if want is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, want) or (want is not bool and isinstance(v, bool)):
            raise ConfigError("%s: \"%s\" should be a %s" % (where, k, _TYPE_NAMES[want.__name__]))
        out[k] = v
    return out


def load_file(path, required):
    """Read settings.json -> (top_level, {scene_name: overrides})."""
    import json
    if not os.path.isfile(path):
        if required:
            raise ConfigError("settings file not found: %s" % path)
        return {}, {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        raise ConfigError("%s is not valid JSON: %s" % (path, e))
    if not isinstance(data, dict):
        raise ConfigError("%s must contain a JSON object { ... }" % path)
    scenes_raw = data.pop("scenes", {})
    if not isinstance(scenes_raw, dict):
        raise ConfigError("%s: \"scenes\" must be an object like {\"christmas\": {...}}" % path)
    top = _check(path, data, allow_scene=True)
    per_scene = {}
    for name, block in scenes_raw.items():
        if name.startswith("_"):
            continue
        if not isinstance(block, dict):
            raise ConfigError("%s: scenes.%s must be an object { ... }" % (path, name))
        per_scene[name.lower()] = _check("%s (scenes.%s)" % (path, name), block, allow_scene=False)
    base = os.path.dirname(os.path.abspath(path))
    for d in [top] + list(per_scene.values()):
        if "cats" in d and not os.path.isabs(d["cats"]):
            d["cats"] = os.path.join(base, d["cats"])
    return top, per_scene


def resolve(scene_cls, top, per_scene, cli, ascii_heart=False):
    """Final settings for one scene, as an object (cfg.greeting, cfg.hold ...)."""
    merged = dict(DEFAULTS)
    merged["cats"] = os.path.join(ROOT, DEFAULTS["cats"])
    merged.update(scene_cls.SETTINGS)
    merged.update(top)
    merged.update(per_scene.get(scene_cls.name, {}))
    merged.update({k: v for k, v in cli.items() if v is not None})
    if not os.path.isabs(merged["cats"]):
        merged["cats"] = os.path.join(ROOT, merged["cats"])
    merged["scene"] = scene_cls.name
    if ascii_heart:
        merged["heart"] = "<3"
    return SimpleNamespace(**merged)
