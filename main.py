import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from telebot import TeleBot
TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(TOKEN)

# === Команда /start ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋\n"
        "Я бот, который будет напоминать тебе о занятиях.\n\n"
        "Отправь расписание на неделю в формате:\n\n"
        "Понедельник:\n"
        "08:00 Математика 101\n"
        "09:40 Физика 203\n\n"
        "Вторник:\n"
        "08:00 Английский 202\n\n"
        "Чтобы удалить старое расписание — введи /delete"
    )

# === Команда /delete ===
@bot.message_handler(commands=['delete'])
def delete_schedule(message):
    path = f"data/{message.chat.id}.json"
    if os.path.exists(path):
        os.remove(path)
        bot.send_message(message.chat.id, "🗑 Старое расписание удалено. Можешь отправить новое!")
    else:
        bot.send_message(message.chat.id, "У тебя ещё нет сохранённого расписания.")

# === Обработка текста (расписания) ===
@bot.message_handler(func=lambda m: True)
def handle_schedule(message):
    text = message.text.strip()
    if not text:
        return
    schedule = parse_schedule(text)
    if schedule:
        save_schedule(message.chat.id, schedule)
        bot.send_message(message.chat.id, "✅ Расписание сохранено!")
    else:
        bot.send_message(message.chat.id, "Не смог понять формат. Попробуй снова.")

# === Парсер расписания ===
def parse_schedule(text):
    days = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
    schedule = {}
    current_day = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Проверяем день
        day = next((d for d in days if d in line.lower()), None)
        if day:
            current_day = day.capitalize()
            schedule[current_day] = []
        elif current_day:
            # Пример строки: "08:00 Математика 101"
            match = re.match(r"(\d{1,2}:\d{2})\s+(.+)\s+(\d+)", line)
            if match:
                time, subject, room = match.groups()
                schedule[current_day].append({
                    "time": time,
                    "subject": subject.strip(),
                    "room": room.strip()
                })
    return schedule if schedule else None

# === Сохранение расписания ===
def save_schedule(user_id, schedule):
    os.makedirs("data", exist_ok=True)
    path = f"data/{user_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def load_schedule(user_id):
    path = f"data/{user_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

##
# ======== Блок уведомлений =========
def notification_worker():
    days_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }

    notified = {}  # словарь для предотвращения повторной отправки

    while True:
        now = datetime.now()
        day_name = days_map[now.weekday()]

        for filename in os.listdir("data"):
            if not filename.endswith(".json"):
                continue
            user_id = int(filename.split(".")[0])
            schedule = load_schedule(user_id)
            today_schedule = schedule.get(day_name, [])

            if not today_schedule:
                continue

            # Сортируем пары по времени
            today_schedule_sorted = sorted(
                today_schedule,
                key=lambda x: datetime.strptime(x["time"], "%H:%M")
            )

            # ==== Уведомление за 1 час только для первой пары ====
            first_lesson = today_schedule_sorted[0]
            lesson_time = datetime.strptime(first_lesson["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            key_60 = f"{user_id}-{lesson_time}-60"
            if 59 <= (lesson_time - now).total_seconds() / 60 <= 60 and key_60 not in notified:
                bot.send_message(
                    user_id,
                    f"⏰ Через 1 час: {first_lesson['subject']} в аудитории {first_lesson['room']} ({first_lesson['time']})"
                )
                notified[key_60] = True

            # ==== Уведомления за 5 минут для всех пар ====
            for lesson in today_schedule_sorted:
                lesson_time_5 = datetime.strptime(lesson["time"], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                key_5 = f"{user_id}-{lesson_time_5}-5"
                if 4 <= (lesson_time_5 - now).total_seconds() / 60 <= 5 and key_5 not in notified:
                    bot.send_message(
                        user_id,
                        f"⏰ Через 5 минут: {lesson['subject']} в аудитории {lesson['room']} ({lesson['time']})"
                    )
                    notified[key_5] = True

        # Проверяем каждую минуту
        time.sleep(60)
#

# ======== Запуск уведомлений в отдельном потоке =========
notification_thread = threading.Thread(target=notification_worker, daemon=True)
notification_thread.start()
#

print("Бот запущен!")
bot.polling()
