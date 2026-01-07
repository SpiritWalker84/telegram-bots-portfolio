from flask import Flask, request, jsonify
try:
    from flask_cors import CORS
except ImportError:
    # Если flask-cors не установлен, создаем заглушку
    class CORS:
        def __init__(self, app):
            @app.after_request
            def after_request(response):
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                return response
import requests
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для работы с фронтендом

# Хранилище: site_chat_id -> список сообщений от админа
pending_replies = {}

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    site_chat_id = data.get('chat_id')
    message = data.get('message')
    
    if not site_chat_id or not message:
        return jsonify({'error': 'Missing chat_id or message'}), 400
    
    # Отправляем сообщение админу в Telegram
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        'chat_id': ADMIN_CHAT_ID,
        'text': f"Сообщение с сайта (chat_id: {site_chat_id}):\n{message}"
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        # Инициализируем список ответов для этого chat_id, если его нет
        if site_chat_id not in pending_replies:
            pending_replies[site_chat_id] = []
        return jsonify({'status': 'sent'})
    return jsonify({'error': 'Failed to send'}), 500

@app.route('/admin_reply', methods=['POST'])
def admin_reply():
    """Эндпоинт для получения ответов от бота (вызывается ботом)"""
    try:
        data = request.json
        print(f"[DEBUG] Получен ответ от бота: {data}")  # Логирование для отладки
        
        site_chat_id = data.get('site_chat_id')
        message = data.get('message')
        
        if not site_chat_id or not message:
            print(f"[ERROR] Отсутствует site_chat_id или message: {data}")
            return jsonify({'error': 'Missing site_chat_id or message'}), 400
        
        # Сохраняем ответ для отправки на сайт
        if site_chat_id not in pending_replies:
            pending_replies[site_chat_id] = []
        pending_replies[site_chat_id].append(message)
        
        print(f"[SUCCESS] Ответ сохранен для chat_id={site_chat_id}, message={message}")
        print(f"[DEBUG] Текущие pending_replies: {pending_replies}")
        
        return jsonify({'status': 'received'})
    except Exception as e:
        print(f"[ERROR] Ошибка в admin_reply: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_replies', methods=['GET'])
def get_replies():
    """Получение ответов от админа для конкретного site_chat_id"""
    site_chat_id = request.args.get('chat_id')
    
    if not site_chat_id:
        return jsonify({'error': 'Missing chat_id'}), 400
    
    # Получаем и очищаем ответы для этого chat_id
    replies = pending_replies.pop(site_chat_id, [])
    
    if replies:
        print(f"[DEBUG] Отправлено {len(replies)} ответов для chat_id={site_chat_id}")
    else:
        print(f"[DEBUG] Нет ответов для chat_id={site_chat_id}")
    
    return jsonify({'replies': replies})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
