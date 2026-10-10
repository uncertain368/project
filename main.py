import telebot
import sqlite3
from telebot import types
import schedule
from datetime import datetime


bot = telebot.TeleBot("")

def init_db():
    conn = sqlite3.connect('fridge.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user_id INTEGER, name TEXT, date TEXT)''')
    conn.commit()
    conn.close()

init_db()


def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🥝 Добавить продукт"), types.KeyboardButton("🗑 Удалить продукт"))
    markup.add(types.KeyboardButton("🥖🥗 Мой холодильник"))
    markup.add(types.KeyboardButton("🔍 Полезные источники"), types.KeyboardButton("👀 Проверить сроки"))
    return markup



@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f'Привет! Я эко-бот, твой умный холодильник!', reply_markup=get_main_keyboard())



@bot.message_handler(func=lambda message: message.text == "🔍 Полезные источники")
def useful_links(message):
    bot.send_message(message.chat.id, 
    """🌱 **Полезные источники об экологии и хранении продуктов:**


🫐 [Cтатья ООН о том, насколько сильно пищевые отходы влияют на экологию](https://news.un.org/ru/story/2026/09/1468800),

🫐 [Сайт с рецептами на любой вкус](https://eda.rambler.ru/)
🫐 [Ещё один сайт с рецептами](https://art-lunch.ru/)

🫐 [7 способов, как сократить пищевые отходы](https://www.unep.org/ru/novosti-i-istorii/istoriya/sem-sposobov-sokratit-pishchevye-otkhody-i-podderzhat-planetu)

🫐 [Почему сокращение пищевых отходов - это выгодно?](https://news.un.org/ru/story/2025/09/1466494)""",
     parse_mode="Markdown", disable_web_page_preview=True)  # скрывает превью сайтов



#    ПОКАЗЫВАЕТ СПИСОК ПРОДУКТОВ СО СРОКАМИ ГОДНОСТИ
@bot.message_handler(func=lambda message: message.text == "🥖🥗 Мой холодильник")
def show_fridge(message):
    user_id = message.from_user.id

    conn = sqlite3.connect('fridge.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, date FROM products WHERE user_id = ?", (user_id,))
    products = cursor.fetchall()
    conn.close()

    if not products:
        bot.reply_to(message, "Тут пока пусто")
        return

    response = "<b>Ваши продукты в холодильнике:</b>\n\n"
    for item in products:
        prod_name = item[0]  # Извлекаем название
        prod_date = item[1]  # Извлекаем дату/срок годности
        response += f"• {prod_name} — до {prod_date}\n"

    bot.send_message(message.chat.id, response, parse_mode="HTML")



#     ДОБАВЛЕНИЕ ПРОДУКТА
@bot.message_handler(func=lambda message: message.text == "🥝 Добавить продукт")
def add_product(message):
    msg = bot.send_message(message.chat.id, "Введите название нового продукта:")
    bot.register_next_step_handler(msg, add_name)

def add_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"До какого числа срок годности у '{name}'? \n(Формат: ДД.ММ.ГГГГ)")
    bot.register_next_step_handler(msg, add_date, name)

def add_date(message, name):
    date_text = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect('fridge.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (user_id, name, date) VALUES (?, ?, ?)", (user_id, name, date_text))
    conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        f"Продукт '{name}' (срок годности до {date_text}) успешно добавлен!"
    )



#     УДАЛЕНИЕ ПРОДУКТА
@bot.message_handler(func=lambda message: message.text == "🗑 Удалить продукт")
def show_delete_menu(message):
    user_id = message.from_user.id

    conn = sqlite3.connect('fridge.db')
    cursor = conn.cursor()
    # Берем id и name для инлайн-кнопок
    cursor.execute("SELECT id, name FROM products WHERE user_id = ?", (user_id,))
    products = cursor.fetchall()
    conn.close()

    if not products:
        bot.reply_to(message, "Вы не можете ничего удалить, так как холодильник пуст!")
        return


    keyboard = types.InlineKeyboardMarkup()
    
    for item in products:
        p_id = item[0]
        prod_name = item[1]
        
        btn = types.InlineKeyboardButton(text=f"❌ {prod_name}", callback_data=f"delete_{p_id}")
        keyboard.add(btn)
        
    bot.send_message(message.chat.id, "Выберите продукт, который хотите удалить:", reply_markup=keyboard)



@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def confirm_delete(call):
    # Разрезаем строку по знаку "_" и забираем ID
    p_id = call.data.split("_")[1]
    
    conn = sqlite3.connect('fridge.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (p_id,))
    conn.commit()
    conn.close()
    
    #   Удаляем из чата сообщение со списком кнопок
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    bot.send_message(call.message.chat.id, 
        "Продукт успешно удален", 
        reply_markup=get_main_keyboard()
    )




#   ФУНКЦИЯ ПРОВЕРКИ
def check_dates():
    conn = sqlite3.connect('fridge.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, date FROM products")
    products = cursor.fetchall()
    conn.close()

    today = datetime.today().date()
    for item in products:
        try:
            prod_date = datetime.strptime(item[2], "%d.%m.%Y").date()
            days_left = (prod_date - today).days
            
            if days_left == 2:
                bot.send_message(item[0], f"❗️ Срок годности'{item[1]}' истекает через 2 дня!")
            elif days_left == 0:
                bot.send_message(item[0], f"‼️ Срок годности'{item[1]}' истекает сегодня!")
        except ValueError:
            continue



#   ПРОВЕРКА СРОКОВ ВРУЧНУЮ
@bot.message_handler(func=lambda message: message.text == "👀 Проверить сроки")
def manual_check(message):
    bot.reply_to(message, "⏳ Проверяю сроки годности ваших продуктов...")
    
    check_dates()     # Запускаем функцию проверки
    
    bot.send_message(message.chat.id, "✅ Проверка завершена!")




#  ЗАПУСК ТАЙМЕРА
if __name__ == '__main__':
    import threading, time
    
    schedule.every().day.at("07:00").do(check_dates)
    schedule.every().day.at("21:00").do(check_dates)

    # Запускаем короткий фоновый цикл, который будет крутить это расписание
    threading.Thread(target=lambda: [time.sleep(1) or schedule.run_pending() for _ in iter(int, 1)], daemon=True).start()

    print("Бот запущен")
    bot.infinity_polling()
