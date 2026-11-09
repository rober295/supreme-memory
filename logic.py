# -*- coding: utf-8 -*-
"""Логіка God-level upgrade без Kivy: плани, XP, серії, нагороди, сон, тренер.
Усе тут можна перевірити тестами без графічного вікна."""
import json
import random
import math
import os
import time
from datetime import date, datetime, timedelta

REST_WEEKDAYS = (2, 6)  # середа та неділя — дні відновлення

DEFAULT_DATA = {
    "profile": {"nickname": "Гравець", "age": "", "weight": "", "height": "",
                "experience": "Початківець", "intensity": "Легке",
                "goal": "Загальна фізична форма",
                "level": 1, "xp": 0, "title": "Новачок", "pinned_badge": ""},
    "workouts": {},      # {"2026-11-09": {done, partial, name, sets_done, sets_total, xp, ...}}
    "sessions": {},      # {"2026-11-09": {"sets": {"0": [{"reps":10,"sec":30}]}}}
    "sleep": {},
    "records": {},       # {"Планка": {"best_sec": 40, "best_reps": 0}}
    "badges": [],        # [{"name":..., "date":...}]
    "titles": ["Новачок"],
    "chat_history": [],
    "chat_context": "",
    "favorites": [],
    "onboarded": False,
}

RARITY_COLORS = {
    "Звичайна": "#9ca3af", "Незвичайна": "#4ade80", "Рідкісна": "#60a5fa",
    "Епічна": "#a78bfa", "Легендарна": "#fbbf24", "Міфічна": "#fb7185",
}

# ---------------------------------------------------------------- вправи
EXERCISES = {
    "Присідання до стільця": {
        "kind": "reps", "muscles": "квадрицепси, сідниці та корпус",
        "steps": ["Постав стопи приблизно на ширині плечей.", "Відведи таз назад і зігни коліна.",
                  "Легко торкнися стільця або зупинися перед ним.", "Повернися у вертикальне положення."],
        "mistakes": "Не падай на стілець і не відривай п'яти від підлоги.",
        "easier": "Використовуй вищий стілець і меншу амплітуду.",
        "video": "bodyweight squat to chair proper form beginner", "aliases": ["присід", "присед"]},
    "Віджимання від опори": {
        "kind": "reps", "muscles": "груди, плечі та трицепси",
        "steps": ["Постав долоні на стійку опору трохи ширше плечей.", "Вирівняй тіло від голови до п'ят і напруж корпус.",
                  "Повільно зігни руки та наблизь груди до опори.", "М'яко відштовхнися назад, продовжуючи дихати."],
        "mistakes": "Не прогинай поперек, не розводь лікті надмірно в сторони й не розгойдуй корпус.",
        "easier": "Віджимання від стіни або від вищої опори.",
        "video": "incline push up proper form beginner", "aliases": ["віджим", "отжим"]},
    "Ягодичний місток": {
        "kind": "reps", "muscles": "сідниці та задня поверхня стегна",
        "steps": ["Ляж на спину, зігни коліна, стопи постав на підлогу.", "Напруж сідниці та підніми таз.",
                  "Зупинися, коли тулуб і стегна утворюють приблизно одну лінію.", "Повільно опусти таз."],
        "mistakes": "Не перерозгинай поперек і не відштовхуйся шиєю.",
        "easier": "Піднімай таз на меншу висоту.",
        "video": "glute bridge proper form beginner", "aliases": ["місток", "мостик"]},
    "Підйоми на носки": {
        "kind": "reps", "muscles": "литкові м'язи",
        "steps": ["Стань рівно, можна триматися за стіну.", "Повільно підніміться на носки.",
                  "Затримайся на секунду вгорі.", "Повільно опустися на всю стопу."],
        "mistakes": "Не поспішай і не хитайся в боки.",
        "easier": "Тримайся за опору обома руками.",
        "video": "calf raises proper form beginner", "aliases": ["носк", "литк"]},
    "Dead bug": {
        "kind": "reps", "muscles": "глибокі м'язи корпусу",
        "steps": ["Ляж на спину, руки вгору, коліна зігнуті під 90°.", "Притисни поперек до підлоги.",
                  "Повільно опусти протилежні руку та ногу.", "Поверни їх і зміни сторону."],
        "mistakes": "Не відривай поперек від підлоги й не поспішай.",
        "easier": "Рухай лише ногами, руки залиш угорі.",
        "video": "dead bug exercise proper form", "aliases": ["dead bug", "дед баг"]},
    "Bird-dog": {
        "kind": "reps", "muscles": "корпус, м'язи спини та сідниці",
        "steps": ["Стань на четвереньки, долоні під плечима, коліна під тазом.", "Повільно витягни протилежні руку та ногу.",
                  "Не повертай таз і не прогинай поперек.", "Повернися та повтори на інший бік."],
        "mistakes": "Не задирай ногу високо й не поспішай.",
        "easier": "Рухай лише однією рукою або ногою.",
        "video": "bird dog exercise proper form", "aliases": ["bird-dog", "bird dog", "пташка"]},
    "Болгарські присідання": {
        "kind": "reps", "muscles": "м'язи ніг і сідниць",
        "steps": ["Стань спиною до невисокої стійкої опори.", "Постав одну стопу позаду на опору, передню стопу — достатньо далеко.",
                  "Повільно опускайся настільки, наскільки зберігаєш рівновагу.", "Піднімися, відштовхуючись передньою ногою."],
        "mistakes": "Не поспішай, не допускай хитання коліна всередину та не використовуй нестійкі предмети.",
        "easier": "Звичайний спліт-присід із задньою ногою на підлозі та опорою рукою.",
        "video": "bulgarian split squat proper form beginner", "aliases": ["болгар", "спліт-присід"]},
    "Планка": {
        "kind": "time", "muscles": "м'язи корпусу та плечі",
        "steps": ["Постав передпліччя на підлогу, лікті під плечима.", "Витягни ноги назад або залиш коліна на підлозі.",
                  "Тримай корпус рівно та дихай спокійно.", "Заверши підхід до того, як техніка почне погіршуватися."],
        "mistakes": "Не затримуй дихання, не провисай у попереку й не піднімай таз надто високо.",
        "easier": "Планка з колін або коротші інтервали.",
        "video": "plank proper form beginner", "aliases": ["планк"]},
    "Шадоубоксинг": {
        "kind": "time", "muscles": "ноги, плечі, корпус; витривалість",
        "steps": ["Стань у легку стійку, ноги трохи ширше плечей, коліна м'які.", "Руки біля підборіддя, лікті близько до корпусу.",
                  "Роби легкі прямі удари в повітря, не розгинай лікті до кінця.", "Рухайся на носках і дихай рівно."],
        "mistakes": "Не бий із повним випрямленням ліктя, не затримуй дихання, не працюй із надмірною силою.",
        "easier": "Роби повільно, без рухів ногами, лише легкі удари.",
        "video": "shadow boxing beginner tutorial", "aliases": ["шадоу", "бокс", "shadow"]},
    "Легка ходьба": {
        "kind": "time", "muscles": "усе тіло, відновлення",
        "steps": ["Іди у комфортному темпі, не задихаючись.", "Тримай поставу, плечі розслаблені.",
                  "Дихай рівно носом або ротом як зручно."],
        "mistakes": "Не перетворюй відновлення на важке тренування.",
        "easier": "Скороти час або йди повільніше.",
        "video": "easy walking recovery day", "aliases": ["ходьб"]},
    "Розтягування": {
        "kind": "time", "muscles": "усе тіло, рухливість",
        "steps": ["Рухайся плавно, без ривків.", "Затримуйся в розтягуванні на 20–30 секунд.",
                  "Не відчувай різкого болю — лише легке натягнення.", "Дихай повільно та глибоко."],
        "mistakes": "Не розтягуйся до болю і не пружинь.",
        "easier": "Зменши амплітуду.",
        "video": "full body stretching routine beginner", "aliases": ["розтяг", "стретч"]},
}

# (вправа, базове значення: повторення або секунди)
WEEK_PLAN = {
    0: ("Все тіло", [("Присідання до стільця", 10), ("Віджимання від опори", 8),
                     ("Ягодичний місток", 12), ("Планка", 20)]),
    1: ("Ноги та корпус", [("Присідання до стільця", 12), ("Підйоми на носки", 15),
                           ("Dead bug", 8), ("Ягодичний місток", 12)]),
    2: ("Відновлення", [("Легка ходьба", 600), ("Розтягування", 300)]),
    3: ("Верх тіла", [("Віджимання від опори", 8), ("Bird-dog", 8), ("Планка", 20), ("Dead bug", 8)]),
    4: ("Бій і витривалість", [("Шадоубоксинг", 60), ("Присідання до стільця", 10),
                                 ("Bird-dog", 8), ("Планка", 20)]),
    5: ("Загальна форма", [("Присідання до стільця", 10), ("Ягодичний місток", 12),
                           ("Віджимання від опори", 8), ("Bird-dog", 8)]),
    6: ("Відновлення", [("Легка ходьба", 600), ("Розтягування", 300)]),
}

INTENSITY_SETS = {"легке": 2, "середнє": 3, "важке": 4}
INTENSITY_REST = {"легке": 60, "середнє": 75, "важке": 90}


def exp_index(exp):
    e = (exp or "").lower()
    if "досвід" in e:
        return 2
    if "серед" in e:
        return 1
    return 0


def intensity_key(value):
    v = (value or "легке").strip().lower()
    for k in INTENSITY_SETS:
        if v.startswith(k[:4]):
            return k
    return "легке"


def build_plan(profile, day):
    """Структурований план на день: список вправ із підходами/повтореннями."""
    name, items = WEEK_PLAN[day.weekday()]
    rest_day = day.weekday() in REST_WEEKDAYS
    ei = exp_index(profile.get("experience"))
    ik = intensity_key(profile.get("intensity"))
    exercises = []
    if rest_day:
        for ex, val in items:
            exercises.append({"name": ex, "kind": "time", "sets": 1, "target": val, "rest": 0})
    else:
        sets = INTENSITY_SETS[ik]
        scale = 1 + 0.25 * ei
        items = list(items)
        if ei >= 1 and day.weekday() == 5:
            items.insert(1, ("Болгарські присідання", 6))
        for ex, val in items:
            kind = EXERCISES[ex]["kind"]
            target = int(round(val * scale))
            if kind == "time" and ex == "Шадоубоксинг":
                target = val
            exercises.append({"name": ex, "kind": kind, "sets": sets, "target": target,
                              "rest": INTENSITY_REST[ik]})
    return {"name": name, "rest_day": rest_day, "difficulty": ik, "exercises": exercises}


def total_sets(plan):
    return sum(e["sets"] for e in plan["exercises"])


# ---------------------------------------------------------------- XP та рівні
XP_PER_SET = 4
XP_FINISH_BONUS = 15


def level_info(xp):
    """(рівень, XP у поточному рівні, XP до наступного рівня)."""
    xp = max(0, int(xp))
    level, need = 1, 100
    while xp >= need:
        xp -= need
        level += 1
        need = 100 + (level - 1) * 20
    return level, xp, need


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- серія
def is_rest_day(d):
    return d.weekday() in REST_WEEKDAYS


def compute_streak(workouts, today):
    """Дні відновлення серію не рвуть. Сьогодні ще не зарахований день серію не рве."""
    streak = 0
    d = today
    if not workouts.get(d.isoformat(), {}).get("done"):
        d -= timedelta(days=1)
    for _ in range(400):
        entry = workouts.get(d.isoformat(), {})
        if entry.get("done"):
            streak += 1
        elif not is_rest_day(d):
            break
        d -= timedelta(days=1)
    return streak


def missed_training_days(workouts, today):
    """Скільки тренувальних (не відпочинкових) днів пропущено перед сьогоднішнім."""
    d = today - timedelta(days=1)
    missed = 0
    for _ in range(60):
        if workouts.get(d.isoformat(), {}).get("done"):
            break
        if not is_rest_day(d):
            missed += 1
        d -= timedelta(days=1)
    return missed


# ---------------------------------------------------------------- нагороди та титули
def completed_count(workouts):
    return sum(1 for v in workouts.values() if v.get("done"))


BADGES = [
    ("Перший крок", "Заверши перше тренування", "Звичайна", lambda s: s["done"] >= 1),
    ("Десятка", "10 завершених тренувань", "Незвичайна", lambda s: s["done"] >= 10),
    ("Тиждень без зривів", "Серія 7 днів", "Рідкісна", lambda s: s["streak"] >= 7),
    ("Рекордсмен", "Побий власний рекорд", "Рідкісна", lambda s: s["pr"] >= 1),
    ("Нічна варта", "Запиши сон 5 разів", "Незвичайна", lambda s: s["sleep"] >= 5),
    ("Місяць сили", "30 завершених тренувань", "Епічна", lambda s: s["done"] >= 30),
    ("Незламна воля", "Серія 30 днів", "Легендарна", lambda s: s["streak"] >= 30),
    ("Міфічний шлях", "100 завершених тренувань", "Міфічна", lambda s: s["done"] >= 100),
]

TITLES = [
    ("Новачок", "Стартовий титул", lambda s: True),
    ("Прокачувач", "Перше тренування", lambda s: s["done"] >= 1),
    ("Боєць", "Серія 3 дні", lambda s: s["streak"] >= 3),
    ("Незламний", "Серія 7 днів", lambda s: s["streak"] >= 7),
    ("Рекордсмен", "Побий рекорд", lambda s: s["pr"] >= 1),
    ("Легенда дисципліни", "Серія 30 днів", lambda s: s["streak"] >= 30),
    ("Прокрастинатор", "Повернення після 2+ пропущених днів (жарт, без покарання)", lambda s: s["comeback"] >= 2),
    ("Тюфяк у відставці", "Повернення після 5+ пропущених днів (жарт, без покарання)", lambda s: s["comeback"] >= 5),
]


def stats_for(data, today, comeback=0):
    return {
        "done": completed_count(data["workouts"]),
        "streak": compute_streak(data["workouts"], today),
        "pr": data.get("pr_count", 0),
        "sleep": len(data["sleep"]),
        "comeback": max(comeback, data.get("max_comeback", 0)),
        "kills": sum(safe_int(v) for v in (data.get("kills") or {}).values()),
        "killed": set((data.get("kills") or {}).keys()),
        "cards": len(data.get("cards") or []),
    }


def check_achievements(data, today, comeback=0):
    """Повертає список нових нагород (значки та титули)."""
    s = stats_for(data, today, comeback)
    new = []
    have_b = {b["name"] for b in data["badges"]}
    for name, desc, rarity, cond in BADGES:
        if name not in have_b and cond(s):
            data["badges"].append({"name": name, "date": today.isoformat()})
            new.append(("значок", name, rarity))
    for name, desc, cond in TITLES:
        if name not in data["titles"] and cond(s):
            data["titles"].append(name)
            new.append(("титул", name, ""))
    return new


def badge_info(name):
    for n, desc, rarity, _ in BADGES:
        if n == name:
            return desc, rarity
    return "", "Звичайна"


# ---------------------------------------------------------------- підходи, рекорди, завершення
def session_for(data, key):
    return data["sessions"].setdefault(key, {"sets": {}})


def sets_done(data, key):
    sess = data["sessions"].get(key, {"sets": {}})
    return sum(len(v) for v in sess["sets"].values())


def sets_done_for(data, key, idx):
    return len(data["sessions"].get(key, {"sets": {}})["sets"].get(str(idx), []))


def record_set(data, key, idx, ex, reps, seconds):
    """Зберігає виконаний підхід. XP за підхід нараховується один раз на кожен підхід дня."""
    sess = session_for(data, key)
    lst = sess["sets"].setdefault(str(idx), [])
    if len(lst) >= ex["sets"]:
        return {"xp": 0, "pr": False, "ignored": True}
    lst.append({"reps": reps, "sec": seconds})
    p = data["profile"]
    xp = XP_PER_SET
    p["xp"] = safe_int(p.get("xp")) + xp
    p["level"] = level_info(p["xp"])[0]
    rec = data["records"].setdefault(ex["name"], {"best_reps": 0, "best_sec": 0})
    pr = False
    had_before = rec["best_reps"] > 0 or rec["best_sec"] > 0
    if ex["kind"] == "reps" and reps > rec["best_reps"]:
        rec["best_reps"] = reps
        pr = had_before
    if ex["kind"] == "time" and seconds > rec["best_sec"]:
        rec["best_sec"] = seconds
        pr = had_before
    if pr:
        data["pr_count"] = data.get("pr_count", 0) + 1
    return {"xp": xp, "pr": pr, "ignored": False}


def finish_workout(data, plan, today):
    """Завершує тренування. XP вже нараховано за підходи; бонус лише за повне тренування."""
    key = today.isoformat()
    done_sets = sets_done(data, key)
    total = total_sets(plan)
    if done_sets == 0:
        return {"ok": False, "reason": "Спочатку виконай хоча б один підхід."}
    already = data["workouts"].get(key, {}).get("done")
    comeback = 0 if already else missed_training_days(data["workouts"], today)
    full = done_sets >= total
    bonus = 0
    if full and not data["workouts"].get(key, {}).get("bonus_paid"):
        bonus = XP_FINISH_BONUS
        p = data["profile"]
        p["xp"] = safe_int(p.get("xp")) + bonus
        p["level"] = level_info(p["xp"])[0]
    prev = data["workouts"].get(key, {})
    data["workouts"][key] = {"done": True, "partial": not full, "name": plan["name"],
                             "difficulty": plan["difficulty"], "sets_done": done_sets,
                             "sets_total": total, "rest_day": plan["rest_day"],
                             "bonus_paid": prev.get("bonus_paid", False) or bool(bonus)}
    if comeback > data.get("max_comeback", 0):
        data["max_comeback"] = comeback
    new = check_achievements(data, today, comeback)
    data["profile"]["title"] = pick_title(data)
    return {"ok": True, "full": full, "bonus": bonus, "new": new, "comeback": comeback}


def pick_title(data):
    cur = data["profile"].get("title")
    if cur in data["titles"] and data.get("title_pinned"):
        return cur
    order = [t[0] for t in TITLES]
    best = max(data["titles"], key=lambda t: order.index(t) if t in order else -1)
    jokes = ("Прокрастинатор", "Тюфяк у відставці")
    if best in jokes:
        non_joke = [t for t in data["titles"] if t not in jokes]
        best = max(non_joke, key=lambda t: order.index(t) if t in order else -1)
    return best


# ---------------------------------------------------------------- сон
def parse_time(text):
    text = (text or "").strip().replace(".", ":").replace(" ", "")
    try:
        parts = text.split(":")
        h = int(parts[0]); m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except (ValueError, IndexError):
        pass
    return None


def sleep_hours(bedtime, wake):
    b, w = parse_time(bedtime), parse_time(wake)
    if b is None or w is None:
        return None
    diff = (w - b) % (24 * 60)
    return round(diff / 60, 1)


def sleep_advice(hours, quality, age=None):
    tips = []
    low = 8 if (age is not None and 0 < age < 18) else 7
    if hours is not None:
        if hours < low:
            tips.append(f"Спав {hours} год — це менше за бажані {low}+ год. Сьогодні краще легше навантаження і раніше лягти спати.")
        elif hours > 10:
            tips.append("Дуже довгий сон: якщо так буває часто, зверни увагу на самопочуття.")
        else:
            tips.append(f"Спав {hours} год — хороший обсяг сну.")
    if quality is not None and quality <= 2:
        tips.append("Якість сну низька: без екранів за годину до сну і приблизно однаковий час засинання допомагають.")
    tips.append("Намагайся засинати в один і той самий час.")
    return " ".join(tips)


def avg_sleep(data, today, days=7):
    vals = []
    for i in range(days):
        e = data["sleep"].get((today - timedelta(days=i)).isoformat())
        if e and e.get("hours") is not None:
            vals.append(e["hours"])
    return round(sum(vals) / len(vals), 1) if vals else None


# ---------------------------------------------------------------- готовність / порада дня
def readiness(data, today):
    """Порада: відпочити, полегшити чи тренуватися на повну."""
    plan = build_plan(data["profile"], today)
    last_night = data["sleep"].get(today.isoformat()) or data["sleep"].get((today - timedelta(days=1)).isoformat())
    hours = last_night.get("hours") if last_night else None
    quality = last_night.get("quality") if last_night else None
    streak = compute_streak(data["workouts"], today)
    hard_recent = sum(1 for i in (1, 2, 3)
                      if data["workouts"].get((today - timedelta(days=i)).isoformat(), {}).get("difficulty") == "важке")
    if plan["rest_day"]:
        return ("Відновлення", "Сьогодні день відновлення. Легка ходьба та розтягування — достатньо. Відпочинок теж частина прогресу.")
    if (hours is not None and hours < 6) or (quality is not None and quality <= 2):
        return ("Легко", "Сон був поганий. Зроби тренування легшим: менше підходів, більше відпочинку, без рекордів.")
    if hard_recent >= 2:
        return ("Легко", "Останні дні були важкими. Сьогодні краще помірний темп — тіло відновлюється.")
    if hours is not None and hours >= 7.5 and (quality is None or quality >= 4):
        return ("На повну", "Ти добре відпочив. Можна працювати активніше та спробувати побити особистий рекорд.")
    if streak >= 5:
        return ("Помірно", "Серія вже довга. Не форсуй — зроби якісно за планом і не пропускай відновлення.")
    return ("Помірно", "Тренуйся за планом у комфортному темпі. Якщо самопочуття погіршиться — скороти обсяг.")


# ---------------------------------------------------------------- тренер
def _find_exercise(text):
    """Обирає вправу з найдовшим збігом назви чи псевдоніма (болгар > присід)."""
    best, best_len = None, 0
    for name, item in EXERCISES.items():
        for key in [name.lower()] + item["aliases"]:
            if key in text and len(key) > best_len:
                best, best_len = name, len(key)
    return best


def exercise_card_text(name):
    item = EXERCISES[name]
    return (f"{name}. Працюють: {item['muscles']}.\n\nТехніка:\n"
            + "\n".join(f"{i}. {s}" for i, s in enumerate(item["steps"], 1))
            + f"\n\nТипові помилки: {item['mistakes']}\nЛегший варіант: {item['easier']}")


def coach_answer(question, data, today, context=""):
    """Відповідь офлайн-тренера. Повертає (текст, нова_тема_контексту)."""
    t = (question or "").lower().replace("ё", "е").strip()
    ex = _find_exercise(t)
    item = EXERCISES.get(ex) if ex else None
    follow = context if (not ex and context in EXERCISES) else None
    if not ex and follow:
        ex, item = follow, EXERCISES[follow]

    if ex and any(w in t for w in ["помилк", "неправильно роблю"]) and not any(w in t for w in ["як правильно", "техн"]):
        return f"Типові помилки у вправі «{ex}»: {item['mistakes']}", ex
    if ex and any(w in t for w in ["м'яз", "які м", "що працю", "що качає"]):
        return f"У вправі «{ex}» працюють: {item['muscles']}.", ex
    if ex and any(w in t for w in ["легш", "складно", "не виходить", "замін", "спрост"]):
        return f"Легший варіант для «{ex}»: {item['easier']}", ex
    if ex and any(w in t for w in ["відео", "покаж"]):
        return f"Натисни «Відео» у бібліотеці вправ біля «{ex}» — відкриється пошук навчальних відео.", ex
    if ex and (any(w in t for w in ["як ", "техн", "правильно", "поясн", "розкаж"]) or ex.lower() in t or any(a in t for a in item["aliases"])):
        return exercise_card_text(ex), ex

    if any(x in t for x in ["запамороч", "нудить", "важко дих", "біль у груд", "непритом", "серце"]):
        return ("Зупини тренування й скажи дорослому, якому довіряєш. За сильних, незвичних або тривалих "
                "симптомів потрібна медична допомога. Не продовжуй заняття."), ""
    if any(x in t for x in ["сьогодні тренув", "чи варто", "тренуватися", "тренуватись", "що робити сьогодні", "порад"]):
        label, tip = readiness(data, today)
        return f"Режим на сьогодні: {label}. {tip}", ""
    if any(x in t for x in ["скільки відпоч", "перерва між", "відпочивати між", "відпочинок між"]):
        return ("Між підходами зазвичай 1–2 хвилини. Якщо дихання не відновилося або техніка погіршується — "
                "відпочинь довше. У застосунку таймер відпочинку є на екрані вправи."), ""
    if any(x in t for x in ["кріпат", "болять м", "болить м", "крепат"]):
        return ("Легка м'язова чутливість після незвичного навантаження — це нормально: обери ходьбу, розтягування "
                "та достатньо сну. Не тренуй болючу ділянку інтенсивно. Якщо біль різкий, сильний чи наростає — "
                "припини заняття та звернися до дорослого й лікаря."), ""
    if any(x in t for x in ["болить", "біль", "травм"]):
        return ("Не тренуйся через біль. Зупини вправу, відпочинь і повідом дорослому. Якщо біль сильний, різкий "
                "або не минає — потрібен лікар."), ""
    if any(x in t for x in ["втом", "не висп", "погано спав", "немає сил", "нема сил", "сон"]):
        hrs = avg_sleep(data, today)
        extra = f" Твій середній сон за тиждень: {hrs} год." if hrs else ""
        return ("Сьогодні краще зменшити навантаження або відпочити. Сон і відновлення — частина прогресу. "
                "Не потрібно надолужувати пропущене подвійним тренуванням." + extra), ""
    if any(x in t for x in ["замін", "без обладнання", "немає обладнання"]):
        return ("Назви вправу, яку треба замінити. Для більшості вправ є легший варіант з власною вагою — "
                "відкрий її в бібліотеці вправ."), ""
    if any(x in t for x in ["рекорд", "прогрес"]):
        recs = [f"{k}: {v['best_reps']} повт." if v["best_reps"] else f"{k}: {v['best_sec']} с"
                for k, v in data["records"].items() if v["best_reps"] or v["best_sec"]]
        return ("Твої рекорди:\n" + "\n".join(recs)) if recs else "Рекордів поки немає. Заверши кілька підходів!", ""
    if any(x in t for x in ["привіт", "добрий день", "хай", "вітаю"]):
        return "Привіт! Запитуй про техніку вправ, заміни, відпочинок, сон або самопочуття.", ""
    return ("Я працюю офлайн, тому відповідаю на теми застосунку. Спробуй: «як правильно робити планку», "
            "«які м'язи працюють у віджиманнях», «чи варто сьогодні тренуватися», «болять м'язи»."), context


# ---------------------------------------------------------------- збереження
def fresh_data():
    return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))


def load_data(path):
    data = fresh_data()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                for key, value in loaded.items():
                    if key in ("profile", "workouts", "sleep", "sessions", "records") and isinstance(value, dict):
                        data[key].update(value)
                    elif key in ("badges", "titles", "chat_history", "favorites") and isinstance(value, list):
                        data[key] = value
                    elif key in ("pr_count", "max_comeback", "chat_context", "title_pinned", "onboarded",
                                 "coins", "battle", "camp", "last_seen", "kills", "cards", "api_key"):
                        data[key] = value
            # сумісність зі старою версією: бейджі без дати, записи як список
            if not isinstance(data["records"], dict):
                data["records"] = {}
            data["badges"] = [b for b in data["badges"] if isinstance(b, dict) and b.get("name")]
            if "Новачок" not in data["titles"]:
                data["titles"].insert(0, "Новачок")
        except (OSError, ValueError, TypeError):
            pass
    p = data["profile"]
    p["level"] = level_info(safe_int(p.get("xp")))[0]
    return data


def save_data(data, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------- таймер
class StopClock:
    """Таймер на monotonic-часі: стан зберігається, поки ти переходиш між екранами.
    mode 'up' — секундомір, 'down' — зворотний відлік до target секунд."""

    def __init__(self, mode="up", target=0, now=time.monotonic):
        self.mode, self.target, self._now = mode, int(target), now
        self.base, self.t0 = 0.0, None

    @property
    def running(self):
        return self.t0 is not None

    @property
    def elapsed(self):
        return self.base + ((self._now() - self.t0) if self.t0 is not None else 0.0)

    def start(self):
        if self.t0 is None and not self.finished():
            self.t0 = self._now()

    def pause(self):
        if self.t0 is not None:
            self.base += self._now() - self.t0
            self.t0 = None

    def reset(self, target=None):
        if target is not None:
            self.target = int(target)
        self.base, self.t0 = 0.0, None

    def finished(self):
        return self.mode == "down" and self.elapsed >= self.target

    def display(self):
        if self.mode == "down":
            return max(0, int(math.ceil(self.target - self.elapsed)))
        return int(self.elapsed)


def fmt_clock(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# ------------------------------------------------- коло вправ (по одному підходу)
def next_in_circuit(plan, data, key):
    """Індекс наступної вправи за колом: 1 підхід кожної вправи, потім знову, поки всі підходи не зроблені.
    Повертає None, коли все виконано."""
    best = None
    for i, ex in enumerate(plan["exercises"]):
        d = sets_done_for(data, key, i)
        if d < ex["sets"] and (best is None or d < best[0]):
            best = (d, i)
    return None if best is None else best[1]


def plan_summary(profile, day):
    """Короткий опис плану дня для календаря: назва + вправи з підходами."""
    plan = build_plan(profile, day)
    parts = []
    for ex in plan["exercises"]:
        unit = "с" if ex["kind"] == "time" else "повт."
        parts.append(f"{ex['name']} — {ex['sets']}×{ex['target']} {unit}")
    return plan["name"], parts


# ---------------------------------------------------- карта м'язів
MUSCLE_GROUPS = ["Груди і плечі", "Руки", "Корпус", "Спина", "Ноги", "Сідниці"]
EXERCISE_MUSCLES = {
    "Присідання до стільця": ["Ноги", "Сідниці"],
    "Болгарські присідання": ["Ноги", "Сідниці"],
    "Віджимання від опори": ["Груди і плечі", "Руки"],
    "Ягодичний місток": ["Сідниці", "Спина"],
    "Підйоми на носки": ["Ноги"],
    "Dead bug": ["Корпус"],
    "Bird-dog": ["Корпус", "Спина"],
    "Планка": ["Корпус", "Груди і плечі"],
    "Шадоубоксинг": ["Руки", "Корпус", "Ноги"],
}
MUSCLE_FULL_SETS = 40  # стільки підходів = 100% прокачки групи


def muscle_levels(data):
    """{група: 0..100} за всіма виконаними підходами."""
    counts = {g: 0 for g in MUSCLE_GROUPS}
    for key, sess in data.get("sessions", {}).items():
        plan = build_plan(data["profile"], date.fromisoformat(key))
        for idx, lst in sess.get("sets", {}).items():
            i = safe_int(idx, -1)
            if 0 <= i < len(plan["exercises"]):
                for g in EXERCISE_MUSCLES.get(plan["exercises"][i]["name"], []):
                    counts[g] += len(lst)
    return {g: min(100, round(100 * n / MUSCLE_FULL_SETS)) for g, n in counts.items()}


# ---------------------------------------------- суперники з аніме (рейтинг)
# Значення «очок» вигадані для гри; фрази — власні, не цитати.
RIVALS = [
    # Dragon Ball
    ("Ямча", 60, "Навіть слабкий день — це крок уперед."),
    ("Крилін", 150, "Малий зріст не заважає великому серцю."),
    ("Теншінхан", 220, "Дисципліна важливіша за талант."),
    ("Пікколо", 400, "Терпіння і тренування мудріші за силу."),
    ("Гохан", 800, "Справжня сила приходить, коли є за кого битися."),
    ("Трункс", 900, "Швидкий, як вітер, і впертий."),
    ("Вегета", 2400, "Гордість — паливо, але не забувай про відпочинок."),
    ("Гоку", 3000, "Межа існує, щоб її перерости."),
    ("Віс", 200000, "Спокійний учитель, якого не наздогнати."),
    ("Бірус", 100000, "Бог руйнування теж не любить пропускати обід."),
    ("Зено", 500000, "Верховний володар усіх всесвітів."),
    # One Piece
    ("Усопп", 90, "Хоробрість починається з першого кроку."),
    ("Чоппер", 110, "Маленький лікар із великою мрією."),
    ("Намі", 130, "Розум теж м'яз, а план — це зброя."),
    ("Брук", 160, "Навіть скелет не лінується розтягнутися."),
    ("Френкі", 300, "Суперсила — це коли весь день на ногах!"),
    ("Нико Робін", 350, "Знання плюс витривалість."),
    ("Санджі", 700, "Ноги — це головне, не зупиняйся."),
    ("Зоро", 1100, "Тренуйся втричі більше, ніж інші."),
    ("Луффі", 1800, "Тренування — це пригода, вперед!"),
    # Naruto
    ("Сакура", 280, "Терпіння і точність б'ють грубу силу."),
    ("Хіната", 320, "Тиха сила росте щодня."),
    ("Рок Лі", 750, "Працею можна перевершити геніїв!"),
    ("Саске", 1700, "Гострий, швидкий, без зайвих слів."),
    ("Какаші", 1500, "Досвід робить будь-який підхід чистішим."),
    ("Наруто", 2200, "Не здаюсь, поки є сили на ще один підхід!"),
    ("Мінато (4-й Хокаге)", 3500, "Швидкість вирішує."),
    ("Цунаде (5-й Хокаге)", 3200, "Сила і турбота йдуть разом."),
    ("Хірузен (3-й Хокаге)", 2600, "Мудрість приходить із роками тренувань."),
    ("Хаширама (1-й Хокаге)", 6000, "Сила, що росте, як ліс."),
    ("Тобірама (2-й Хокаге)", 4500, "Точність і швидкість."),
    ("Данзо (6-й Хокаге)", 1900, "Холодний розрахунок."),
    ("Наруто (7-й Хокаге)", 8000, "Мрія стала справою."),
    ("Чіаоцзи", 100, "Маленький, але вперто йде до кінця."),
    ("Яджиробе", 130, "Іноді найкраще — просто вижити і вчитися."),
    ("Майстер Роші", 600, "Тренування починається з довгої прогулянки."),
    ("Радіц", 500, "Брат Гоку, чий шлях почався з ворожнечі."),
    ("Наппа", 900, "Груба сила, яка мало думає."),
    ("Рікум", 2000, "Швидкий і витривалий воїн із Сил Гінью."),
    ("Бардок", 1500, "Батько, що не здається."),
    ("Андроїд 17", 3400, "Енергії вистачить на цілий день."),
    ("Андроїд 18", 3500, "Холодна та рівна, як метроном."),
    ("Андроїд 16", 3600, "Тиха сила, що береже життя."),
    ("Тієн", 1000, "Три ока, три рази старанніше."),
    ("Гінью (капітан)", 1600, "Команда сильніша за одного воїна."),
    ("Фріза (перша форма)", 6000, "Тільки початок."),
    ("Селл (досконалий)", 9000, "Збирає силу з усього, що бачить."),
    ("Маджин Бу", 14000, "Просто не відчуває втоми."),
    ("Кід Бу", 11000, "Швидкий, і грається."),
    ("Бродлі", 17000, "Сила, що росте без кінця."),
    ("Фріза (остання форма)", 20000, "Повна сила, жодного жалю."),
    ("Кефла", 30000, "Об'єднана сила двох воїнів."),
    ("Золота Фріза", 40000, "Після тисячі днів тренувань."),
    ("Чорна Фріза", 60000, "Тренування, що змінило все."),
    ("Топпо", 90000, "Справедливість, яка не поступається."),
    ("Хіт", 70000, "Тихий і точний."),
    ("Джирен", 150000, "Межа, за якою немає межі."),
    ("Гоку Блек", 40000, "Тінь, що копіює все."),
]


_SCALE = 10
_OVERRIDES = {"Ямча": 3000, "Чіаоцзи": 4500, "Крилін": 8000, "Теншінхан": 9000, "Майстер Роші": 7000}
_NEW = [
    ("Містер Сатан", 600, "Звичайна людина з великою вірою в себе."),
    ("Бульма", 500, "Мозок, а не м'язи, веде вперед."),
    ("Чічі", 1800, "Сувора, але справедлива."),
    ("Гоку (хлопчик на башті Камі)", 12000, "Шлях до Бога починається з першого поверху."),
    ("Король Колд", 90000, "Батько тирана."),
    ("Кулер", 110000, "Брат, що не поступається."),
    ("Гоку (Супер Сайян)", 450000, "Злість, що стала силою."),
    ("Вегета (Ультра-Его)", 900000, "Сила, що росте від ударів."),
    ("Гоку (Ультра-Інстинкт)", 1500000, "Тіло діє само."),
]
RIVALS = [(n, _OVERRIDES.get(n, p * _SCALE), q) for n, p, q in RIVALS] + _NEW


def total_score(data):
    """Очки гравця: повторення + 1 очко за кожні 10 с вправ на час."""
    pts = 0
    for sess in data.get("sessions", {}).values():
        for lst in sess.get("sets", {}).values():
            for s in lst:
                pts += s.get("reps", 0) or s.get("sec", 0) // 10
    return pts


def rival_ranking(data, nickname="Ти"):
    table = [(n, pts, q) for n, pts, q in RIVALS] + [(nickname, total_score(data), "")]
    return sorted(table, key=lambda r: -r[1])


# ---------------------------------------------------- бій з монстрами
MONSTERS = [
    ("Слиз", 5), ("Два слизи", 10), ("Гоблін-розвідник", 20), ("Гоблін-лучник", 35),
    ("Гоблін-стрілок", 45), ("Гоблін-мечник", 60), ("Хобгоблін", 90), ("Гоблін-шаман", 110),
    ("Огр (найманий гоблінами)", 160), ("Король гоблінів (бос)", 260),
    ("Скелет-вартовий", 300), ("Орк-берсерк", 360), ("Орк-бос Громорук", 450),
    ("Тролль печер", 550), ("Вовкулак", 650), ("Лич Морбрак (бос)", 800),
    ("Дракон Іскра", 1100), ("Дракон Пітьми (бос)", 1500), ("Титан безодні", 2200),
]
# 100 мідяків = 1 срібний, 100 срібних = 1 золотий, 100 золотих = 1 платиновий
COINS = [("платин.", 1000000), ("зол.", 10000), ("срібл.", 100), ("мідн.", 1)]


def format_coins(cu):
    cu = max(0, safe_int(cu))
    parts = []
    for name, val in COINS:
        n, cu = divmod(cu, val)
        if n:
            parts.append(f"{n} {name}")
    return " ".join(parts) or "0 мідн."


MAX_HIT_REPS = 100


def battle_state(data):
    b = data.setdefault("battle", {"idx": 0, "damage": 0, "defeated": 0})
    b["idx"] = min(safe_int(b.get("idx")), len(MONSTERS) - 1)
    ev = ensure_encounter(data)
    name, hp = MONSTERS[b["idx"]]
    hp = max(1, round(hp * EVENTS[ev][1]))
    return {"name": name, "hp": hp, "damage": b["damage"], "left": max(0, hp - b["damage"]),
            "number": b["idx"] + 1, "total": len(MONSTERS), "defeated": b.get("defeated", 0),
            "event": ev, "event_text": EVENTS[ev][0], "shield": b.get("shield", False)}


def _battle_hit_base(data, reps, rng=None):
    """Удар повтореннями (віджимання тощо). Повертає результат; XP за перемогу = HP/2."""
    reps = safe_int(reps)
    if not 1 <= reps <= MAX_HIT_REPS:
        return {"ok": False}
    st = battle_state(data)
    b = data["battle"]
    res = {"ok": True, "dealt": reps, "killed": False, "xp": 0, "monster": st["name"], "blocked": False}
    if b.get("shield"):
        if reps < SHIELD_BREAK_REPS:
            res.update(dealt=0, blocked=True)
            return res
        b["shield"] = False
    b["damage"] += reps
    if b["damage"] >= st["hp"]:
        res["killed"] = True
        res["xp"] = st["hp"] // 2
        res["coins"] = st["hp"] * 3 + (rng or random).randint(0, st["hp"])
        data["coins"] = safe_int(data.get("coins")) + res["coins"]
        b["defeated"] = b.get("defeated", 0) + 1
        b["damage"] = 0
        for k in ("event", "shield"):
            b.pop(k, None)
        if b["idx"] < len(MONSTERS) - 1:
            b["idx"] += 1
        p = data["profile"]
        p["xp"] = safe_int(p.get("xp")) + res["xp"]
        p["level"] = level_info(p["xp"])[0]
    return res


def rival_window(data, nickname="Ти", above=3, below=2):
    """Частина рейтингу навколо гравця: (місце, ім'я, очки, фраза, це_ти)."""
    table = rival_ranking(data, nickname)
    pos = next(i for i, r in enumerate(table) if r[0] == nickname and r[2] == "")
    lo, hi = max(0, pos - above), min(len(table), pos + below + 1)
    return [(i + 1, *table[i], i == pos) for i in range(lo, hi)], len(table)


# ------------------------------------------------------------- форми (за рівнем)
FORM_LADDERS = {
    "Шлях Гоку": [
        (1, "Хлопчик"), (22, "Хлопчик на башті Камі"), (30, "Кайокен"),
        (40, "Супер Сайян"), (48, "Супер Сайян 2"), (56, "Супер Сайян 3"),
        (64, "Супер Сайян 4"), (72, "Супер Сайян Бог"), (80, "Супер Сайян Блакитний"),
        (88, "Блакитний із Кайоканом"), (96, "Знак Ультра-Інстинкту"), (104, "Досконалий Ультра-Інстинкт"),
        (112, "Ксено Гоку (Супер Сайян 4 із часової лінії)"),
    ],
    "Шлях Гоку Блека": [
        (1, "Тінь"), (76, "Супер Сайян Роузе"),
    ],
    "Шлях Вегети": [
        (1, "Принц-воїн"), (42, "Супер Сайян"), (50, "Супер Сайян 2"),
        (58, "Супер Сайян 3 (з неканону)"), (66, "Супер Сайян 4 (Ксено Вегета)"),
        (74, "Супер Сайян Бог"), (82, "Супер Сайян Блакитний"), (100, "Ультра-Его (сила від ударів)"),
    ],
    "Шлях Фрізи": [
        (1, "Перша форма (у кріслі)"), (34, "Друга форма"), (44, "Третя форма"),
        (54, "Остання форма"), (70, "Форма, яку не бачив навіть брат Кулер"),
        (84, "Золота форма"), (98, "Чорна форма"),
    ],
}
# Тіри сили: від звичайної людини до богів. Реалістично за часом тренувань.
RACES = [
    (1, "Звичайна людина"), (3, "Містер Сатан"), (5, "Мирний воїн"), (8, "Ямча"),
    (12, "Чіаоцзи (левітація й телекінез)"), (16, "Крилін"), (20, "Тієн"),
    (24, "Хлопчик Гоку на башті Камі"), (30, "Пікколо"), (40, "Сайян-воїн"),
    (60, "Еліта всесвіту"), (80, "Ангел-учень"), (100, "Бог руйнування-учень"),
]


def current_form(level, ladder):
    cur, nxt = None, None
    for need, name in FORM_LADDERS[ladder]:
        if level >= need:
            cur = (need, name)
        elif nxt is None:
            nxt = (need, name)
    return cur, nxt


def current_race(level):
    race = RACES[0][1]
    for need, name in RACES:
        if level >= need:
            race = name
    return race


# ----------------------------------------- події бою та табір із нічним нападом
SHIELD_BREAK_REPS = 15
EVENTS = {
    "plain": ("Звичайна зустріч.", 1.0),
    "sneak": ("Ти підкрався непомітно! Здоров'я монстра менше.", 0.7),
    "spotted": ("Монстр тебе помітив! Йому потрібно більше ударів.", 1.3),
    "ambush": ("Засада! Прийшло ще більше ворогів.", 1.5),
    "shield": (f"Монстр підняв щит! Удари менші за {SHIELD_BREAK_REPS} повторень відбиваються, поки щит не пробито.", 1.0),
}


def ensure_encounter(data, rng=None):
    rng = rng or random
    b = data.setdefault("battle", {"idx": 0, "damage": 0, "defeated": 0})
    if "event" not in b:
        r = rng.random()
        ev = "sneak" if r < 0.2 else "spotted" if r < 0.4 else "shield" if r < 0.55 else "ambush" if r < 0.7 else "plain"
        b["event"], b["shield"] = ev, ev == "shield"
    return b["event"]


def camp_start(data, now, tent):
    data["camp"] = {"start": now.isoformat(), "tent": bool(tent)}


def check_night_attack(data, now, rng=None):
    """Викликати при відкритті застосунку. Повертає текст події або None.
    Табір: шанс нападу росте з часом (у наметі ~15%, без нього ~60%).
    Без табору після бою (є урон монстру) і довгої відсутності — 40%."""
    rng = rng or random
    msg = None
    camp = data.get("camp")
    seen = data.get("last_seen")
    p = data["profile"]
    if camp:
        hours = max(0.0, (now - datetime.fromisoformat(camp["start"])).total_seconds() / 3600)
        chance = min(1.0, hours / 8) * (0.15 if camp["tent"] else 0.6)
        if hours >= 1 and rng.random() < chance:
            msg = _lose_xp(p, 0.05 if camp["tent"] else 0.15,
                           "Вночі на табір напала орда гоблінів!")
        elif hours >= 6:
            p["xp"] = safe_int(p.get("xp")) + 5
            p["level"] = level_info(p["xp"])[0]
            msg = "Ти добре виспався: +5 XP."
        data["camp"] = None
    elif seen and data.get("battle", {}).get("damage", 0) > 0:
        gone = (now - datetime.fromisoformat(seen)).total_seconds() / 3600
        if gone >= 8 and rng.random() < 0.4:
            msg = _lose_xp(p, 0.1, "Ти залишив поле бою без табору, і гобліни напали!")
    data["last_seen"] = now.isoformat()
    return msg


def _lose_xp(p, frac, text):
    before = p.get("level", 1)
    loss = int(safe_int(p.get("xp")) * frac)
    p["xp"] = max(0, safe_int(p.get("xp")) - loss)
    p["level"] = level_info(p["xp"])[0]
    extra = f" Рівень знизився до {p['level']}." if p["level"] < before else ""
    return f"{text} Втрачено {loss} XP.{extra}"


# ============================================================ 2.6: титули за монстрів, картки, вікно удару, онлайн-ШІ
BOSS_TITLES = {
    "Слиз": ("Слизолов", "Переможи першого слизя"),
    "Король гоблінів (бос)": ("Володар гоблінів", "Переможи Короля гоблінів"),
    "Орк-бос Громорук": ("Зламав Громорука", "Переможи Громорука"),
    "Лич Морбрак (бос)": ("Погибель лича", "Переможи Лича Морбрака"),
    "Дракон Пітьми (бос)": ("Драконоборець", "Переможи Дракона Пітьми"),
    "Титан безодні": ("Титаноборець", "Переможи Титана безодні"),
}
KILL_TITLES = [("Вбивця монстрів", 10), ("Мисливець на чудовиськ", 50), ("Винищувач", 150)]

for _boss, (_t, _d) in BOSS_TITLES.items():
    TITLES.append((_t, _d, lambda s, b=_boss: b in s["killed"]))
for _t, _n in KILL_TITLES:
    TITLES.append((_t, f"Переможи {_n} монстрів", lambda s, n=_n: s["kills"] >= n))
TITLES.append(("Колекціонер", "Збери 5 карток героїв", lambda s: s["cards"] >= 5))

# (ім'я, рідкість, фраза)
CARDS = [
    ("Гоку", "Легендарна", "Я ще не досяг межі!"),
    ("Вегета", "Епічна", "Гордість сайяна не знає поразки."),
    ("Гохан", "Епічна", "Справжня сила прокидається, коли треба захищати."),
    ("Транкс", "Рідкісна", "Меч і тренування замість слів."),
    ("Готен", "Незвичайна", "Давай тренуватися ще!"),
    ("Бульма", "Рідкісна", "Розум теж зброя."),
    ("Чічі", "Незвичайна", "Спочатку тренування, потім відпочинок!"),
    ("Кріллін", "Незвичайна", "Навіть слабший може стати героєм."),
    ("Пікколо", "Рідкісна", "Дисципліна важливіша за силу."),
    ("Віс", "Міфічна", "Їжа та відпочинок теж частина тренування."),
    ("Бірус", "Міфічна", "Спи, їж і ставай сильнішим."),
    ("Люфі", "Епічна", "Я стану королем піратів!"),
    ("Наруто", "Епічна", "Я не здамся, це мій шлях."),
    ("Слиз-талісман", "Звичайна", "Бульк."),
]
_RARITY_W = {"Звичайна": 50, "Незвичайна": 25, "Рідкісна": 14, "Епічна": 7, "Легендарна": 3, "Міфічна": 1}


def is_boss(name):
    return "(бос)" in name or "Громорук" in name or name == "Титан безодні"


def window_seconds(name):
    """Скільки секунд монстр «відкритий» для удару: 6 с, у босів 5 с."""
    return 5 if is_boss(name) else 6


def window_result(started, now, seconds):
    """Чи вклався удар у вікно. started/now — секунди (time.time())."""
    return 0 <= now - started <= seconds


def card_drop_chance(name):
    return 0.5 if is_boss(name) else 0.1


def roll_card(data, name, rng=None):
    """Шанс картки героя після перемоги. Повертає (ім'я, рідкість, фраза, дублікат) або None."""
    rng = rng or random
    if rng.random() >= card_drop_chance(name):
        return None
    weights = dict(_RARITY_W)
    if is_boss(name):
        for r in ("Звичайна", "Незвичайна"):
            weights[r] = 0
    pool = [c for c in CARDS if weights[c[1]] > 0]
    card = rng.choices(pool, weights=[weights[c[1]] for c in pool])[0]
    have = data.setdefault("cards", [])
    dup = card[0] in have
    if not dup:
        have.append(card[0])
    return (*card, dup)


def battle_hit(data, reps, rng=None, in_window=True):
    """Удар. Поза вікном монстр ухиляється: урон вдвічі менший. Після перемоги: kills, титули, картка."""
    reps = safe_int(reps)
    base_reps = reps if in_window else max(1, reps // 2)
    if not 1 <= reps <= MAX_HIT_REPS:
        return {"ok": False}
    res = _battle_hit_base(data, base_reps, rng)
    res["late"] = not in_window
    res["new"], res["card"] = [], None
    if res.get("killed"):
        kills = data.setdefault("kills", {})
        kills[res["monster"]] = safe_int(kills.get(res["monster"])) + 1
        res["card"] = roll_card(data, res["monster"], rng)
        res["new"] = check_achievements(data, date.today())
        data["profile"]["title"] = pick_title(data)
    return res


# ---- онлайн-тренер: власний ключ користувача, запит у окремому потоці з головного файлу
AI_MODEL = "claude-haiku-5-5"
AI_URL = "https://api.anthropic.com/v1/messages"


def ai_system_prompt(data, today):
    p = data["profile"]
    return ("Ти ШІ-тренер у фітнес-RPG. Відповідай українською, коротко (до 6 речень), безпечно, без діагнозів; "
            "при болю радь зупинитися й звернутися до лікаря. Дані гравця: "
            f"рівень {p.get('level')}, досвід {p.get('experience')}, важкість {p.get('intensity')}, "
            f"серія {compute_streak(data['workouts'], today)} дн.")


def ai_messages(data, question, limit=6):
    msgs = []
    for e in data.get("chat_history", [])[-limit:]:
        if e.get("q") and e.get("a"):
            msgs += [{"role": "user", "content": e["q"]}, {"role": "assistant", "content": e["a"]}]
    return msgs + [{"role": "user", "content": question}]


def ai_request(key, data, question, today, timeout=20):
    """Викликає API. Кидає виняток при помилці мережі/ключа; виклик ловить його й іде в офлайн-тренера."""
    import urllib.request
    body = json.dumps({"model": AI_MODEL, "max_tokens": 600,
                       "system": ai_system_prompt(data, today),
                       "messages": ai_messages(data, question)}).encode("utf-8")
    req = urllib.request.Request(AI_URL, data=body, headers={
        "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    ctx = None
    try:  # на Android немає системних сертифікатів для Python, беремо certifi
        import ssl, certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        out = json.loads(r.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text").strip()
