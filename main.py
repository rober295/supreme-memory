# -*- coding: utf-8 -*-
"""
God-level upgrade 2.1 — фітнес-RPG на Kivy (Windows / Android).
Уся логіка (плани, XP, серії, нагороди, тренер) живе в logic.py і покрита тестами.
Тут — лише інтерфейс. Дані зберігаються локально в user_data.json.
"""
import os
import threading
import time
import traceback
import webbrowser
from datetime import date, datetime, timedelta
from urllib.parse import quote

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, platform

import logic as L

BG = "#10101b"
PANEL = "#1c1b2b"
PANEL_HERO = "#241f3d"
PANEL_DONE = "#1b3327"
PURPLE = "#8b5cf6"
PINK = "#ec4899"
TEXT = "#f5f3ff"
MUTED = "#b8b4cc"
GREEN = "#22a35a"
GREEN_TEXT = "#4ade80"
RED = "#fb7185"
GOLD = "#fbbf24"
BLUE = "#4f6bd8"
GREY_BTN = "#39344f"
INPUT_BG = "#2a2840"

Window.clearcolor = get_color_from_hex(BG)
if platform in ("android", "ios"):
    Window.softinput_mode = "below_target"
else:
    Window.size = (420, 800)  # зручний розмір для перевірки на комп'ютері


def rgba(h):
    return get_color_from_hex(h)


class RButton(Button):
    """Кнопка із закругленими кутами та нормальним переносом тексту."""

    def __init__(self, bg=PURPLE, **kw):
        super().__init__(background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), halign="center", valign="middle", **kw)
        self._bg = rgba(bg)
        with self.canvas.before:
            self._color = Color(*self._bg)
            self._rect = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._sync, size=self._sync, state=self._recolor)
        self.bind(width=lambda i, w: setattr(i, "text_size", (max(w - dp(10), 10), None)))

    def set_bg(self, hex_color):
        self._bg = rgba(hex_color)
        self._recolor()

    def _sync(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size

    def _recolor(self, *_):
        r, g, b, a = self._bg
        self._color.rgba = (r * .75, g * .75, b * .75, a) if self.state == "down" else self._bg


class Card(BoxLayout):
    """Панель із закругленим фоном; висота підлаштовується під вміст."""

    def __init__(self, bg=PANEL, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", dp(12))
        kw.setdefault("spacing", dp(6))
        super().__init__(size_hint_y=None, **kw)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            self._c = Color(*rgba(bg))
            self._r = RoundedRectangle(radius=[dp(14)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._r.pos, self._r.size = self.pos, self.size


def level_color(v):
    """0..100 -> колір від темно-фіолетового до золотого."""
    a, b = (0.23, 0.16, 0.42), (0.98, 0.75, 0.14)
    t = max(0, min(100, v)) / 100.0
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3)) + (1,)


# (група, форма, x, y зверху, ширина, висота) у координатах фігури 100x200
BODY_FRONT = [
    (None, "e", 40, 0, 20, 22),
    ("Груди і плечі", "e", 20, 26, 22, 16), ("Груди і плечі", "e", 58, 26, 22, 16),
    ("Груди і плечі", "r", 32, 32, 36, 26),
    ("Руки", "r", 10, 42, 13, 50), ("Руки", "r", 77, 42, 13, 50),
    ("Корпус", "r", 34, 60, 32, 42),
    ("Ноги", "r", 32, 106, 16, 84), ("Ноги", "r", 52, 106, 16, 84),
]
BODY_BACK = [
    (None, "e", 40, 0, 20, 22),
    ("Спина", "r", 28, 28, 44, 56),
    ("Руки", "r", 10, 42, 13, 50), ("Руки", "r", 77, 42, 13, 50),
    ("Сідниці", "e", 30, 84, 40, 28),
    ("Ноги", "r", 32, 112, 16, 78), ("Ноги", "r", 52, 112, 16, 78),
]


class BodyMap(Widget):
    """Дві фігури (спереду і ззаду); колір групи залежить від прокачки."""

    def __init__(self, levels, **kw):
        super().__init__(**kw)
        self.levels = levels
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *_):
        self.canvas.clear()
        fw = self.width / 2.0
        k = min(fw / 100.0, self.height / 200.0)
        with self.canvas:
            for fi, shapes in enumerate((BODY_FRONT, BODY_BACK)):
                ox = self.x + fi * fw + (fw - 100 * k) / 2.0
                top = self.y + self.height - (self.height - 200 * k) / 2.0
                for grp, kind, x, y, w, h in shapes:
                    Color(*(level_color(self.levels.get(grp, 0)) if grp else (0.55, 0.5, 0.7, 1)))
                    args = dict(pos=(ox + x * k, top - (y + h) * k), size=(w * k, h * k))
                    (Ellipse if kind == "e" else Rectangle)(**args)


def fmt_target(ex):
    if ex["kind"] == "reps":
        return f"{ex['sets']} × {ex['target']} повторень"
    t = ex["target"]
    if t >= 60 and t % 60 == 0:
        return f"{ex['sets']} × {t // 60} хв"
    return f"{ex['sets']} × {t} с"


class GodLevelApp(App):
    title = "God-level upgrade"

    # ------------------------------------------------------------ каркас
    def build(self):
        self.data_path = os.path.join(self.user_data_dir, "user_data.json")
        self.data = L.load_data(self.data_path)
        self.stack, self.current = [], None
        self.ticker = None
        self.tm = None            # таймер поточної вправи
        self.free_clock = L.StopClock("down", 60)
        self.flash = ""           # коротке повідомлення на наступному екрані
        self._popup = None

        root = BoxLayout(orientation="vertical", padding=[dp(10), dp(8), dp(10), dp(6)], spacing=dp(6))
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.back_btn = RButton(text="Назад", bg=GREY_BTN, size_hint=(None, 1), width=dp(84),
                                font_size=dp(14), color=rgba("#ffffff"))
        self.back_btn.bind(on_release=lambda *_: self.back())
        self.title_lbl = Label(text="", font_size=dp(19), bold=True, color=rgba(TEXT),
                               halign="left", valign="middle")
        self.title_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        header.add_widget(self.back_btn)
        header.add_widget(self.title_lbl)
        root.add_widget(header)

        self.scroll = ScrollView(bar_width=dp(3))
        self.content = BoxLayout(orientation="vertical", spacing=dp(10),
                                 padding=[0, dp(4), 0, dp(12)], size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        root.add_widget(self.scroll)

        nav = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(4))
        for text, fn in [("Домівка", self.show_home), ("Тренінг", self.show_workout),
                         ("Календар", self.show_calendar), ("Тренер", self.show_coach),
                         ("Профіль", self.show_profile)]:
            b = RButton(text=text, bg="#2b2745", font_size=dp(12), color=rgba("#ffffff"))
            b.bind(on_release=lambda _i, f=fn: self.safe(lambda: self.go_root(f))())
            nav.add_widget(b)
        root.add_widget(nav)

        Window.bind(on_keyboard=self.on_key)
        if not self.data.get("onboarded"):
            self.go_root(self.show_setup)
        else:
            self.go_root(self.show_home)
        return root

    def on_stop(self):
        try:
            L.save_data(self.data, self.data_path)
        except OSError:
            pass

    def on_pause(self):
        self.on_stop()
        return True

    def on_key(self, _window, key, *_):
        if key == 27:  # Esc / кнопка «Назад» на Android
            if self._popup is not None:
                self._popup.dismiss()
                return True
            if self.stack:
                self.back()
                return True
        return False

    # ------------------------------------------------------------ навігація
    def go(self, fn, *args):
        if self.current:
            self.stack.append(self.current)
        self._show(fn, args)

    def go_root(self, fn, *args):
        self.stack = []
        self._show(fn, args)

    def back(self):
        if self.stack:
            fn, args = self.stack.pop()
            self._show(fn, args)
        else:
            self.go_root(self.show_home)

    def refresh(self):
        if self.current:
            self._show(*self.current)

    def replace(self, fn, *args):
        """Замінює поточний екран, не змінюючи стек (наприклад, наступна вправа)."""
        self._show(fn, args)

    def _show(self, fn, args):
        self.stop_ticker()
        self.current = (fn, args)
        try:
            fn(*args)
        except Exception:
            traceback.print_exc()
            self.content.clear_widgets()
            self.title_lbl.text = "Помилка"
            card = Card()
            card.add_widget(self.lbl("Не вдалося відкрити цей екран. Дані не втрачено.", 15, RED))
            card.add_widget(self.btn("На домівку", lambda: self.go_root(self.show_home)))
            self.content.add_widget(card)
        self.back_btn.opacity = 1 if self.stack else 0
        self.back_btn.disabled = not self.stack

    def safe(self, cb):
        def handler(*_):
            try:
                cb()
            except Exception:
                traceback.print_exc()
                self.popup("Помилка", "Щось пішло не так. Спробуй ще раз або повернись на домівку.")
        return handler

    # ------------------------------------------------------------ віджети-помічники
    def lbl(self, text, size=15, color=TEXT, bold=False, halign="left"):
        w = Label(text=str(text), font_size=dp(size), color=rgba(color), bold=bold,
                  halign=halign, valign="top", size_hint_y=None, height=dp(size * 1.6))
        w.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))
        w.bind(texture_size=lambda i, v: setattr(i, "height", max(v[1], dp(size)) + dp(4)))
        return w

    def btn(self, text, callback, color=PURPLE, height=46, size=15, width=None):
        kw = {}
        if width:
            kw.update(size_hint_x=None, width=dp(width))
        b = RButton(text=text, bg=color, size_hint_y=None, height=dp(height),
                    font_size=dp(size), color=rgba("#ffffff"), **kw)
        b.bind(on_release=self.safe(callback))
        return b

    def row(self, height=46, spacing=6):
        return BoxLayout(size_hint_y=None, height=dp(height), spacing=dp(spacing))

    def field(self, text="", hint="", numeric=False, height=44, multiline=False):
        return TextInput(text=text, hint_text=hint, multiline=multiline, size_hint_y=None,
                         height=dp(height), input_filter="int" if numeric else None,
                         background_normal="", background_active="",
                         background_color=rgba(INPUT_BG), foreground_color=rgba(TEXT),
                         hint_text_color=rgba("#7c7896"), cursor_color=rgba(PINK),
                         padding=[dp(10), dp(10)], font_size=dp(15))

    def choice_row(self, options, current):
        """Ряд кнопок-перемикачів. Повертає (віджет, функція_отримання_вибору)."""
        state = {"value": current if current in options else options[0]}
        row = self.row(44, 6)
        buttons = {}

        def paint():
            for name, b in buttons.items():
                b.set_bg(PURPLE if name == state["value"] else GREY_BTN)

        for name in options:
            b = RButton(text=name, bg=GREY_BTN, font_size=dp(13), color=rgba("#ffffff"))
            def pick(_i, n=name):
                state["value"] = n
                paint()
            b.bind(on_release=pick)
            buttons[name] = b
            row.add_widget(b)
        paint()
        return row, (lambda: state["value"])

    def page(self, title):
        self.content.clear_widgets()
        self.title_lbl.text = title
        self.scroll.scroll_y = 1
        if self.flash:
            card = Card(bg="#3b2f12")
            card.add_widget(self.lbl(self.flash, 15, GOLD, bold=True))
            self.content.add_widget(card)
            self.flash = ""
        return self.content

    def popup(self, title, message, buttons=None):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        sv = ScrollView()
        sv.add_widget(self.lbl(message, 15, TEXT))
        box.add_widget(sv)
        pop = Popup(title=title, content=box, size_hint=(.9, .55), auto_dismiss=False)
        buttons = buttons or [("Добре", None, PURPLE)]
        row = self.row(46, 8)

        def make(cb):
            def run():
                pop.dismiss()
                if cb:
                    cb()
            return run

        for text, cb, color in buttons:
            row.add_widget(self.btn(text, make(cb), color))
        box.add_widget(row)
        pop.bind(on_dismiss=lambda *_: setattr(self, "_popup", None))
        self._popup = pop
        pop.open()

    def save(self):
        try:
            L.save_data(self.data, self.data_path)
        except OSError:
            self.popup("Збереження", "Не вдалося зберегти дані. Перевір вільне місце на пристрої.")

    def stop_ticker(self):
        if self.ticker is not None:
            self.ticker.cancel()
            self.ticker = None

    def start_ticker(self, fn):
        self.stop_ticker()
        self.ticker = Clock.schedule_interval(fn, 0.25)

    def open_url(self, url):
        try:
            if platform == "android":
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                activity = autoclass("org.kivy.android.PythonActivity").mActivity
                activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            else:
                webbrowser.open(url)
        except Exception:
            traceback.print_exc()
            self.popup("Відео", "Не вдалося відкрити браузер.")

    def video_url(self, query):
        return "https://www.youtube.com/results?search_query=" + quote(query)

    # ------------------------------------------------------------ домівка
    def show_home(self):
        night = L.check_night_attack(self.data, datetime.now())
        if night:
            self.save()
            Clock.schedule_once(lambda _dt: self.popup("Нічна подія", night), 0.3)
        c = self.page("GOD-LEVEL UPGRADE")
        p = self.data["profile"]
        today = date.today()
        lvl, cur, need = L.level_info(p.get("xp", 0))
        streak = L.compute_streak(self.data["workouts"], today)

        hero = Card(bg=PANEL_HERO)
        hero.add_widget(self.lbl(f"Вітаю, {p.get('nickname', 'Гравець')}!", 22, bold=True))
        hero.add_widget(self.lbl(f"Рівень {lvl}  •  {p.get('title', 'Новачок')}", 15, GOLD))
        hero.add_widget(ProgressBar(max=need, value=cur, size_hint_y=None, height=dp(12)))
        hero.add_widget(self.lbl(f"До наступного рівня: {need - cur} XP  •  Серія: {streak} дн.", 13, MUTED))
        if p.get("pinned_badge"):
            hero.add_widget(self.lbl(f"Закріплений значок: {p['pinned_badge']}", 13, PINK))
        c.add_widget(hero)

        label, tip = L.readiness(self.data, today)
        colors = {"На повну": GREEN_TEXT, "Помірно": GOLD, "Легко": "#fb923c", "Відновлення": "#60a5fa"}
        adv = Card()
        adv.add_widget(self.lbl(f"Режим на сьогодні: {label}", 16, colors.get(label, TEXT), bold=True))
        adv.add_widget(self.lbl(tip, 14, MUTED))
        c.add_widget(adv)

        plan = L.build_plan(p, today)
        key = today.isoformat()
        total, done = L.total_sets(plan), L.sets_done(self.data, key)
        finished = self.data["workouts"].get(key, {}).get("done")
        wk = Card()
        wk.add_widget(self.lbl(f"Сьогодні: {plan['name']}", 17, bold=True))
        wk.add_widget(ProgressBar(max=max(total, 1), value=done, size_hint_y=None, height=dp(10)))
        wk.add_widget(self.lbl(f"Підходів: {done} з {total}" + ("  •  тренування завершено" if finished else ""), 13, MUTED))
        caption = "Переглянути тренування" if finished else ("Продовжити тренування" if done else "Почати тренування")
        wk.add_widget(self.btn(caption, lambda: self.go(self.show_workout), GREEN))
        c.add_widget(wk)

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for text, fn, col in [("Вільний таймер", self.show_timer, "#6d4aa8"),
                              ("Сон і відновлення", self.show_sleep, "#425b91"),
                              ("Бібліотека вправ", self.show_exercises, "#386b83"),
                              ("Відео та бойові мистецтва", self.show_videos, "#9a4564"),
                              ("Календар", self.show_calendar, "#5b4b9a"),
                              ("Бій з монстрами", self.show_battle, "#a0422f"),
                              ("Налаштування", self.show_setup, GREY_BTN)]:
            grid.add_widget(self.btn(text, lambda f=fn: self.go(f), col, height=64, size=14))
        c.add_widget(grid)
        c.add_widget(self.lbl("Біль, запаморочення або незвична слабкість — привід зупинитися. "
                              "Відпочинок не є провалом.", 12, MUTED))

    # ------------------------------------------------------------ налаштування
    def show_setup(self):
        c = self.page("Налаштування персонажа")
        p = self.data["profile"]
        if not self.data.get("onboarded"):
            c.add_widget(self.lbl("Кілька запитань, щоб підібрати план. Усе зберігається лише на цьому пристрої.", 14, MUTED))
        inputs = {}
        for caption, key, numeric in [("Псевдонім", "nickname", False), ("Вік", "age", True),
                                      ("Вага (кг)", "weight", True), ("Зріст (см)", "height", True)]:
            c.add_widget(self.lbl(caption, 14, MUTED))
            inp = self.field(str(p.get(key, "")), numeric=numeric)
            inputs[key] = inp
            c.add_widget(inp)
        c.add_widget(self.lbl("Скільки займаєшся", 14, MUTED))
        exp_row, get_exp = self.choice_row(["Початківець", "Середній", "Досвідчений"], p.get("experience", "Початківець"))
        c.add_widget(exp_row)
        c.add_widget(self.lbl("Важкість тренувань", 14, MUTED))
        int_row, get_int = self.choice_row(["Легке", "Середнє", "Важке"], p.get("intensity", "Легке"))
        c.add_widget(int_row)
        c.add_widget(self.lbl("Мета", 14, MUTED))
        goal = self.field(p.get("goal", ""), hint="сила, витривалість, загальна форма")
        c.add_widget(goal)

        def save():
            vals = {k: w.text.strip() for k, w in inputs.items()}
            for key, lo, hi, name in [("age", 5, 100, "Вік"), ("weight", 20, 300, "Вага"), ("height", 80, 250, "Зріст")]:
                if vals[key] and not (lo <= L.safe_int(vals[key], -1) <= hi):
                    self.popup("Перевір дані", f"{name}: введи число від {lo} до {hi} або залиш поле порожнім.")
                    return
            for key, val in vals.items():
                p[key] = val
            p["nickname"] = p["nickname"][:20] or "Гравець"
            p["experience"] = get_exp()
            p["intensity"] = get_int()
            p["goal"] = goal.text.strip() or "Загальна фізична форма"
            self.data["onboarded"] = True
            self.save()
            self.go_root(self.show_home)

        c.add_widget(self.btn("Зберегти профіль", save, GREEN))

        def reset():
            self.data = L.fresh_data()
            self.save()
            self.tm = None
            self.go_root(self.show_setup)

        c.add_widget(self.btn("Скинути весь прогрес", lambda: self.popup(
            "Скинути прогрес?", "Буде видалено профіль, тренування, сон, значки й історію чату. Це не можна скасувати.",
            [("Скасувати", None, GREY_BTN), ("Скинути", reset, "#b91c1c")]), "#6b2b3b", height=40, size=13))

    # ------------------------------------------------------------ тренування
    def show_workout(self):
        c = self.page("Тренування сьогодні")
        today = date.today()
        key = today.isoformat()
        plan = L.build_plan(self.data["profile"], today)
        total, done = L.total_sets(plan), L.sets_done(self.data, key)
        entry = self.data["workouts"].get(key, {})

        head = Card(bg=PANEL_HERO)
        head.add_widget(self.lbl(f"{plan['name']}  •  {plan['difficulty'].capitalize()}", 20, GOLD, bold=True))
        head.add_widget(ProgressBar(max=max(total, 1), value=done, size_hint_y=None, height=dp(12)))
        head.add_widget(self.lbl(f"Підходів виконано: {done} з {total}", 14, MUTED))
        if plan["rest_day"]:
            head.add_widget(self.lbl("День відновлення: роби спокійно, без рекордів. Це теж прогрес.", 13, MUTED))
        else:
            head.add_widget(self.lbl("Почни з розминки 5–8 хвилин. Не тренуйся через біль.", 13, MUTED))
        c.add_widget(head)

        for i, ex in enumerate(plan["exercises"]):
            sd = L.sets_done_for(self.data, key, i)
            complete = sd >= ex["sets"]
            card = Card(bg=PANEL_DONE if complete else PANEL)
            card.add_widget(self.lbl(f"{i + 1}. {ex['name']}", 17, bold=True))
            card.add_widget(self.lbl(fmt_target(ex), 14, GOLD))
            card.add_widget(self.lbl(f"Виконано: {sd} з {ex['sets']}", 13, GREEN_TEXT if complete else MUTED))
            r = self.row(44, 8)
            r.add_widget(self.btn("Техніка", lambda n=ex["name"]: self.go(self.show_exercise_detail, n), GREY_BTN, height=44, size=14))
            caption = "Відкрити" if complete else ("Продовжити" if sd else "Почати")
            r.add_widget(self.btn(caption, lambda k=i: self.go(self.show_exercise_run, k), GREEN if not complete else BLUE, height=44, size=14))
            card.add_widget(r)
            c.add_widget(card)

        if entry.get("done"):
            tag = "частково" if entry.get("partial") else "повністю"
            c.add_widget(self.lbl(f"Тренування зараховане ({tag}): {entry.get('sets_done', 0)} з {entry.get('sets_total', 0)} підходів.", 14, GREEN_TEXT))
        caption = "Оновити результат" if entry.get("done") else "Завершити тренування"
        c.add_widget(self.btn(caption, self.finish_workout, GREEN))
        c.add_widget(self.lbl("XP нараховується за виконані підходи та бонус за повне тренування — не за натискання кнопки.", 12, MUTED))

    def finish_workout(self):
        today = date.today()
        key = today.isoformat()
        plan = L.build_plan(self.data["profile"], today)
        done, total = L.sets_done(self.data, key), L.total_sets(plan)
        if done == 0:
            self.popup("Ще немає підходів", "Виконай хоча б один підхід у вправах, тоді тренування можна завершити.")
            return

        def do():
            before = self.data["profile"]["level"]
            res = L.finish_workout(self.data, plan, today)
            if not res["ok"]:
                self.popup("Тренування", res["reason"])
                return
            self.save()
            lines = [f"Підходів: {done} з {total}."]
            lines.append(f"Бонус за повне тренування: +{res['bonus']} XP." if res["bonus"]
                         else ("Тренування зараховано частково — відпочинок теж частина прогресу." if not res["full"] else "Бонус уже було отримано."))
            if self.data["profile"]["level"] > before:
                lines.append(f"Новий рівень: {self.data['profile']['level']}!")
            if res["comeback"] >= 2:
                lines.append(f"З поверненням! Пропущено тренувальних днів: {res['comeback']}. Без осуду — головне, що ти тут.")
            for kind, name, rarity in res["new"]:
                lines.append(f"Нова нагорода ({kind}): {name}" + (f" — {rarity}" if rarity else ""))
            self.refresh()
            self.popup("Тренування завершено", "\n".join(lines))

        if done < total:
            self.popup("Завершити зараз?", f"Виконано {done} з {total} підходів. Можна завершити зараз або ще потренуватися.",
                       [("Ще потренуюсь", None, GREY_BTN), ("Завершити", do, GREEN)])
        else:
            do()

    # ------------------------------------------------------------ екран вправи + таймер
    def show_exercise_run(self, idx):
        today = date.today()
        key = today.isoformat()
        plan = L.build_plan(self.data["profile"], today)
        if idx >= len(plan["exercises"]):
            self.back()
            return
        ex = plan["exercises"][idx]
        c = self.page(ex["name"])
        sd = L.sets_done_for(self.data, key, idx)
        ident = (key, idx)

        if not self.tm or self.tm["ident"] != ident:
            self.tm = {"ident": ident, "phase": "work", "clock": self.work_clock(ex), "last": None}
        tm = self.tm
        if sd >= ex["sets"] and tm["phase"] != "rest":
            tm["phase"] = "done"
        if tm["phase"] == "done" and sd < ex["sets"]:
            tm["phase"], tm["clock"] = "work", self.work_clock(ex)
        phase = tm["phase"]
        clock = tm["clock"]

        info = Card(bg=PANEL_HERO)
        if phase == "done":
            info.add_widget(self.lbl("Усі підходи цієї вправи виконано!", 18, GREEN_TEXT, bold=True))
        else:
            info.add_widget(self.lbl(f"Підхід {min(sd + 1, ex['sets'])} з {ex['sets']}", 18, GOLD, bold=True))
        info.add_widget(self.lbl(f"Ціль: {fmt_target(ex)}", 14, TEXT))
        rec = self.data["records"].get(ex["name"], {})
        if ex["kind"] == "reps" and rec.get("best_reps"):
            info.add_widget(self.lbl(f"Рекорд: {rec['best_reps']} повторень", 13, MUTED))
        if ex["kind"] == "time" and rec.get("best_sec"):
            info.add_widget(self.lbl(f"Рекорд: {rec['best_sec']} с", 13, MUTED))
        if tm.get("last"):
            info.add_widget(self.lbl(f"Минулий підхід: {tm['last']}", 13, MUTED))
        c.add_widget(info)

        timer_card = Card()
        titles = {"work": "Робочий підхід", "rest": "Відпочинок", "done": "Готово"}
        timer_card.add_widget(self.lbl(titles[phase], 15, PINK if phase == "rest" else MUTED, halign="center"))
        disp = self.lbl(L.fmt_clock(clock.display()), 54, GOLD, bold=True, halign="center")
        status = self.lbl("", 14, MUTED, halign="center")
        timer_card.add_widget(disp)
        timer_card.add_widget(status)

        def update(_dt=0):
            disp.text = L.fmt_clock(clock.display())
            if clock.mode == "down" and clock.running and clock.finished():
                clock.pause()
                status.text = "Час вийшов! Можна зберегти підхід." if phase == "work" else "Відпочинок завершено. Починай наступний підхід."
                disp.text = "00:00"
            elif clock.running:
                status.text = "Іде час..."
            elif clock.elapsed > 0:
                status.text = "Пауза"
            else:
                status.text = "Натисни «Старт», коли будеш готовий"

        if phase != "done":
            ctr = self.row(46, 6)
            ctr.add_widget(self.btn("Старт", lambda: (clock.start(), update()), GREEN))
            ctr.add_widget(self.btn("Пауза", lambda: (clock.pause(), update()), "#6b5b91"))
            ctr.add_widget(self.btn("Скинути", lambda: (clock.reset(), update()), "#6b425b"))
            timer_card.add_widget(ctr)
        c.add_widget(timer_card)
        update()
        self.start_ticker(update)

        if phase == "work":
            reps_in = None
            if ex["kind"] == "reps":
                box = Card()
                box.add_widget(self.lbl("Скільки повторень зробив?", 14, MUTED))
                reps_in = self.field(str(ex["target"]), numeric=True)
                box.add_widget(reps_in)
                c.add_widget(box)

            def save_set():
                el = clock.elapsed
                reps = 0
                if ex["kind"] == "reps":
                    reps = L.safe_int(reps_in.text, 0)
                    if not 1 <= reps <= 500:
                        self.popup("Повторення", "Введи кількість повторень від 1 до 500.")
                        return
                    if el < 3:
                        self.popup("Запусти таймер", "XP нараховується лише за реально виконані підходи: натисни «Старт», виконай підхід і збережи.")
                        return
                elif el < ex["target"] * 0.5:
                    self.popup("Підхід ще не закінчено", "Дочекайся хоча б половини часу — тоді підхід зарахується.")
                    return
                clock.pause()
                seconds = int(round(min(el, max(ex["target"] * 3, 600))))
                lvl_before = self.data["profile"]["level"]
                res = L.record_set(self.data, key, idx, ex, reps, seconds)
                if res["ignored"]:
                    self.refresh()
                    return
                new = L.check_achievements(self.data, today)
                self.data["profile"]["title"] = L.pick_title(self.data)
                self.save()
                msg = [f"+{res['xp']} XP"]
                if res["pr"]:
                    msg.append("НОВИЙ РЕКОРД!")
                if self.data["profile"]["level"] > lvl_before:
                    msg.append(f"Рівень {self.data['profile']['level']}!")
                for kind, name, _r in new:
                    msg.append(f"Нова нагорода ({kind}): {name}")
                self.flash = "  •  ".join(msg)
                tm["last"] = f"{reps} повт., {seconds} с" if ex["kind"] == "reps" else f"{seconds} с"
                if L.next_in_circuit(plan, self.data, key) is not None:
                    tm["phase"], tm["clock"] = "rest", L.StopClock("down", ex["rest"])
                else:
                    tm["phase"] = "done"
                self.refresh()

            c.add_widget(self.btn("Підхід виконано", save_set, GREEN, height=52, size=17))
        elif phase == "rest":
            nxt = L.next_in_circuit(plan, self.data, key)
            nxt_name = plan["exercises"][nxt]["name"] if nxt is not None else ""
            c.add_widget(self.lbl(f"Ця група м'язів відпочиває. Далі за колом: {nxt_name}", 14, GOLD))
            if nxt is not None:
                c.add_widget(self.btn(f"Далі: {nxt_name}", lambda: self.replace(self.show_exercise_run, nxt), GREEN, height=52, size=16))
            c.add_widget(self.lbl("Відпочинок не стартує сам — натисни «Старт», коли готовий.", 12, MUTED))
        else:
            nxt = L.next_in_circuit(plan, self.data, key)
            if nxt is not None:
                c.add_widget(self.btn("Далі за колом", lambda: self.replace(self.show_exercise_run, nxt), GREEN, height=52, size=16))
            c.add_widget(self.btn("До списку вправ", self.back, BLUE))

        c.add_widget(self.btn("Показати техніку", lambda: self.go(self.show_exercise_detail, ex["name"]), GREY_BTN))
        c.add_widget(self.btn("Назад до тренування", self.back, "#2b2745", height=40, size=14))

    def work_clock(self, ex):
        return L.StopClock("down", ex["target"]) if ex["kind"] == "time" else L.StopClock("up")

    # ------------------------------------------------------------ вільний таймер
    def show_timer(self):
        c = self.page("Вільний таймер")
        clock = self.free_clock
        card = Card()
        card.add_widget(self.lbl("Для відпочинку між підходами або власного відліку", 13, MUTED))
        field = self.field(str(clock.target or 60), numeric=True)
        card.add_widget(field)
        disp = self.lbl(L.fmt_clock(clock.display()), 54, GOLD, bold=True, halign="center")
        status = self.lbl("", 14, MUTED, halign="center")

        def update(_dt=0):
            disp.text = L.fmt_clock(clock.display())
            if clock.mode == "down" and clock.running and clock.finished():
                clock.pause()
                disp.text = "00:00"
                status.text = "Час вийшов!"
            elif clock.running:
                status.text = "Іде час..."
            else:
                status.text = "Пауза" if clock.elapsed > 0 else "Готовий до старту"

        def start():
            if clock.mode == "down" and (clock.elapsed == 0 or clock.finished()):
                clock.reset(max(1, min(L.safe_int(field.text, 60), 3600)))
            clock.start()
            update()

        def reset():
            clock.reset(max(1, min(L.safe_int(field.text, 60), 3600)) if clock.mode == "down" else None)
            update()

        def preset(sec):
            field.text = str(sec)
            clock.mode = "down"
            clock.reset(sec)
            update()

        pr = self.row(40, 6)
        for sec in (30, 60, 90, 120):
            pr.add_widget(self.btn(f"{sec} с", lambda s=sec: preset(s), GREY_BTN, height=40, size=13))
        card.add_widget(pr)
        card.add_widget(disp)
        card.add_widget(status)
        ctr = self.row(46, 6)
        ctr.add_widget(self.btn("Старт", start, GREEN))
        ctr.add_widget(self.btn("Пауза", lambda: (clock.pause(), update()), "#6b5b91"))
        ctr.add_widget(self.btn("Скинути", reset, "#6b425b"))
        card.add_widget(ctr)

        def toggle():
            clock.pause()
            clock.mode = "up" if clock.mode == "down" else "down"
            clock.reset(max(1, L.safe_int(field.text, 60)))
            self.refresh()

        card.add_widget(self.btn("Режим: " + ("зворотний відлік" if clock.mode == "down" else "секундомір") + " (змінити)", toggle, "#45445b", height=40, size=13))
        c.add_widget(card)
        update()
        self.start_ticker(update)

    # ------------------------------------------------------------ календар
    def show_calendar(self):
        c = self.page("Календар і прогрес")
        today = date.today()
        start = today - timedelta(days=today.weekday() + 21)
        legend = Card()
        legend.add_widget(self.lbl("Зелений — виконано, світло-зелений — частково, жовтий — відновлення, червоний — пропуск, синя рамка — сьогодні.", 12, MUTED))
        c.add_widget(legend)

        detail = Card()
        detail_lbl = self.lbl("Натисни на день, щоб побачити подробиці.", 14, TEXT)
        detail.add_widget(detail_lbl)

        def describe(d):
            e = self.data["workouts"].get(d.isoformat(), {})
            head = d.strftime("%d.%m.%Y")
            if e.get("done"):
                tag = "частково" if e.get("partial") else "повністю"
                return f"{head}: {e.get('name', 'тренування')} ({tag}). Підходів: {e.get('sets_done', 0)} з {e.get('sets_total', 0)}. Важкість: {e.get('difficulty', '-')}."
            plan = L.build_plan(self.data["profile"], d)
            if d >= today:
                nm, parts = L.plan_summary(self.data["profile"], d)
                return f"{head}: {nm}\n" + "\n".join(parts)
            if L.is_rest_day(d):
                return f"{head}: день відновлення."
            return f"{head}: тренування не позначено. Нічого страшного — повертайся до плану."

        grid = GridLayout(cols=7, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for name in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]:
            grid.add_widget(self.lbl(name, 12, MUTED, halign="center"))
        for i in range(28):
            d = start + timedelta(days=i)
            e = self.data["workouts"].get(d.isoformat(), {})
            if e.get("done"):
                col = "#2f9e5b" if not e.get("partial") else "#6fbf8a"
            elif L.is_rest_day(d):
                col = "#a3801f"
            elif d < today:
                col = "#9b3b4b"
            else:
                col = "#2b2745"
            b = RButton(text=str(d.day), bg=col, font_size=dp(13), color=rgba("#ffffff"),
                        size_hint_y=None, height=dp(44))
            if d == today:
                b.text = f"[{d.day}]"
            b.bind(on_release=lambda _i, dd=d: setattr(detail_lbl, "text", describe(dd)))
            grid.add_widget(b)
        c.add_widget(grid)
        c.add_widget(detail)

        done = L.completed_count(self.data["workouts"])
        week_start = today - timedelta(days=today.weekday())
        week = sum(1 for i in range(7) if self.data["workouts"].get((week_start + timedelta(days=i)).isoformat(), {}).get("done"))
        stats = Card()
        stats.add_widget(self.lbl(f"Усього тренувань: {done}", 16, GREEN_TEXT, bold=True))
        stats.add_widget(self.lbl(f"На цьому тижні: {week}  •  Серія: {L.compute_streak(self.data['workouts'], today)} дн.", 14, GOLD))
        stats.add_widget(self.lbl("Дні відновлення (середа та неділя) не рвуть серію.", 12, MUTED))
        c.add_widget(stats)

    # ------------------------------------------------------------ бій
    def show_battle(self):
        c = self.page("Бій з монстрами")
        st = L.battle_state(self.data)
        card = Card(bg=PANEL_HERO)
        card.add_widget(self.lbl(f"Монстр {st['number']} з {st['total']}: {st['name']}", 19, GOLD, bold=True))
        card.add_widget(ProgressBar(max=st["hp"], value=st["left"], size_hint_y=None, height=dp(16)))
        card.add_widget(self.lbl(f"Здоров'я: {st['left']} з {st['hp']}  •  Переможено: {st['defeated']}", 14, MUTED))
        card.add_widget(self.lbl(st["event_text"], 13, PINK))
        card.add_widget(self.lbl("Гаманець: " + L.format_coins(self.data.get("coins", 0)), 13, GOLD))
        c.add_widget(card)
        box = Card()
        win_sec = L.window_seconds(st["name"])
        box.add_widget(self.lbl(f"Зроби підхід, введи повторення (1 = 1 урон). Потім відкрий вікно: у тебе {win_sec} с, щоб вдарити. Запізнився — монстр ухиляється, урон вдвічі менший.", 13, MUTED))
        reps_in = self.field("10", numeric=True)
        box.add_widget(reps_in)
        timer_lbl = self.lbl("Вікно закрите", 16, MUTED, bold=True, halign="center")
        box.add_widget(timer_lbl)
        state = {"start": None}

        def open_window():
            state["start"] = time.time()
            strike_btn.disabled = False
            open_btn.disabled = True

            def tick(_dt=0):
                left = win_sec - (time.time() - state["start"])
                if left > 0:
                    timer_lbl.text = f"Монстр відкрився! {left:0.1f} с"
                    timer_lbl.color = rgba(GREEN_TEXT)
                else:
                    timer_lbl.text = "Монстр ухилився! Вдар — урон буде меншим"
                    timer_lbl.color = rgba(RED)
            self.start_ticker(tick)

        def hit():
            started = state["start"]
            in_win = started is not None and L.window_result(started, time.time(), win_sec)
            res = L.battle_hit(self.data, reps_in.text, in_window=in_win)
            if not res["ok"]:
                self.popup("Удар", f"Введи число повторень від 1 до {L.MAX_HIT_REPS}.")
                return
            lvl_before = self.data["profile"]["level"]
            self.save()
            msg = f"Завдано {res['dealt']} урону!" + (" Монстр ухилився, урон вдвічі менший." if res.get("late") else "")
            if res.get("blocked"):
                msg = "Щит відбив удар! Зроби більше повторень за один підхід."
            if res["killed"]:
                msg = f"{res['monster']} переможено! +{res['xp']} XP, {L.format_coins(res['coins'])}"
                if self.data["profile"]["level"] > lvl_before:
                    msg += f"  •  Рівень {self.data['profile']['level']}!"
                if res.get("card"):
                    n, r, q, dup = res["card"]
                    msg += f"\nКартка: {n} ({r})" + (" — вже була" if dup else " — нова!")
                for kind, name, _r in res.get("new", []):
                    msg += f"\nНовий {kind}: {name}"
            self.flash = msg
            self.refresh()

        open_btn = self.btn("Відкрити вікно удару", open_window, BLUE, height=46, size=15)
        strike_btn = self.btn("УДАР!", hit, GREEN, height=58, size=20)
        strike_btn.disabled = True
        box.add_widget(open_btn)
        box.add_widget(strike_btn)
        box.add_widget(self.lbl("Бий монстра після реального підходу. Не накручуй: XP за перемогу — це твоя власна сила.", 12, MUTED))
        c.add_widget(box)

        camp = Card()
        data_camp = self.data.get("camp")
        if data_camp:
            camp.add_widget(self.lbl("Ти в таборі" + (" (намет)" if data_camp["tent"] else " (просто неба)") + ". Спи спокійно, а я пильную.", 14, GOLD))
        else:
            camp.add_widget(self.lbl("Привал: відпочинь між боями. Закриєш застосунок без табору — ризик нападу.", 13, MUTED))
            r = self.row(46, 6)

            def make_camp(tent):
                L.camp_start(self.data, datetime.now(), tent)
                self.save()
                self.flash = "Табір розбито."
                self.refresh()

            r.add_widget(self.btn("Намет (безпечніше)", lambda: make_camp(True), BLUE, height=46, size=13))
            r.add_widget(self.btn("Просто неба", lambda: make_camp(False), GREY_BTN, height=46, size=13))
            camp.add_widget(r)
        c.add_widget(camp)


    # ------------------------------------------------------------ сон
    def show_sleep(self):
        c = self.page("Сон і відновлення")
        today = date.today()
        last = next((self.data["sleep"][(today - timedelta(days=i)).isoformat()]
                     for i in range(7) if (today - timedelta(days=i)).isoformat() in self.data["sleep"]), {})
        card = Card()
        card.add_widget(self.lbl("Запиши сон за минулу ніч", 17, GOLD, bold=True))
        start = self.field(last.get("bedtime", ""), hint="Коли заснув? Наприклад 22:30")
        end = self.field(last.get("wake", ""), hint="Коли прокинувся? Наприклад 07:00")
        card.add_widget(start)
        card.add_widget(end)
        card.add_widget(self.lbl("Якість сну (1 — погано, 5 — чудово)", 13, MUTED))
        q_row, get_q = self.choice_row(["1", "2", "3", "4", "5"], str(last.get("quality", 3)))
        card.add_widget(q_row)

        def save():
            hours = L.sleep_hours(start.text, end.text)
            if hours is None:
                self.popup("Перевір час", "Введи час у форматі ГГ:ХХ, наприклад 22:30 і 07:00.")
                return
            q = L.safe_int(get_q(), 3)
            self.data["sleep"][today.isoformat()] = {"bedtime": start.text.strip(), "wake": end.text.strip(), "hours": hours, "quality": q}
            new = L.check_achievements(self.data, today)
            self.save()
            age = L.safe_int(self.data["profile"].get("age"), 0) or None
            extra = "".join(f"\nНова нагорода ({k}): {n}" for k, n, _r in new)
            self.refresh()
            self.popup("Сон збережено", L.sleep_advice(hours, q, age) + extra)

        card.add_widget(self.btn("Зберегти сон", save, GREEN))
        c.add_widget(card)

        avg = L.avg_sleep(self.data, today)
        rep = Card()
        rep.add_widget(self.lbl("Останні 7 днів" + (f"  •  середнє {avg} год" if avg else ""), 16, bold=True))
        any_row = False
        for i in range(7):
            d = today - timedelta(days=i)
            e = self.data["sleep"].get(d.isoformat())
            if e and e.get("hours") is not None:
                any_row = True
                rep.add_widget(self.lbl(f"{d.strftime('%d.%m')}  —  {e['hours']} год, якість {e.get('quality', '-')}/5", 14, TEXT))
                rep.add_widget(ProgressBar(max=10, value=min(e["hours"], 10), size_hint_y=None, height=dp(8)))
        if not any_row:
            rep.add_widget(self.lbl("Записів поки немає.", 14, MUTED))
        c.add_widget(rep)
        tip = Card()
        tip.add_widget(self.lbl("Лягай і прокидайся в приблизно один і той самий час. За годину до сну — без яскравих екранів. "
                                "Підліткам зазвичай потрібно 8–10 годин сну.", 13, MUTED))
        c.add_widget(tip)

    # ------------------------------------------------------------ бібліотека вправ
    def show_exercises(self):
        c = self.page("Бібліотека вправ")
        c.add_widget(self.lbl("Обери вправу: техніка, типові помилки, легший варіант і відео.", 14, MUTED))
        for name, item in L.EXERCISES.items():
            c.add_widget(self.btn(f"{name}", lambda n=name: self.go(self.show_exercise_detail, n), "#386b83"))

    def show_exercise_detail(self, name):
        item = L.EXERCISES.get(name)
        c = self.page(name)
        if not item:
            c.add_widget(self.lbl("Вправу не знайдено.", 14, MUTED))
            return
        card = Card()
        card.add_widget(self.lbl("Працюють м'язи", 16, GOLD, bold=True))
        card.add_widget(self.lbl(item["muscles"], 14))
        c.add_widget(card)
        tech = Card()
        tech.add_widget(self.lbl("Техніка виконання", 16, GOLD, bold=True))
        for i, step in enumerate(item["steps"], 1):
            tech.add_widget(self.lbl(f"{i}. {step}", 14))
        c.add_widget(tech)
        err = Card()
        err.add_widget(self.lbl("Типові помилки", 16, PINK, bold=True))
        err.add_widget(self.lbl(item["mistakes"], 14))
        err.add_widget(self.lbl("Легший варіант", 16, GREEN_TEXT, bold=True))
        err.add_widget(self.lbl(item["easier"], 14))
        c.add_widget(err)
        c.add_widget(self.btn("Знайти відео з технікою", lambda: self.open_url(self.video_url(item["video"])), "#5b4b9a"))
        c.add_widget(self.btn("Запитати тренера про вправу", lambda: self.go(self.show_coach, f"Поясни, як правильно виконувати вправу «{name}»."), "#8b4a9c"))

    def show_videos(self):
        c = self.page("Відео та бойові мистецтва")
        c.add_widget(self.lbl("Відкриває пошук навчальних відео. Обирай матеріали кваліфікованих тренерів і тренуйся в безпечному місці. "
                              "Прийоми самооборони краще вчити з тренером.", 14, MUTED))
        for title, query in [("Базова розминка", "warm up beginner exercise proper form"),
                             ("Бокс — стійка та робота ніг", "boxing beginner stance footwork tutorial"),
                             ("Карате — основи", "karate beginner basics tutorial"),
                             ("Тхеквондо — основи", "taekwondo beginner basics tutorial"),
                             ("Дзюдо — правила та безпека", "judo beginner rules safety tutorial"),
                             ("Самооборона — безпека та уникнення конфлікту", "beginner self defense awareness de-escalation"),
                             ("Загальна фізична підготовка", "beginner bodyweight workout proper form")]:
            c.add_widget(self.btn(title, lambda q=query: self.open_url(self.video_url(q)), "#5b4b9a"))

    # ------------------------------------------------------------ тренер
    def show_coach(self, prefill=""):
        c = self.page("ШІ-тренер")
        c.add_widget(self.lbl("Запитуй про техніку, м'язи, відпочинок, сон і самопочуття. Це офлайн-помічник, не лікар.", 13, MUTED))
        history = self.data.get("chat_history", [])[-12:]
        if not history:
            c.add_widget(self.lbl("Приклад: «Як правильно робити болгарські присідання?» А потім: «а які помилки?»", 13, MUTED))
        for entry in history:
            q = Card(bg="#3a2f63")
            q.add_widget(self.lbl("Ти: " + entry.get("q", ""), 14, GOLD))
            c.add_widget(q)
            a = Card()
            a.add_widget(self.lbl("Тренер: " + entry.get("a", ""), 14, TEXT))
            c.add_widget(a)

        chips = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        chips.bind(minimum_height=chips.setter("height"))
        for text in ["Чи варто сьогодні тренуватися?", "Скільки відпочивати між підходами?", "Болять м'язи після тренування", "Мої рекорди"]:
            chips.add_widget(self.btn(text, lambda t=text: self.ask_coach(t), "#4a3d7a", height=52, size=12))
        c.add_widget(chips)

        inp = self.field(prefill, hint="Напиши запитання тренеру", height=84, multiline=True)
        c.add_widget(inp)
        r = self.row(46, 8)
        r.add_widget(self.btn("Надіслати", lambda: self.ask_coach(inp.text), GREEN))
        r.add_widget(self.btn("Очистити чат", self.clear_chat, "#6b425b", width=130))
        c.add_widget(r)
        key_box = Card()
        key_box.add_widget(self.lbl("Онлайн-режим: встав свій API-ключ Anthropic (зберігається лише на телефоні). Без ключа працює офлайн-тренер.", 12, MUTED))
        key_in = self.field(self.data.get("api_key", ""), hint="sk-ant-…", height=44)
        key_box.add_widget(key_in)
        key_box.add_widget(self.btn("Зберегти ключ", lambda: self.save_api_key(key_in.text), BLUE, height=42, size=14))
        c.add_widget(key_box)
        Clock.schedule_once(lambda _dt: setattr(self.scroll, "scroll_y", 0), 0.2)

    def ask_coach(self, question):
        q = (question or "").strip()
        if not q:
            self.popup("Порожнє повідомлення", "Напиши запитання для тренера.")
            return
        key = (self.data.get("api_key") or "").strip()
        if not key:
            answer, ctx = L.coach_answer(q, self.data, date.today(), self.data.get("chat_context", ""))
            self.data["chat_context"] = ctx
            self._add_chat(q, answer)
            return
        self.flash = "Тренер думає…"
        snapshot = self.data

        def work():
            try:
                text = L.ai_request(key, snapshot, q, date.today())
                if not text:
                    raise ValueError("empty")
                suffix = ""
            except Exception:
                text, ctx = L.coach_answer(q, snapshot, date.today(), snapshot.get("chat_context", ""))
                snapshot["chat_context"] = ctx
                suffix = "\n(Немає зв'язку або ключ не підійшов: відповів офлайн-тренер.)"
            Clock.schedule_once(lambda _dt: self._add_chat(q, text + suffix), 0)

        threading.Thread(target=work, daemon=True).start()
        self.refresh()

    def _add_chat(self, q, answer):
        self.flash = ""
        self.data.setdefault("chat_history", []).append({"q": q, "a": answer, "time": datetime.now().isoformat(timespec="minutes")})
        self.data["chat_history"] = self.data["chat_history"][-50:]
        self.save()
        self.refresh()

    def save_api_key(self, value):
        self.data["api_key"] = (value or "").strip()
        self.save()
        self.flash = "Онлайн-режим увімкнено." if self.data["api_key"] else "Онлайн-режим вимкнено, працює офлайн-тренер."
        self.refresh()

    def clear_chat(self):
        self.data["chat_history"] = []
        self.data["chat_context"] = ""
        self.save()
        self.refresh()

    # ------------------------------------------------------------ профіль
    def show_profile(self):
        c = self.page("Профіль гравця")
        p = self.data["profile"]
        lvl, cur, need = L.level_info(p.get("xp", 0))
        hero = Card(bg=PANEL_HERO)
        hero.add_widget(self.lbl(f"{p.get('nickname')}  •  Рівень {lvl}", 21, GOLD, bold=True))
        hero.add_widget(self.lbl(f"Титул: {p.get('title')}", 15))
        hero.add_widget(ProgressBar(max=need, value=cur, size_hint_y=None, height=dp(12)))
        hero.add_widget(self.lbl(f"XP: {p.get('xp', 0)}  •  Серія: {L.compute_streak(self.data['workouts'], date.today())} дн.", 13, MUTED))
        if p.get("pinned_badge"):
            hero.add_widget(self.lbl(f"Закріплений значок: {p['pinned_badge']}", 13, PINK))
        c.add_widget(hero)

        forms = Card()
        forms.add_widget(self.lbl(f"Раса: {L.current_race(lvl)}", 17, GOLD, bold=True))
        for ladder in L.FORM_LADDERS:
            cur, nxt = L.current_form(lvl, ladder)
            line = f"{ladder}: {cur[1]}"
            if nxt:
                line += f"   (далі: {nxt[1]} — рівень {nxt[0]})"
            forms.add_widget(self.lbl(line, 13, TEXT))
        c.add_widget(forms)

        mus = Card()
        mus.add_widget(self.lbl("Карта м'язів", 17, GOLD, bold=True))
        levels = L.muscle_levels(self.data)
        mus.add_widget(BodyMap(levels, size_hint_y=None, height=dp(300)))
        mus.add_widget(self.lbl("Спереду і ззаду. Тьмяний фіолетовий — слабо прокачано, золотий — сильно.", 12, MUTED))
        for g, v in levels.items():
            mus.add_widget(self.lbl(f"{g}: {v}%" + ("  — качати більше" if v < 25 else ""), 13, GREEN_TEXT if v >= 50 else MUTED))
            mus.add_widget(ProgressBar(max=100, value=v, size_hint_y=None, height=dp(8)))
        c.add_widget(mus)

        rk = Card()
        rk.add_widget(self.lbl("Рейтинг проти героїв аніме", 17, GOLD, bold=True))
        rows, total_n = L.rival_window(self.data, p.get("nickname", "Ти"))
        rk.add_widget(self.lbl(f"Твоє місце — з {total_n} учасників", 13, MUTED))
        for pos, n, pts, q, me in rows:
            rk.add_widget(self.lbl(f"{pos}. {n} — {pts} очок" + (f"\n    {q}" if q else ""), 13, PINK if me else TEXT))
        c.add_widget(rk)

        c.add_widget(self.lbl("Титули (натисни, щоб закріпити)", 17, PINK, bold=True))
        info = {n: d for n, d, _ in L.TITLES}
        for name in self.data["titles"]:
            selected = name == p.get("title")
            c.add_widget(self.btn(("Обрано: " if selected else "") + name, lambda n=name: self.pin_title(n),
                                  PURPLE if selected else GREY_BTN, height=40, size=14))
        locked = [n for n, d, _ in L.TITLES if n not in self.data["titles"]]
        if locked:
            c.add_widget(self.lbl("Ще не відкрито: " + "; ".join(f"{n} ({info[n]})" for n in locked), 12, MUTED))

        cards = Card()
        cards.add_widget(self.lbl(f"Картки героїв: {len(self.data.get('cards', []))} з {len(L.CARDS)}", 17, GOLD, bold=True))
        got = set(self.data.get("cards", []))
        for n, r, q in L.CARDS:
            if n in got:
                cards.add_widget(self.lbl(f"{n} — {r}\n    «{q}»", 13, L.RARITY_COLORS[r]))
            else:
                cards.add_widget(self.lbl("??? — ще не знайдено", 12, "#6b6880"))
        cards.add_widget(self.lbl("Картки випадають після перемог: рідше зі слизів, частіше з босів.", 12, MUTED))
        c.add_widget(cards)

        c.add_widget(self.lbl("Значки (натисни, щоб закріпити)", 17, PINK, bold=True))
        have = {b["name"]: b for b in self.data["badges"]}
        for name, desc, rarity, _cond in L.BADGES:
            if name in have:
                col = L.RARITY_COLORS[rarity]
                b = RButton(text=f"{name}  —  {rarity}\n{desc}", bg="#262338", font_size=dp(13),
                            color=rgba(col), size_hint_y=None, height=dp(66))
                b.bind(on_release=self.safe(lambda n=name: self.pin_badge(n)))
                c.add_widget(b)
            else:
                card = Card(bg="#17161f")
                card.add_widget(self.lbl(f"{name}  —  {rarity}  (закрито)", 13, "#6b6880", bold=True))
                card.add_widget(self.lbl(desc, 12, "#6b6880"))
                c.add_widget(card)

        recs = [(k, v) for k, v in self.data["records"].items() if v.get("best_reps") or v.get("best_sec")]
        card = Card()
        card.add_widget(self.lbl("Особисті рекорди", 17, GOLD, bold=True))
        if recs:
            for k, v in recs:
                card.add_widget(self.lbl(f"{k}: " + (f"{v['best_reps']} повторень" if v.get("best_reps") else f"{v['best_sec']} с"), 14))
        else:
            card.add_widget(self.lbl("Поки немає. Виконуй підходи — рекорди збережуться автоматично.", 13, MUTED))
        c.add_widget(card)

    def pin_title(self, name):
        self.data["profile"]["title"] = name
        self.data["title_pinned"] = True
        self.save()
        self.refresh()

    def pin_badge(self, name):
        self.data["profile"]["pinned_badge"] = "" if self.data["profile"].get("pinned_badge") == name else name
        self.save()
        self.refresh()


if __name__ == "__main__":
    GodLevelApp().run()
