"""Run:  python main.py            (interactive)
        python main.py --demo      (scripted demo)
        python main.py --live      (real weather via Open-Meteo, needs internet)
        python main.py --voice     (speak replies if `pip install pyttsx3`)"""
import argparse
import os

from ai_assistant import Assistant, MusicService, NewsService, SmartHomeService, User, WeatherService
from ai_assistant.services import open_meteo_provider, offline_weather

DEMO = ["hey nova, hello", "add task submit OOSD assignment due tomorrow at 5pm", "add task revise Docker basics",
        "list tasks", "remind me to drink water in 1 minute", "done 2", "weather in Surat", "news about tech",
        "play jazz", "pause", "turn on the light", "devices", "set units to f", "weather in Surat",
        "what time is it", "history", "play something for me please"]


def build_assistant(args) -> Assistant:
    user = User("u1", args.name, "user@example.com")
    provider = open_meteo_provider if args.live else offline_weather
    services = [SmartHomeService(), WeatherService(provider), NewsService(), MusicService()]
    tts = None
    if args.voice:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            tts = lambda text: (engine.say(text), engine.runAndWait())
        except ImportError:
            print("pyttsx3 not installed -> running without voice")
    return Assistant(user, services=services, tts=tts)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="Friend")
    p.add_argument("--data", default="assistant_data.json")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--live", action="store_true")
    p.add_argument("--voice", action="store_true")
    args = p.parse_args()
    bot = build_assistant(args)
    if args.demo:
        for line in DEMO:
            print(f"{args.name}> {line}")
            bot.speak(bot.process_command(line))
        return
    if os.path.exists(args.data):
        bot.load(args.data)
    bot.run()
    bot.save(args.data)


if __name__ == "__main__":
    main()
