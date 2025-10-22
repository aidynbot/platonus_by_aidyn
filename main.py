import json
import os
import re
from datetime import datetime
from telebot import TeleBot

TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(TOKEN)

# === Команды /start и /delete для локального теста ===
# В GitHub Actions интерактивность не работает, можно оставить для локального запуска
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

@bot.message_handler(commands=['delete'])
def delete_schedule(message):
    path = f"data/{message.chat.id}.json"
    if os.path.exists(path):
        os.remove(path)
        bot.send_message(message.chat.id, "🗑 Старое расписание удалено. Можешь отправить новое!")
    else:
        bot.send_message(message.chat.id, "У тебя ещё нет сохранённого расписания.")

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
        day = next((d for d in days if d in line.lower()), None)
        if day:
            current_day = day.capitalize()
            schedule[current_day] = []
        elif current_day:
            match = re.match(r"(\d{1,2}:\d{2})\s+(.+)\s+(\d+)", line)
            if match:
                time_str, subject, room = match.groups()
                schedule[current_day].append({
                    "time": time_str,
                    "subject": subject.strip(),
                    "room": room.strip()
                })
    return schedule if schedule else None

# === Сохранение/загрузка расписания ===
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

# === Функция уведомлений (для GitHub Actions) ===
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

        for lesson in today_schedule_sorted:
            lesson_time = datetime.strptime(lesson["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            diff_minutes = (lesson_time - now).total_seconds() / 60

            # Уведомление за 1 час
            if 55 <= diff_minutes <= 60:
                bot.send_message(
                    user_id,
                    f"⏰ Через 1 час: {lesson['subject']} в аудитории {lesson['room']} ({lesson['time']})"
                )

            # Уведомление за 5 минут
            if 4 <= diff_minutes <= 6:
                bot.send_message(
                    user_id,
                    f"⏰ Через 5 минут: {lesson['subject']} в аудитории {lesson['room']} ({lesson['time']})"
                )

# === Запуск уведомлений один раз ===
if __name__ == "__main__":
    notification_worker()
    print("GitHub Actions run finished.")
