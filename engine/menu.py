# -*- coding: utf-8 -*-
"""
menu.py - the start menu: pick one scene and tick the cats / people to show
===========================================================================

    python main.py --menu

    Up / Down   move            Space   choose a scene / tick a cat
    Enter       start           a       clear the ticks (again: first 3)
    q / Esc     quit

The right-hand panel shows the cat under the cursor wearing the chosen
scene's accessory. Menu state and drawing are separate from the key loop
(Menu.handle / Menu.draw), so they can be tested without a terminal; the
key / screen loop is terminal.run_menu().
"""
from . import cats as catlib
from .render import CH, CW, S, text_width

PERSONALITY = {"calm": "穩重", "playful": "調皮", "person": "人物"}
HELP = "上下鍵 移動   空白鍵 選擇/勾選   Enter 開始   a 清除勾選   q 離開"


class Menu:
    def __init__(self, manager, cats_path, scene=None, title="", only=None,
                 only_people=None):
        self.m = manager
        self.title = title
        self.scenes = manager.names()
        self.scene = scene if scene in self.scenes else self.scenes[0]
        cfg, skins_dir = catlib.read_config(cats_path)
        self.cats = []
        for i, c in enumerate(cfg["cats"]):
            try:
                skin = catlib.load_skin(c["skin"], skins_dir)
            except (catlib.SkinError, KeyError):
                skin = None
            self.cats.append({"name": c.get("name", c.get("skin", "?")),
                              "skin": skin, "skin_name": c.get("skin", "?"),
                              "personality": c.get("personality", "calm")})
        if only is not None:
            self.checked = set(list(only)[:catlib.MAX_CATS])
        else:
            on = [i for i, c in enumerate(cfg["cats"]) if c.get("enabled", True)]
            self.checked = set(on[:catlib.MAX_CATS])
        self.people = []
        people = catlib.people_entries(cfg, cats_path)
        for p in people:
            try:
                skin = catlib.load_skin(p["skin"], skins_dir)
            except (catlib.SkinError, KeyError):
                skin = None
            self.people.append({"name": p.get("name", p.get("skin", "?")), "skin": skin,
                                "skin_name": p.get("skin", "?"), "personality": "person"})
        if only_people is not None:
            self.people_checked = set(list(only_people)[:catlib.MAX_PEOPLE])
        else:
            on = [i for i, p in enumerate(people) if p.get("enabled", True)]
            self.people_checked = set(on[:catlib.MAX_PEOPLE])
        self.items = ([("scene", n) for n in self.scenes] +
                      [("cat", i) for i in range(len(self.cats))] +
                      [("person", i) for i in range(len(self.people))] + [("start", None)])
        self.cursor = self.scenes.index(self.scene)
        self.warn = 0.0
        self.warn_text = ""

    # ---------------- state ----------------
    def selection(self):
        return self.scene, sorted(self.checked)

    def handle(self, k):
        """Returns ('start', scene, [cat positions], [person positions]),
        ('quit',) or None."""
        kind, val = self.items[self.cursor]
        if k in ("up", "w", "k"):
            self.cursor = (self.cursor - 1) % len(self.items)
        elif k in ("down", "s", "j", "\t"):
            self.cursor = (self.cursor + 1) % len(self.items)
        elif k == " ":
            if kind == "scene":
                self.scene = val
            elif kind == "cat":
                if val in self.checked:
                    self.checked.discard(val)
                elif len(self.checked) >= catlib.MAX_CATS:
                    self.say("最多只能選 %d 隻貓咪" % catlib.MAX_CATS)
                else:
                    self.checked.add(val)
            elif kind == "person":
                if val in self.people_checked:
                    self.people_checked.discard(val)
                elif len(self.people_checked) >= catlib.MAX_PEOPLE:
                    self.say("最多只能選 %d 個人" % catlib.MAX_PEOPLE)
                else:
                    self.people_checked.add(val)
            else:
                return self.start()
        elif k in ("\r", "\n"):
            if kind == "scene":
                self.scene = val
            return self.start()
        elif k == "a":
            # clear the ticks; pressed again, tick the first MAX_CATS cats
            self.checked = set() if self.checked else set(range(len(self.cats))[:catlib.MAX_CATS])
        elif k in ("q", "\x1b", "\x03"):
            return ("quit",)
        return None

    def say(self, text):
        self.warn, self.warn_text = 2.5, text

    def start(self):
        if not self.checked:
            self.say("請至少勾選一隻貓咪")
            return None
        return ("start",) + self.selection() + (sorted(self.people_checked),)

    # ---------------- drawing ----------------
    def draw(self, cv, t, dt=0.0):
        cv.clear()
        self.warn = max(0.0, self.warn - dt)
        dim, norm, hi = S(244), S(252), S(231, 1)
        head, pink = S(222, 1), S(211, 1)

        def text(x, y, s, st):
            return cv.put_text(x, y, s, lambda i, c: st)

        title = "♥  %s  ♥" % self.title if self.title else "♥"
        text((CW - text_width(title)) // 2, 1, title, pink)
        sub = "選一個場景，再勾選要一起出場的貓咪和人物"
        text((CW - text_width(sub)) // 2, 2, sub, dim)

        y = 4
        text(2, y, "場景", head)
        for i, (kind, val) in enumerate(self.items):
            if kind == "scene":
                y += 1
                row = y
                cls = self.m.get(val)
                on = val == self.scene
                text(4, row, "(*)" if on else "( )", S(213, 1) if on else dim)
                text(8, row, cls.label or cls.title, hi if on else norm)
                text(28, row, val, dim)
            elif kind == "cat":
                if val == 0:
                    y += 2
                    text(2, y, "貓咪（最多 %d 隻）  已選 %d 隻" % (catlib.MAX_CATS, len(self.checked)),
                         head)
                y += 1
                row = y
                c = self.cats[val]
                on = val in self.checked
                text(4, row, "[x]" if on else "[ ]", S(46, 1) if on else dim)
                text(8, row, c["name"], hi if on else norm)
                text(18, row, c["skin_name"], dim)
                text(28, row, PERSONALITY.get(c["personality"], c["personality"]), dim)
            elif kind == "person":
                if val == 0:
                    y += 2
                    text(2, y, "人物（最多 %d 位）" % catlib.MAX_PEOPLE, head)
                y += 1
                row = y
                p = self.people[val]
                on = val in self.people_checked
                text(4, row, "[x]" if on else "[ ]", S(46, 1) if on else dim)
                text(8, row, p["name"], hi if on else norm)
                text(18, row, p["skin_name"], dim)
            else:
                y += 2
                row = y
                sel = self.cursor == i
                label = "[  開始播放  ]"
                text(4, row, label, S(226, 1) if sel else norm)
                if self.warn > 0:
                    text(22, row, self.warn_text, S(203, 1))
            if i == self.cursor:
                text(2, row, ">", S(226, 1))
        self.draw_preview(cv, t)
        text((CW - text_width(HELP)) // 2, CH - 2, HELP, dim)

    def preview_cat(self):
        kind, val = self.items[self.cursor]
        if kind == "cat":
            return self.cats[val]
        if kind == "person":
            return self.people[val]
        for i in sorted(self.checked):
            return self.cats[i]
        return self.cats[0] if self.cats else None

    def draw_preview(self, cv, t):
        x0, y0, x1, y1 = 44, 4, CW - 2, 18
        frame = S(238)
        for x in range(x0, x1 + 1):
            cv.put(x, y0, "-", frame)
            cv.put(x, y1, "-", frame)
        for y in range(y0, y1 + 1):
            cv.put(x0, y, "|", frame)
            cv.put(x1, y, "|", frame)
        cls = self.m.get(self.scene)
        name = cls.label or cls.title
        cv.put_text(x0 + 2, y0 + 1, name, lambda i, c: S(222, 1))
        c = self.preview_cat()
        tall = c is not None and c["skin"] is not None and c["skin"].height > 6
        sub = cls.title if cls.label else ""
        if text_width(sub) > x1 - x0 - 3:
            sub = sub[:x1 - x0 - 6] + "..."
        if not tall:                               # a person needs that row
            cv.put_text(x0 + 2, y0 + 2, sub, lambda i, c: S(244))
        if c is None or c["skin"] is None:
            return
        skin = c["skin"]
        eyes = "closed" if (t % 4.0) > 3.85 else "normal"
        cells = skin.cells("sit", 0, int(t * 2.5), skin.eye_pair(eyes), 1, cls.CAT_ACCESSORY)
        left = (x0 + x1 - skin.width) // 2
        top, who_y = y0 + 5, y1 - 2
        if tall:                                   # a person: taller than a cat
            top, who_y = y0 + 2, y1 - 1
        for (x, y, ch, st) in cells:
            cv.put(left + x, top + y, ch, st, ch == " ")
        who = "%s  (%s)" % (c["name"], PERSONALITY.get(c["personality"], ""))
        cv.put_text((x0 + x1 - text_width(who)) // 2, who_y, who, lambda i, ch: S(231, 1))

