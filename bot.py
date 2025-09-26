import telebot
from telebot import types
import sqlite3
import random
import time
import config
import threading

# Инициализация бота
bot = telebot.TeleBot(config.TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('doxbot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                score INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0
              )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER PRIMARY KEY,
                last_dox_time REAL DEFAULT 0,
                last_shop_time REAL DEFAULT 0
              )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS defs (
                user_id INTEGER PRIMARY KEY,
                purchased INTEGER DEFAULT 0,
                last_def_time REAL DEFAULT 0
              )''')

conn.commit()

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)', 
                  (user_id, username, full_name))
    conn.commit()
    
    bot.reply_to(message, "👋 Привет! Я бот для доксинга. Используй /dox чтобы начать!")

def check_subscription(user_id):
    try:
        status = bot.get_chat_member(config.ID_CHANNEL, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def subscription_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Подписаться", url=config.LINK_CHANNEL),
        types.InlineKeyboardButton("Проверить подписку", callback_data="check_sub")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Вы подписаны! Теперь можете использовать команды.")
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!", show_alert=True)

def check_shop_cooldown(user_id):
    cursor.execute('SELECT last_shop_time FROM cooldowns WHERE user_id = ?', (user_id,))
    cooldown_data = cursor.fetchone()
    
    if cooldown_data and cooldown_data[0]:
        if time.time() - cooldown_data[0] < 60:
            return int(60 - (time.time() - cooldown_data[0]))
    return 0

def buy_svat(user_id, chat_id):
    cursor.execute('UPDATE users SET score = score - 500 WHERE user_id = ?', (user_id,))
    conn.commit()
    
    target = random.choice(list(config.DOX_TABLE.keys()))
    msg = bot.send_message(chat_id, f"🔍 Произвожу сват на {target}...")
    time.sleep(2)
    
    rand = random.random()
    cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
    current_score = cursor.fetchone()[0]
    
    if rand < 0.25:
        cursor.execute('UPDATE users SET score = score + 1000 WHERE user_id = ?', (user_id,))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"✅ Сват удался! +1000 очков\n💳 Ваш баланс: {new_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    elif rand < 0.95:
        bot.edit_message_text(
            f"❌ Сват не удался... -500 очков\n💳 Ваш баланс: {current_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    else:
        cursor.execute('UPDATE users SET score = score - 100 WHERE user_id = ?', (user_id,))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"🚨 Вас обнаружила полиция! -600 очков (500+100)\n💳 Ваш баланс: {new_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    
    cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, last_shop_time) VALUES (?, ?)', 
                  (user_id, time.time()))
    conn.commit()

def buy_def(user_id, chat_id):
    cursor.execute('SELECT purchased FROM defs WHERE user_id = ?', (user_id,))
    def_data = cursor.fetchone()
    
    if def_data and def_data[0] == 1:
        return "❌ Вы уже купили дефа!"
    
    cursor.execute('UPDATE users SET score = score - 1000 WHERE user_id = ?', (user_id,))
    cursor.execute('INSERT OR REPLACE INTO defs (user_id, purchased) VALUES (?, 1)', (user_id,))
    cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, last_shop_time) VALUES (?, ?)', (user_id, time.time()))
    conn.commit()
    
    return "✅ Вы купили дефа! Теперь он будет пытаться задоксить случайных пользователей каждые 1.5 минуты."

def buy_dox_all(user_id, chat_id):
    cursor.execute('UPDATE users SET score = score - 5000 WHERE user_id = ?', (user_id,))
    conn.commit()
    
    msg = bot.send_message(chat_id, "🌐 Докшу все км...")
    time.sleep(2)
    
    rand = random.random()
    if rand < 0.2:
        cursor.execute('UPDATE users SET score = score + 7000 WHERE user_id = ?', (user_id,))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"✅ Докс всех удался! +2000 очков (7000-5000)\n💳 Ваш баланс: {new_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    else:
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        current_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"❌ Докс всех провалился... -5000 очков\n💳 Ваш баланс: {current_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    
    cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, last_shop_time) VALUES (?, ?)', 
                  (user_id, time.time()))
    conn.commit()

def buy_door_fire(user_id, chat_id):
    cursor.execute('UPDATE users SET score = score - 1500 WHERE user_id = ?', (user_id,))
    conn.commit()
    
    target = random.choice(list(config.DOX_TABLE.keys()))
    msg = bot.send_message(chat_id, f"🔥 Поджигаю дверь {target}...")
    time.sleep(2)
    
    rand = random.random()
    if rand < 0.4:
        cursor.execute('UPDATE users SET score = score + 2000 WHERE user_id = ?', (user_id,))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"✅ Поджог удался! +500 очков (2000-1500)\n💳 Ваш баланс: {new_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    else:
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        current_score = cursor.fetchone()[0]
        bot.edit_message_text(
            f"❌ Поджог не удался... -1500 очков\n💳 Ваш баланс: {current_score}",
            chat_id=chat_id,
            message_id=msg.message_id
        )
    
    cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, last_shop_time) VALUES (?, ?)', 
                  (user_id, time.time()))
    conn.commit()

@bot.message_handler(commands=['shop'])
def shop_command(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "📢 Подпишитесь на канал, чтобы использовать команды!",
                     reply_markup=subscription_keyboard())
        return
    
    cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
    score_data = cursor.fetchone()
    if not score_data:
        bot.reply_to(message, "❌ Вы не зарегистрированы! Напишите /start")
        return
        
    score = score_data[0]
    cooldown = check_shop_cooldown(user_id)
    cooldown_text = f"\n⏳ До следующей покупки: {cooldown} сек" if cooldown > 0 else ""
    
    text = f"🛒 Магазин | 💰 Баланс: {score} очков{cooldown_text}\n\n"
    text += "1. Сват — 500 очков\n"
    text += "   - Шансы: удача (25%), неудача (70%), полиция (5%)\n\n"
    text += "2. Деф — 1000 очков (1 раз)\n"
    text += "   - Автоматически пытается задоксить каждые 1.5 минуты\n"
    text += "   - Шансы: успех (85%), неудача (14.5%), пропажа (0.5%)\n\n"
    text += "3. Докс всех — 5000 очков\n"
    text += "   - Шансы: удача (20% - +7000), неудача (80% - потеря 5000)\n\n"
    text += "4. Поджог двери — 1500 очков\n"
    text += "   - Шансы: удача (40% - +2000), неудача (60%)\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Сват (500)", callback_data="shop_svat"),
        types.InlineKeyboardButton("Деф (1000)", callback_data="shop_def")
    )
    keyboard.row(
        types.InlineKeyboardButton("Докс всех (5000)", callback_data="shop_doxall"),
        types.InlineKeyboardButton("Поджог двери (1500)", callback_data="shop_fire")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('shop_'))
def shop_callback(call):
    user_id = call.from_user.id
    action = call.data.split('_')[1]
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Подпишитесь на канал!", show_alert=True)
        return
    
    cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
    score_data = cursor.fetchone()
    if not score_data:
        bot.answer_callback_query(call.id, "❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    score = score_data[0]
    cooldown = check_shop_cooldown(user_id)
    if cooldown > 0:
        bot.answer_callback_query(call.id, f"⏳ Подождите {cooldown} секунд!", show_alert=True)
        return
    
    if action == "svat":
        if score < 500:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "✅ Куплено!")
        buy_svat(user_id, call.message.chat.id)
        
    elif action == "def":
        if score < 1000:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков!", show_alert=True)
            return
        result = buy_def(user_id, call.message.chat.id)
        bot.answer_callback_query(call.id, result)
        
    elif action == "doxall":
        if score < 5000:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "✅ Куплено!")
        buy_dox_all(user_id, call.message.chat.id)
        
    elif action == "fire":
        if score < 1500:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "✅ Куплено!")
        buy_door_fire(user_id, call.message.chat.id)

@bot.message_handler(commands=['dox'])
def dox_command(message):
    user_id = message.from_user.id
    
    cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
    ban_data = cursor.fetchone()
    
    if ban_data is None:
        username = message.from_user.username
        full_name = message.from_user.full_name
        cursor.execute('INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)', 
                      (user_id, username, full_name))
        conn.commit()
        cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
        ban_data = cursor.fetchone()
    
    if ban_data and ban_data[0] == 1:
        bot.reply_to(message, "🚫 Вы забанены!")
        return
    
    if not check_subscription(user_id):
        bot.reply_to(message, "📢 Подпишитесь на канал, чтобы использовать команды!",
                     reply_markup=subscription_keyboard())
        return
    
    cursor.execute('SELECT last_dox_time FROM cooldowns WHERE user_id = ?', (user_id,))
    cooldown_data = cursor.fetchone()
    cooldown_duration = 60
    
    if cooldown_data and cooldown_data[0]:
        last_time = cooldown_data[0]
        if time.time() - last_time < cooldown_duration:
            remaining = int(cooldown_duration - (time.time() - last_time))
            bot.reply_to(message, f"⏳ Подождите {remaining} секунд перед следующим доксом!")
            return
    
    cursor.execute('INSERT OR REPLACE INTO cooldowns (user_id, last_dox_time) VALUES (?, ?)', 
                  (user_id, time.time()))
    conn.commit()
    
    rand = random.random()
    target = random.choice(list(config.DOX_TABLE.keys()))
    
    if rand < 0.05:
        event_type = random.choice(config.EASTER_EGGS)
        points = event_type["points"]
        cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        response = f"{event_type['message']}\n+{points} очков!\n💳 Ваш баланс: {new_score}"
    elif rand < 0.60:
        points = config.DOX_TABLE[target]
        cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))
        conn.commit()
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
        new_score = cursor.fetchone()[0]
        response = f"✅ Докс удался! Вы задоксили {target}, +{points} очков!\n💳 Ваш баланс: {new_score}"
    else:
        points = 0
        response = f"❌ Задоксить не получилось, {target} слишком анонимен"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['top'])
def top_command(message):
    cursor.execute('SELECT username, score FROM users WHERE banned = 0 ORDER BY score DESC LIMIT 10')
    top_users = cursor.fetchall()
    
    if not top_users:
        bot.reply_to(message, "🥺 Топ пуст!")
        return
    
    response = "🏆 ТОП ДОКСЕРОВ:\n\n"
    for i, (username, score) in enumerate(top_users, 1):
        if username:
            response += f"{i}. @{username}: {score} очков\n"
        else:
            response += f"{i}. [без юзернейма]: {score} очков\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    
    cursor.execute('SELECT username, score FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        bot.reply_to(message, "❌ Вы не зарегистрированы! Напишите /start")
        return
        
    username, score = user_data
    
    cursor.execute('SELECT purchased FROM defs WHERE user_id = ?', (user_id,))
    def_data = cursor.fetchone()
    def_status = "✅ Куплен" if def_data and def_data[0] == 1 else "❌ Не куплен"
    
    response = f"👤 Ваш профиль:\n"
    response += f"👤 Юзернейм: @{username}\n" if username else "👤 Юзернейм: не указан\n"
    response += f"💰 Баланс: {score} очков\n"
    response += f"🕵️‍♂️ Деф: {def_status}\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['info'])
def info_command(message):
    # Получаем общее количество пользователей
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Получаем количество активных пользователей (не забаненных)
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 0')
    active_users = cursor.fetchone()[0]
    
    # Получаем количество пользователей с дефами
    cursor.execute('SELECT COUNT(*) FROM defs WHERE purchased = 1')
    def_users = cursor.fetchone()[0]
    
    response = f"📊 Статистика бота:\n\n"
    response += f"👥 Всего пользователей: {total_users}\n"
    response += f"👤 Активных пользователей: {active_users}\n"
    response += f"🕵️‍♂️ Пользователей с дефами: {def_users}\n"
    response += f"🌐 Целей для докса: {len(config.DOX_TABLE)}\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📖 Доступные команды:

/dox - Попытаться задоксить случайного пользователя
/top - Показать топ игроков
/profile - Показать ваш профиль
/shop - Магазин улучшений
/trans @юзер сумма - Перевести очки другому игроку
/info - Статистика бота
/help - Показать это сообщение

🛠 Админ-команды:
/ban @юзер - Забанить пользователя
/unban @юзер - Разбанить пользователя
/add @юзер количество - Добавить очки пользователю
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['ban'])
def ban_command(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.reply_to(message, "⛔ У вас нет прав!")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "❌ Укажите @юзернейм!")
        return
    
    target = message.text.split()[1]
    if not target.startswith('@'):
        bot.reply_to(message, "❌ Укажите @юзернейм!")
        return
    
    username = target[1:]
    cursor.execute('UPDATE users SET banned = 1 WHERE username = ?', (username,))
    conn.commit()
    
    if cursor.rowcount > 0:
        bot.reply_to(message, f"🔨 Пользователь @{username} забанен!")
    else:
        bot.reply_to(message, "❌ Пользователь не найден!")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.reply_to(message, "⛔ У вас нет прав!")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "❌ Укажите @юзернейм!")
        return
    
    target = message.text.split()[1]
    if not target.startswith('@'):
        bot.reply_to(message, "❌ Укажите @юзернейм!")
        return
    
    username = target[1:]
    cursor.execute('UPDATE users SET banned = 0 WHERE username = ?', (username,))
    conn.commit()
    
    if cursor.rowcount > 0:
        bot.reply_to(message, f"🔓 Пользователь @{username} разбанен!")
    else:
        bot.reply_to(message, "❌ Пользователь не найден!")

@bot.message_handler(commands=['add'])
def add_points_command(message):
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        bot.reply_to(message, "⛔ У вас нет прав!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError
        
        target_username = parts[1]
        if not target_username.startswith('@'):
            raise ValueError
        
        points = int(parts[2])
        if points <= 0:
            raise ValueError
        
        # Убираем @ из username
        target_username = target_username[1:]
        
        # Находим пользователя
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
        target_data = cursor.fetchone()
        
        if not target_data:
            bot.reply_to(message, "❌ Пользователь не найден!")
            return
        
        target_id = target_data[0]
        
        # Добавляем очки
        cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, target_id))
        conn.commit()
        
        # Получаем новый баланс
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (target_id,))
        new_score = cursor.fetchone()[0]
        
        bot.reply_to(message, f"✅ Добавлено {points} очков пользователю @{target_username}\n💳 Новый баланс: {new_score}")
    
    except ValueError:
        bot.reply_to(message, "❌ Неправильный формат команды. Используйте: /add @юзер количество_очков")

@bot.message_handler(commands=['trans'])
def transfer_points_command(message):
    sender_id = message.from_user.id
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError

target_username = parts[1]
        if not target_username.startswith('@'):
            raise ValueError
        
        points = int(parts[2])
        if points <= 0:
            raise ValueError
        
        # Убираем @ из username
        target_username = target_username[1:]
        
        # Находим пользователя
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
        target_data = cursor.fetchone()
        
        if not target_data:
            bot.reply_to(message, "❌ Пользователь не найден!")
            return
        
        target_id = target_data[0]
        
        # Добавляем очки
        cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, target_id))
        conn.commit()
        
        # Получаем новый баланс
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (target_id,))
        new_score = cursor.fetchone()[0]
        
        bot.reply_to(message, f"✅ Добавлено {points} очков пользователю @{target_username}\n💳 Новый баланс: {new_score}")
    
    except ValueError:
        bot.reply_to(message, "❌ Неправильный формат команды. Используйте: /add @юзер количество_очков")

@bot.message_handler(commands=['trans'])
def transfer_points_command(message):
    sender_id = message.from_user.id
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError
        
        target_username = parts[1]
        if not target_username.startswith('@'):
            raise ValueError

        points = int(parts[2])
        if points <= 0:
            raise ValueError
        
        # Убираем @ из username
        target_username = target_username[1:]
        
        # Проверяем что отправитель не переводит сам себе
        cursor.execute('SELECT username FROM users WHERE user_id = ?', (sender_id,))
        sender_username = cursor.fetchone()[0]
        if sender_username == target_username:
            bot.reply_to(message, "❌ Нельзя переводить очки самому себе!")
            return
        
        # Проверяем баланс отправителя
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (sender_id,))
        sender_balance = cursor.fetchone()[0]
        
        if sender_balance < points:
            bot.reply_to(message, f"❌ Недостаточно очков для перевода! Ваш баланс: {sender_balance}")
            return
        
        # Находим получателя
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
        target_data = cursor.fetchone()
        
        if not target_data:
            bot.reply_to(message, "❌ Пользователь не найден!")
            return
        
        target_id = target_data[0]
        
        # Выполняем перевод
        cursor.execute('UPDATE users SET score = score - ? WHERE user_id = ?', (points, sender_id))
        cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, target_id))
        conn.commit()
        
        # Получаем новые балансы
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (sender_id,))
        new_sender_balance = cursor.fetchone()[0]
        
        cursor.execute('SELECT score FROM users WHERE user_id = ?', (target_id,))
        new_target_balance = cursor.fetchone()[0]
        
        bot.reply_to(message, 
                    f"✅ Успешный перевод!\n"
                    f"📤 Вы перевели @{target_username} {points} очков\n"
                    f"💳 Ваш новый баланс: {new_sender_balance}\n"
                    f"💳 Баланс получателя: {new_target_balance}")
        
        # Уведомляем получателя
        try:
            bot.send_message(
                target_id,
                f"💸 Вам перевели {points} очков от @{sender_username}\n"
                f"💳 Ваш новый баланс: {new_target_balance}"
            )
        except Exception as e:
            print(f"Не удалось уведомить получателя: {e}")
    
    except ValueError:
        bot.reply_to(message, "❌ Неправильный формат команды. Используйте: /trans @юзер количество_очков")

def def_actions():
    while True:
        try:
            cursor.execute('SELECT user_id FROM defs WHERE purchased = 1')
            def_users = cursor.fetchall()
            
            for (user_id,) in def_users:
                try:
                    cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
                    if cursor.fetchone()[0] == 1:
                        continue
                    
                    cursor.execute('SELECT last_def_time FROM defs WHERE user_id = ?', (user_id,))
                    def_data = cursor.fetchone()
                    
                    current_time = time.time()
                    last_def_time = def_data[0] if def_data and def_data[0] else 0
                    
                    # КД 1.5 минуты (90 секунд)
                    if current_time - last_def_time >= 90:
                        target = random.choice(list(config.DOX_TABLE.keys()))
                        points = config.DOX_TABLE[target]
                        
                        rand = random.random()
                        if rand < 0.85:  # 85% успех
                            cursor.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))
                            try:
                                bot.send_message(
                                    user_id, 
                                    f"🕵️‍♂️ Ваш деф задоксил {target} и принес вам {points} очков!"
                                )
                            except Exception as e:
                                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                        elif rand < 0.995:  # 14.5% неудача (85% + 14.5% = 99.5%)
                            try:
                                bot.send_message(
                                    user_id, 
                                    f"🕵️‍♂️ Ваш деф пытался задоксить {target}, но не смог."
                                )
                            except Exception as e:
                                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                        else:  # 0.5% пропажа дефа
                            cursor.execute('DELETE FROM defs WHERE user_id = ?', (user_id,))
                            try:
                                bot.send_message(
                                    user_id, 
                                    "💥 Ваш деф был раскрыт и уничтожен! Придется покупать нового."
                                )
                            except Exception as e:
                                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                            continue  # Пропускаем обновление времени для удаленного дефа
                        
                        cursor.execute('UPDATE defs SET last_def_time = ? WHERE user_id = ?', (current_time, user_id))
                        conn.commit()
                
                except Exception as e:
                    print(f"Ошибка при обработке пользователя {user_id}: {e}")
                    conn.rollback()
            
            time.sleep(30)  # Проверяем каждые 30 секунд
            
        except Exception as e:
            print(f"Критическая ошибка в def_actions: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Удаляем старую таблицу cooldowns и создаем новую с нужными колонками
    cursor.execute('DROP TABLE IF EXISTS cooldowns')
    cursor.execute('''CREATE TABLE cooldowns (
                    user_id INTEGER PRIMARY KEY,
                    last_dox_time REAL DEFAULT 0,
                    last_shop_time REAL DEFAULT 0
                  )''')
    
    # Добавляем колонку last_def_time в таблицу defs
    try:
        cursor.execute('ALTER TABLE defs ADD COLUMN last_def_time REAL DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    conn.commit()
    
    # Устанавливаем меню команд
    bot.set_my_commands(
        commands=[
            telebot.types.BotCommand("dox", "Попытаться задоксить"),
            telebot.types.BotCommand("top", "Топ игроков"),
            telebot.types.BotCommand("profile", "Ваш профиль"),
            telebot.types.BotCommand("shop", "Магазин улучшений"),
            telebot.types.BotCommand("trans", "Перевод очков"),
            telebot.types.BotCommand("info", "Статистика бота"),
            telebot.types.BotCommand("help", "Помощь по командам"),
            telebot.types.BotCommand("start", "Перезапустить бота")
        ],
        scope=telebot.types.BotCommandScopeAllPrivateChats()
    )
    
    bot.set_my_commands(
        commands=[
            telebot.types.BotCommand("dox", "Попытаться задоксить"),
            telebot.types.BotCommand("top", "Топ игроков"),
            telebot.types.BotCommand("profile", "Ваш профиль"),
            telebot.types.BotCommand("shop", "Магазин улучшений"),
            telebot.types.BotCommand("trans", "Перевод очков"),
            telebot.types.BotCommand("info", "Статистика бота"),
            telebot.types.BotCommand("help", "Помощь по командам")
        ],
        scope=telebot.types.BotCommandScopeAllGroupChats()
    )
    
    # Запускаем поток для автоматических действий дефа
    def_thread = threading.Thread(target=def_actions, daemon=True)
    def_thread.start()
    
    print("Бот запущен! Команды настроены.")
    bot.infinity_polling()
