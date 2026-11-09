import os, tempfile, unittest
from datetime import date, timedelta
import logic as L

MON = date(2026, 11, 9)   # понеділок
class T(unittest.TestCase):
    def setUp(self): self.d = L.fresh_data()

    def test_plan_scaling(self):
        p = L.build_plan({"experience": "Початківець", "intensity": "Легке"}, MON)
        self.assertEqual(p["exercises"][0]["sets"], 2)
        p2 = L.build_plan({"experience": "Досвідчений", "intensity": "Важке"}, MON)
        self.assertEqual(p2["exercises"][0]["sets"], 4)
        self.assertGreater(p2["exercises"][0]["target"], p["exercises"][0]["target"])
        sat = L.build_plan({"experience": "Середній", "intensity": "Середнє"}, date(2026, 11, 14))
        self.assertIn("Болгарські присідання", [e["name"] for e in sat["exercises"]])
        wed = L.build_plan({}, date(2026, 11, 11))
        self.assertTrue(wed["rest_day"])
        for wd in range(7):
            L.build_plan(self.d["profile"], MON + timedelta(days=wd))

    def test_xp_only_for_sets_and_no_farming(self):
        plan = L.build_plan(self.d["profile"], MON); key = MON.isoformat()
        ex = plan["exercises"][0]
        for _ in range(ex["sets"] + 3):
            L.record_set(self.d, key, 0, ex, 10, 30)
        self.assertEqual(self.d["profile"]["xp"], L.XP_PER_SET * ex["sets"])
        self.assertEqual(L.sets_done(self.d, key), ex["sets"])

    def test_finish_requires_sets(self):
        plan = L.build_plan(self.d["profile"], MON)
        self.assertFalse(L.finish_workout(self.d, plan, MON)["ok"])

    def test_full_workout_bonus_once(self):
        plan = L.build_plan(self.d["profile"], MON); key = MON.isoformat()
        for i, ex in enumerate(plan["exercises"]):
            for _ in range(ex["sets"]): L.record_set(self.d, key, i, ex, 10, 20)
        r = L.finish_workout(self.d, plan, MON)
        self.assertTrue(r["full"]); self.assertEqual(r["bonus"], L.XP_FINISH_BONUS)
        xp = self.d["profile"]["xp"]
        r2 = L.finish_workout(self.d, plan, MON)
        self.assertEqual(r2["bonus"], 0); self.assertEqual(self.d["profile"]["xp"], xp)
        self.assertIn("Перший крок", [b["name"] for b in self.d["badges"]])

    def test_partial(self):
        plan = L.build_plan(self.d["profile"], MON); key = MON.isoformat()
        L.record_set(self.d, key, 0, plan["exercises"][0], 10, 20)
        r = L.finish_workout(self.d, plan, MON)
        self.assertTrue(r["ok"]); self.assertFalse(r["full"]); self.assertEqual(r["bonus"], 0)
        self.assertTrue(self.d["workouts"][key]["partial"])

    def test_pr(self):
        ex = {"name": "Планка", "kind": "time", "sets": 5, "target": 20, "rest": 60}
        k = MON.isoformat()
        self.assertFalse(L.record_set(self.d, k, 0, ex, 0, 20)["pr"])   # перший запис не рекорд
        self.assertTrue(L.record_set(self.d, k, 0, ex, 0, 30)["pr"])
        self.assertEqual(self.d["records"]["Планка"]["best_sec"], 30)

    def test_streak_rest_days(self):
        w = {}
        for off in (0, 1, 2, 3):  # пн, нд(відпочинок, не позначено), сб, пт
            pass
        w["2026-11-09"] = {"done": True}; w["2026-11-07"] = {"done": True}; w["2026-11-06"] = {"done": True}
        # нд 08.11 — відпочинок і не порушує серію
        self.assertEqual(L.compute_streak(w, MON), 3)
        w2 = {"2026-11-09": {"done": True}, "2026-11-06": {"done": True}}  # сб 07 пропущено
        self.assertEqual(L.compute_streak(w2, MON), 1)
        # сьогодні ще не зроблено — серія не рветься
        self.assertEqual(L.compute_streak({"2026-11-07": {"done": True}}, date(2026, 11, 8)), 1)

    def test_comeback_titles(self):
        plan = L.build_plan(self.d["profile"], MON); key = MON.isoformat()
        self.d["workouts"]["2026-11-02"] = {"done": True}
        L.record_set(self.d, key, 0, plan["exercises"][0], 10, 20)
        r = L.finish_workout(self.d, plan, MON)
        self.assertEqual(r["comeback"], 4)
        self.assertIn("Прокрастинатор", self.d["titles"])
        self.assertNotEqual(self.d["profile"]["title"], "Прокрастинатор")

    def test_levels(self):
        self.assertEqual(L.level_info(0), (1, 0, 100))
        self.assertEqual(L.level_info(100), (2, 0, 120))
        self.assertEqual(L.level_info(219)[0], 2)
        self.assertEqual(L.level_info(220)[0], 3)

    def test_sleep(self):
        self.assertEqual(L.sleep_hours("22:30", "07:00"), 8.5)
        self.assertEqual(L.sleep_hours("23.45", "6:15"), 6.5)
        self.assertIsNone(L.sleep_hours("abc", "07:00"))
        self.assertIsNone(L.parse_time("25:00"))

    def test_coach(self):
        a, ctx = L.coach_answer("Як правильно робити болгарські присідання?", self.d, MON)
        self.assertIn("Техніка", a); self.assertEqual(ctx, "Болгарські присідання")
        a2, _ = L.coach_answer("а які типові помилки?", self.d, MON, ctx)
        self.assertIn("Типові помилки", a2)
        a3, _ = L.coach_answer("які м'язи працюють у віджиманнях", self.d, MON)
        self.assertIn("груди", a3)
        a4, _ = L.coach_answer("чи варто сьогодні тренуватися?", self.d, MON)
        self.assertIn("Режим", a4)
        a5, _ = L.coach_answer("запаморочення", self.d, MON)
        self.assertIn("Зупини", a5)
        for q in ["", "ффф", "привіт", "болять м'язи", "скільки відпочивати між підходами", "мої рекорди"]:
            L.coach_answer(q, self.d, MON)

    def test_readiness(self):
        self.d["sleep"][MON.isoformat()] = {"hours": 5, "quality": 2}
        self.assertEqual(L.readiness(self.d, MON)[0], "Легко")
        self.d["sleep"][MON.isoformat()] = {"hours": 8.5, "quality": 5}
        self.assertEqual(L.readiness(self.d, MON)[0], "На повну")
        self.assertEqual(L.readiness(self.d, date(2026, 11, 11))[0], "Відновлення")

    def test_save_load_and_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "x", "user_data.json")
            self.d["profile"]["nickname"] = "Тест"; self.d["profile"]["xp"] = 250
            L.save_data(self.d, path)
            d2 = L.load_data(path)
            self.assertEqual(d2["profile"]["nickname"], "Тест"); self.assertEqual(d2["profile"]["level"], 3)
            open(path, "w", encoding="utf-8").write('{"profile":{"xp":30},"records":[{"date":"x"}],"badges":[{"name":"A","rarity":"Рідкісний"}],"streak":3}')
            d3 = L.load_data(path)
            self.assertEqual(d3["records"], {}); self.assertEqual(d3["profile"]["xp"], 30)
            open(path, "w").write("{битий json")
            self.assertEqual(L.load_data(path)["profile"]["nickname"], "Гравець")

class C(unittest.TestCase):
    def test_clock(self):
        t = [100.0]
        up = L.StopClock("up", now=lambda: t[0]); up.start(); t[0] += 5
        self.assertEqual(up.display(), 5); up.pause(); t[0] += 50
        self.assertEqual(up.display(), 5); up.start(); t[0] += 2.5
        self.assertEqual(up.display(), 7); up.reset(); self.assertEqual(up.display(), 0)
        dn = L.StopClock("down", 10, now=lambda: t[0]); dn.start(); t[0] += 3.2
        self.assertEqual(dn.display(), 7); self.assertFalse(dn.finished())
        t[0] += 10; self.assertTrue(dn.finished()); self.assertEqual(dn.display(), 0)
        dn.pause(); dn.start(); self.assertFalse(dn.running)   # завершений не стартує знову
        self.assertEqual(L.fmt_clock(75), "01:15")


class TestCircuit(unittest.TestCase):
    def test_circuit_rotates_and_finishes(self):
        d = L.fresh_data(); d["profile"]["intensity"] = "Важке"
        day = date(2026, 11, 9); key = day.isoformat()
        plan = L.build_plan(d["profile"], day); n = len(plan["exercises"])
        order = []
        while True:
            i = L.next_in_circuit(plan, d, key)
            if i is None: break
            order.append(i)
            L.record_set(d, key, i, plan["exercises"][i], 10, 30)
        self.assertEqual(order[:n], list(range(n)))
        self.assertEqual(len(order), n * 4)

    def test_muscles_and_rivals(self):
        d = L.fresh_data(); day = date(2026, 11, 9); key = day.isoformat()
        plan = L.build_plan(d["profile"], day)
        L.record_set(d, key, 1, plan["exercises"][1], 10, 30)
        self.assertGreater(L.muscle_levels(d)["Груди і плечі"], 0)
        self.assertEqual(L.total_score(d), 10)
        self.assertEqual(len(L.rival_ranking(d)), len(L.RIVALS) + 1)

    def test_plan_summary(self):
        name, parts = L.plan_summary(L.fresh_data()["profile"], date(2026, 11, 9))
        self.assertTrue(name and parts)


class TestBattle(unittest.TestCase):
    def test_battle(self):
        d = L.fresh_data()
        d["battle"] = {"idx": 0, "damage": 0, "defeated": 0, "event": "plain", "shield": False}
        self.assertFalse(L.battle_hit(d, 0)["ok"])
        self.assertFalse(L.battle_hit(d, 999)["ok"])
        r = L.battle_hit(d, 20)
        self.assertTrue(r["killed"])
        self.assertEqual(d["profile"]["xp"], 2)
        self.assertGreater(d["coins"], 0)
        self.assertEqual(L.battle_state(d)["number"], 2)

    def test_rival_window(self):
        rows, n = L.rival_window(L.fresh_data())
        self.assertTrue(any(r[-1] for r in rows))
        self.assertGreater(n, 30)


class TestEvents(unittest.TestCase):
    def test_shield_blocks_small_hits(self):
        d = L.fresh_data()
        d["battle"] = {"idx": 0, "damage": 0, "defeated": 0, "event": "shield", "shield": True}
        self.assertTrue(L.battle_hit(d, 5)["blocked"])
        self.assertEqual(d["battle"]["damage"], 0)
        self.assertFalse(L.battle_hit(d, 15)["blocked"])
        self.assertGreater(d["battle"]["damage"] + d["battle"]["idx"], 0)

    def test_camp_attack_loses_xp(self):
        import random
        from datetime import datetime, timedelta
        d = L.fresh_data(); d["profile"]["xp"] = 1000
        now = datetime(2026, 11, 9, 22, 0)
        L.camp_start(d, now, tent=False)
        class Always: 
            def random(self): return 0.0
        msg = L.check_night_attack(d, now + timedelta(hours=8), Always())
        self.assertIn("Втрачено", msg)
        self.assertEqual(d["profile"]["xp"], 850)
        self.assertIsNone(d["camp"])

    def test_forms(self):
        cur, nxt = L.current_form(4, "Шлях Гоку")
        self.assertEqual(cur[1], "Хлопчик")
        cur, nxt = L.current_form(40, "Шлях Гоку")
        self.assertEqual(cur[1], "Супер Сайян")
        self.assertEqual(L.format_coins(10101), "1 зол. 1 срібл. 1 мідн.")
        self.assertEqual(L.current_race(1), "Звичайна людина")


class T26(unittest.TestCase):
    def setUp(self): self.d = L.fresh_data()

    def test_persistence_of_battle_and_coins(self):
        import random
        self.d["battle"] = {"idx": 3, "damage": 4, "defeated": 3}; self.d["coins"] = 500
        self.d["kills"] = {"Слиз": 1}; self.d["cards"] = ["Гоку"]
        p = os.path.join(tempfile.mkdtemp(), "s.json"); L.save_data(self.d, p)
        e = L.load_data(p)
        self.assertEqual(e["coins"], 500); self.assertEqual(e["battle"]["idx"], 3)
        self.assertEqual(e["kills"], {"Слиз": 1}); self.assertEqual(e["cards"], ["Гоку"])

    def test_first_kill_gives_title(self):
        import random
        self.d["battle"] = {"idx": 0, "damage": 0, "defeated": 0, "event": "plain", "shield": False}
        res = L.battle_hit(self.d, 5, rng=random.Random(1))
        self.assertTrue(res["killed"])
        self.assertIn("Слизолов", self.d["titles"])
        self.assertEqual(self.d["kills"]["Слиз"], 1)

    def test_window_halves_damage(self):
        self.d["battle"] = {"idx": 5, "damage": 0, "defeated": 0, "event": "plain", "shield": False}
        res = L.battle_hit(self.d, 4, in_window=False)
        self.assertEqual(res["dealt"], 2); self.assertTrue(res["late"])
        self.assertTrue(L.window_result(100, 105.5, 6)); self.assertFalse(L.window_result(100, 107, 6))
        self.assertEqual(L.window_seconds("Слиз"), 6); self.assertEqual(L.window_seconds("Лич Морбрак (бос)"), 5)

    def test_boss_title_and_cards(self):
        import random
        self.d["kills"] = {"Король гоблінів (бос)": 1}
        L.check_achievements(self.d, MON)
        self.assertIn("Володар гоблінів", self.d["titles"])
        class Always(random.Random):
            def random(self): return 0.0
        got = L.roll_card(self.d, "Дракон Пітьми (бос)", Always(2))
        self.assertIsNotNone(got); self.assertNotIn(got[1], ("Звичайна", "Незвичайна"))
        self.assertIn(got[0], self.d["cards"])

    def test_ai_message_building(self):
        self.d["chat_history"] = [{"q": "привіт", "a": "вітаю"}]
        m = L.ai_messages(self.d, "як відпочивати?")
        self.assertEqual(m[-1]["role"], "user"); self.assertEqual(len(m), 3)
        self.assertIn("рівень", L.ai_system_prompt(self.d, MON))


if __name__ == "__main__":
    unittest.main(verbosity=1)
