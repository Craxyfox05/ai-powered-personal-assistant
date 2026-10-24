import os
import tempfile
import unittest
from datetime import datetime, timedelta

from ai_assistant import (Assistant, MusicService, NewsService, Reminder, Service, ServiceError,
                          SmartHomeService, Task, TaskStatus, User, WeatherService)
from ai_assistant.parsing import parse_when

NOW = datetime(2026, 10, 24, 10, 0)


def make_assistant(**kw):
    user = User("u1", "Aditya", "a@b.com")
    services = kw.pop("services", [SmartHomeService(), WeatherService(), NewsService(), MusicService()])
    return Assistant(user, services=services, clock=lambda: NOW, output_fn=lambda s: None, **kw)


class ReminderTests(unittest.TestCase):          # QA example: Reminder tested WITHOUT the Assistant
    def test_one_time(self):
        r = Reminder("x", NOW + timedelta(minutes=5)); r.schedule()
        self.assertIsNone(r.trigger(NOW))
        self.assertEqual(r.trigger(NOW + timedelta(minutes=6)), "x")
        self.assertFalse(r.is_active)

    def test_repeated_moves_forward(self):
        r = Reminder("x", NOW, True); r.schedule()
        self.assertEqual(r.trigger(NOW), "x")
        self.assertTrue(r.is_active)
        self.assertEqual(r.reminder_time, NOW + timedelta(days=1))

    def test_cancel(self):
        r = Reminder("x", NOW); r.schedule(); r.cancel()
        self.assertFalse(r.is_due(NOW))


class TaskUserTests(unittest.TestCase):
    def test_lifecycle(self):
        u = User("u", "A", "a@b.com")
        t = u.add_task(Task.create("study"))
        self.assertEqual(t.task_id, 1)
        t.update(title="study docker")
        t.mark_complete()
        self.assertIs(t.status, TaskStatus.DONE)
        t.delete()
        self.assertEqual(u.tasks, [])

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            Task.create("  ")

    def test_login_and_encapsulation(self):
        u = User("u", "A", "a@b.com", password="secret")
        self.assertTrue(u.login("secret")); self.assertFalse(u.login("nope"))
        u.preferences["city"] = "X"                      # modifying the copy must not change the user
        self.assertEqual(u.preferences, {})

    def test_bad_email(self):
        with self.assertRaises(ValueError):
            User("u", "A", "not-an-email")

    def test_completing_cancels_reminder(self):
        t = Task.create("x"); t.set_reminder(NOW); t.mark_complete()
        self.assertFalse(t.reminder.is_active)


class ParsingTests(unittest.TestCase):
    def test_in_minutes(self):
        when, rep, msg = parse_when("call mom in 10 minutes", NOW)
        self.assertEqual(when, NOW + timedelta(minutes=10)); self.assertFalse(rep); self.assertEqual(msg, "call mom")

    def test_at_pm_daily(self):
        when, rep, msg = parse_when("drink water at 6pm daily", NOW)
        self.assertEqual(when, NOW.replace(hour=18, minute=0)); self.assertTrue(rep); self.assertEqual(msg, "drink water")

    def test_past_time_goes_to_tomorrow(self):
        when, _, _ = parse_when("gym at 7am", NOW)
        self.assertEqual(when, datetime(2026, 10, 25, 7, 0))

    def test_tomorrow_default(self):
        when, _, msg = parse_when("submit report tomorrow", NOW)
        self.assertEqual(when, datetime(2026, 10, 25, 9, 0)); self.assertEqual(msg, "submit report")


class ServiceTests(unittest.TestCase):
    def test_polymorphism(self):
        for s, q in [(WeatherService(), "weather in pune"), (NewsService(), "news"), (MusicService(), "play jazz"),
                     (SmartHomeService(), "turn on the light")]:
            self.assertIsInstance(s, Service)
            s.request(q)
            self.assertTrue(s.get_result())

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            Service()

    def test_mock_provider_failure_is_friendly(self):
        def broken(city): raise ConnectionError("offline")
        with self.assertRaises(ServiceError):
            WeatherService(broken).request("weather")

    def test_unknown_device(self):
        with self.assertRaises(ServiceError):
            SmartHomeService().request("turn on the spaceship")


class AssistantTests(unittest.TestCase):
    def test_task_flow(self):
        a = make_assistant()
        self.assertIn("Task added", a.process_command("add task buy milk due tomorrow at 5pm"))
        self.assertIn("buy milk", a.process_command("list tasks"))
        self.assertIn("done", a.process_command("done 1").lower())
        self.assertEqual(a.get_response(), "Marked as done: buy milk ✅")

    def test_reminder_triggers(self):
        a = make_assistant()
        a.process_command("remind me to stretch in 5 minutes")
        self.assertEqual(a.check_reminders(NOW + timedelta(minutes=1)), [])
        self.assertEqual(a.check_reminders(NOW + timedelta(minutes=6)), ["stretch"])
        self.assertEqual(a.check_reminders(NOW + timedelta(minutes=7)), [])

    def test_routes_to_services(self):
        a = make_assistant()
        self.assertTrue(a.process_command("hey nova, weather in Surat").startswith("Weather in Surat"))
        self.assertIn("Now playing", a.process_command("play jazz"))
        self.assertIn("ON", a.process_command("turn on the light"))
        self.assertIn("headlines", a.process_command("news"))

    def test_new_service_without_changing_assistant(self):
        class JokeService(Service):
            keywords = ("joke",)
            def _fetch(self, query, context): return "Why do programmers prefer dark mode? Light attracts bugs."
        a = make_assistant(services=[JokeService()])
        self.assertIn("dark mode", a.process_command("tell me a joke"))

    def test_personalization(self):
        a = make_assistant()
        a.process_command("set city to Pune")
        self.assertTrue(a.process_command("what's the weather").startswith("Weather in Pune"))
        a.process_command("set units to f")
        self.assertIn("°F", a.process_command("weather"))

    def test_unknown_and_errors(self):
        a = make_assistant()
        self.assertIn("didn't get that", a.process_command("blah blah"))
        self.assertIn("Sorry", a.process_command("turn on the spaceship"))
        self.assertIn("couldn't find", a.process_command("done 99"))

    def test_history_and_persistence(self):
        a = make_assistant()
        a.process_command("add task one"); a.process_command("remind me to sleep in 2 hours")
        self.assertEqual(len(a.history), 2)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data.json")
            a.save(p)
            b = make_assistant(); b.load(p)
            self.assertEqual([t.title for t in b.user.tasks], ["one", "sleep"])
            self.assertEqual(len(b.history), 2)
            self.assertTrue(b.user.tasks[1].reminder.is_active)
            b.process_command("add task two")
            self.assertEqual(b.user.tasks[-1].task_id, 3)

    def test_register_rejects_non_service(self):
        with self.assertRaises(TypeError):
            make_assistant().register_service(object())


if __name__ == "__main__":
    unittest.main()
