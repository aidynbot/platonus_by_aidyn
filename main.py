import json
import os
import re
from datetime import datetime
from telebot import TeleBot

TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(TOKEN)

# === Команды /start и /delete для локального теста ===
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
        
        # Проверяем, является ли строка названием дня
        day = next((d for d in days if line.lower().startswith(d)), None)
        if day:
            current_day = day.capitalize()
            schedule[current_day] = []
        elif current_day:
            # Гибкий парсер: номер аудитории опционален
            match = re.match(r"(\d{1,2}:\d{2})\s+(.+?)(?:\s+([A-Za-zА-Яа-я0-9,\s]+))?$", line)
            if match:
                time_str = match.group(1)
                subject = match.group(2).strip()
                room = match.group(3).strip() if match.group(3) else "Не указана"
                
                # Валидация времени
                try:
                    datetime.strptime(time_str, "%H:%M")
                    schedule[current_day].append({
                        "time": time_str,
                        "subject": subject,
                        "room": room
                    })
                except ValueError:
                    continue
    
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

# === Загрузка/сохранение отправленных уведомлений ===
def load_sent_notifications():
    path = "data/sent_notifications.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_sent_notifications(sent_set):
    os.makedirs("data", exist_ok=True)
    path = "data/sent_notifications.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(sent_set), f)

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
    today_date = now.strftime("%Y-%m-%d")
    
    # Загружаем отправленные уведомления
    sent_notifications = load_sent_notifications()
    new_notifications = set()

    print(f"[{now}] Running notification worker for {day_name}")

    if not os.path.exists("data"):
        print("No data directory found")
        return

    for filename in os.listdir("data"):
        if not filename.endswith(".json") or filename == "sent_notifications.json":
            continue
        
        user_id = int(filename.split(".")[0])
        
        try:
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
                try:
                    lesson_time = datetime.strptime(lesson["time"], "%H:%M").replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    diff_minutes = (lesson_time - now).total_seconds() / 60

                    # Уведомление за 1 час (окно 50-70 минут)
                    notification_1h_key = f"{user_id}_{today_date}_{lesson['time']}_1h"
                    if 50 <= diff_minutes <= 70 and notification_1h_key not in sent_notifications:
                        try:
                            bot.send_message(
                                user_id,
                                f"⏰ Через 1 час: {lesson['subject']}\n"
                                f"📍 Аудитория: {lesson['room']}\n"
                                f"🕐 Время: {lesson['time']}"
                            )
                            new_notifications.add(notification_1h_key)
                            print(f"Sent 1h notification to {user_id} for {lesson['time']}")
                        except Exception as e:
                            print(f"Failed to send 1h notification to {user_id}: {e}")

                    # Уведомление за 5 минут (окно 3-7 минут)
                    notification_5m_key = f"{user_id}_{today_date}_{lesson['time']}_5m"
                    if 3 <= diff_minutes <= 7 and notification_5m_key not in sent_notifications:
                        try:
                            bot.send_message(
                                user_id,
                                f"🔔 Через 5 минут: {lesson['subject']}\n"
                                f"📍 Аудитория: {lesson['room']}\n"
                                f"🕐 Время: {lesson['time']}"
                            )
                            new_notifications.add(notification_5m_key)
                            print(f"Sent 5m notification to {user_id} for {lesson['time']}")
                        except Exception as e:
                            print(f"Failed to send 5m notification to {user_id}: {e}")
                
                except Exception as e:
                    print(f"Error processing lesson for {user_id}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error loading schedule for {user_id}: {e}")
            continue
    
    # Сохраняем новые отправленные уведомления
    if new_notifications:
        sent_notifications.update(new_notifications)
        save_sent_notifications(sent_notifications)
        print(f"Saved {len(new_notifications)} new notifications")

# === Запуск уведомлений один раз ===
if __name__ == "__main__":
    notification_worker()
    print("GitHub Actions run finished.")
