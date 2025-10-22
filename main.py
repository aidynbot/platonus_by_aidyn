import json
import datetime
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # временно можно указать прямо здесь

JSON_FILE = "schedule.json"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def load_schedule():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    weekday = now.strftime("%A").lower()

    data = load_schedule()
    for chat_id, schedule in data.items():
        if weekday in schedule:
            for pair in schedule[weekday]:
                # за 5 минут до начала
                t = (datetime.datetime.strptime(pair["time"], "%H:%M") - datetime.timedelta(minutes=5)).strftime("%H:%M")
                if current_time == t:
                    send_message(chat_id, f"⏰ Через 5 минут занятие: {pair['subject']} ({pair['room']})")
                # за 1 час до первой пары
                first_time = schedule[weekday][0]["time"]
                t1h = (datetime.datetime.strptime(first_time, "%H:%M") - datetime.timedelta(hours=1)).strftime("%H:%M")
                if current_time == t1h:
                    send_message(chat_id, f"📅 Через час начнётся первая пара: {pair['subject']} ({pair['room']})")

if __name__ == "__main__":
    main()
