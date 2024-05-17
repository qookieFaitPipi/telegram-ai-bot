import telebot
import requests
import os
from flask import Flask, request, render_template
import sqlite3
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np

import matplotlib
matplotlib.use('agg')

TOKEN = ''

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

WEBHOOK_URL_BASE = "https://96b7-31-134-187-189.ngrok-free.app"
WEBHOOK_URL_PATH = "/{}/".format(TOKEN)

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

conn = sqlite3.connect('database.sql', check_same_thread=False)
cursor = conn.cursor()

model = tf.keras.models.load_model("model/trained_model798.keras")

user_states = {}

@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
  update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))

  if update.message:
    message = update.message
    chat_id = message.chat.id
    text = message.text

    if text == '/start':
      send_telegram_message(chat_id, "Привет! Этот бот предназначен для угадывания картинки")
      return 'done', 200

    elif text == '/predict':
      user_states[chat_id] = 'awaiting_image'
      send_telegram_message(chat_id, "Отправьте изображение для классификации")
      return 'done', 200

    elif text == '/register':
      user_states[chat_id] = 'awaiting_password_register'
      send_telegram_message(chat_id, "Введите ваш пароль:")
      return 'done', 200

    elif text == '/login':
      user_states[chat_id] = 'awaiting_password_login'
      send_telegram_message(chat_id, "Введите ваш пароль:")
      return 'done', 200


    if chat_id in user_states and user_states[chat_id] == 'awaiting_password_register':
      try:
        # Обработка ввода пользователя и вставка данных в базу данных
        password = message.text
        cursor.execute("INSERT INTO users (id, password) VALUES (?, ?)", (chat_id, password))
        conn.commit()
        del user_states[chat_id]  # Удаляем состояние пользователя после успешной регистрации
      except sqlite3.IntegrityError:
        send_telegram_message(chat_id, "Ошибка при регистрации пользователя. Возможно, вы уже зарегистрированы.")
      except Exception as e:
        send_telegram_message(chat_id, f"Произошла ошибка при регистрации пользователя: {e}")
        
      send_telegram_message(chat_id, f"Пользователь успешно зарегистрирован!")

    if chat_id in user_states and user_states[chat_id] == 'awaiting_password_login':
      try:
        # Обработка ввода пользователя и вставка данных в базу данных
        password = message.text
        cursor.execute("SELECT * FROM users WHERE id=? AND password=?", (chat_id, password))
        user = cursor.fetchone()
        del user_states[chat_id]  # Удаляем состояние пользователя после успешной регистрации
      except Exception as e:
        send_telegram_message(chat_id, f"Произошла ошибка при авторизации: {e}")
      
      if user:
        send_telegram_message(chat_id, f"Вход успешно выполнен")
      else:
        send_telegram_message(chat_id, f"Неправильный пароль!")

    if chat_id in user_states and user_states[chat_id] == 'awaiting_image':
      if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        file_path = download_file_by_url(file_url, chat_id)
        print(file_path)
        
        img = image.load_img(file_path, target_size=(200, 200))
        x = image.img_to_array(img)
        plt.imshow(x / 255.)
        x = np.expand_dims(x, axis=0)
        images = np.vstack([x])
        classes = model.predict(images, batch_size=10, verbose=0)

        if classes[0] < 0.5:
          send_telegram_message(chat_id, 'На изображении изображен fox.')
        else:
          send_telegram_message(chat_id, 'На изображении изображен human.')
        
        try:
          os.remove(file_path)
        except:
          pass

      else:
        send_telegram_message(chat_id, 'Пожалуйста, отправьте изображение.')

  return 'done', 200


def send_telegram_message(chat_id, text):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={text}"
  res = requests.get(url)

  if res.status_code != 200:
    print(f"Ошибка при отправке сообщения: {response.status_code}, {response.text}")


def download_file_by_url(file_url, chat_id):
  try:
    response = requests.get(file_url)
    if response.status_code == 200:
      file_path = f"images/image_{chat_id}.jpg"
      with open(file_path, 'wb') as f:
        f.write(response.content)
      return file_path
    else:
      print(f"Error receiving data: {response.status_code}")
  except requests.exceptions.RequestException as e:
    print(f"Error HTTP request: {e}")

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8000)
