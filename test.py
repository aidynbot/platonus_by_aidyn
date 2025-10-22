import json
import datetime
import os
import time
import requests

TOKEN = "8404877972:AAH_qPvWOXupQb_-XphO_T6BPOt3Qd4uZLc"
CHAT_ID = "1088421327"  # можно временно указать вручную
JSON_FILE = "schedule.json"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def load_schedule():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def check_schedule():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    weekday = now.strftime("%A").lower()

    data = load_schedule()
    for chat_id, schedule in data.items():
        if weekday in schedule:
            for pair in schedule[weekday]:
                # время за 5 минут до начала
                before_5 = (datetime.datetime.strptime(pair["time"], "%H:%M") - datetime.timedelta(minutes=5)).strftime("%H:%M")
                # время за 1 час до первой пары
                first_time = schedule[weekday][0]["time"]
                before_1h = (datetime.datetime.strptime(first_time, "%H:%M") - datetime.timedelta(hours=1)).strftime("%H:%M")

                if current_time == before_5:
                    send_message(chat_id, f"⏰ Через 5 минут занятие: {pair['subject']} ({pair['room']})")

                if current_time == before_1h:
                    send_message(chat_id, f"📅 Через час начнётся первая пара: {pair['subject']} ({pair['room']})")

def main():
    print("✅ Бот запущен. Проверка расписания каждую минуту...")
    while True:
        check_schedule()
        time.sleep(60)  # ждём 1 минуту

if __name__ == "__main__":
    main()
