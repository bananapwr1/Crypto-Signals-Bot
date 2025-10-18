"""
Webhook сервер для приема сигналов от Crypto Signals Bot
Использует JWT авторизацию для безопасности
"""

from flask import Flask, request, jsonify
import jwt
import json
import logging
from datetime import datetime
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Секретный ключ для проверки JWT (должен совпадать с ботом!)
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your_secret_key_here')

# Файл для сохранения сигналов
SIGNALS_FILE = 'received_signals.json'

def verify_jwt_token(token):
    """Проверка JWT токена"""
    try:
        # Декодируем токен
        payload = jwt.decode(
            token,
            WEBHOOK_SECRET,
            algorithms=['HS256'],
            audience=request.url_root + 'webhook'  # Проверяем audience
        )
        logger.info(f"✅ JWT токен валидный: {payload}")
        return True, payload
    except jwt.ExpiredSignatureError:
        logger.error("❌ JWT токен истек")
        return False, "Token expired"
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ Невалидный JWT токен: {e}")
        return False, f"Invalid token: {str(e)}"

def save_signal(signal_data):
    """Сохранить сигнал в файл"""
    try:
        # Читаем существующие сигналы
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
                signals = json.load(f)
        else:
            signals = []
        
        # Добавляем timestamp получения
        signal_data['received_at'] = datetime.now().isoformat()
        
        # Добавляем новый сигнал
        signals.append(signal_data)
        
        # Сохраняем обратно
        with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Сигнал сохранен в {SIGNALS_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения сигнала: {e}")
        return False

@app.route('/')
def index():
    """Главная страница"""
    return jsonify({
        'status': 'running',
        'name': 'Crypto Signals Webhook Server',
        'version': '1.0',
        'endpoints': {
            '/webhook': 'POST - receive signals from bot',
            '/signals': 'GET - view received signals',
            '/health': 'GET - health check'
        }
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Прием webhook от бота"""
    try:
        # Получаем Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("❌ Отсутствует Authorization header")
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        # Извлекаем токен
        token = auth_header.split(' ')[1]
        
        # Проверяем токен
        valid, result = verify_jwt_token(token)
        
        if not valid:
            return jsonify({'error': result}), 401
        
        # Получаем данные сигнала
        signal_data = request.get_json()
        
        if not signal_data:
            logger.warning("❌ Пустые данные сигнала")
            return jsonify({'error': 'No signal data provided'}), 400
        
        # Логируем полученный сигнал
        logger.info("=" * 60)
        logger.info("🎯 НОВЫЙ СИГНАЛ ПОЛУЧЕН!")
        logger.info("=" * 60)
        logger.info(f"📊 Тип: {signal_data.get('type', 'unknown')}")
        logger.info(f"💎 Актив: {signal_data.get('asset', 'unknown')}")
        logger.info(f"🎯 Направление: {signal_data.get('direction', 'unknown')}")
        logger.info(f"⏱ Таймфрейм: {signal_data.get('timeframe', 'unknown')}")
        logger.info(f"📈 Уверенность: {signal_data.get('confidence', 0)}%")
        logger.info(f"⭐ Оценка: {signal_data.get('score', 0)}/8")
        logger.info(f"💰 Выплата: {signal_data.get('payout', 0)}%")
        logger.info(f"🔥 OTC: {'Да' if signal_data.get('is_otc') else 'Нет'}")
        logger.info(f"💵 Рекомендуемая ставка: {signal_data.get('recommended_stake', 0)}₽")
        logger.info("=" * 60)
        
        # Сохраняем сигнал
        save_signal(signal_data)
        
        # Возвращаем успешный ответ
        return jsonify({
            'status': 'success',
            'message': 'Signal received and processed',
            'signal': {
                'asset': signal_data.get('asset'),
                'direction': signal_data.get('direction'),
                'timeframe': signal_data.get('timeframe')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/signals', methods=['GET'])
def get_signals():
    """Просмотр полученных сигналов"""
    try:
        if not os.path.exists(SIGNALS_FILE):
            return jsonify({'signals': [], 'count': 0})
        
        with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
            signals = json.load(f)
        
        # Получаем параметр limit (по умолчанию 10)
        limit = request.args.get('limit', 10, type=int)
        
        # Возвращаем последние N сигналов
        return jsonify({
            'signals': signals[-limit:],
            'count': len(signals),
            'total': len(signals)
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка чтения сигналов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'secret_configured': bool(WEBHOOK_SECRET and WEBHOOK_SECRET != 'your_secret_key_here')
    })

if __name__ == '__main__':
    logger.info("🚀 Запуск Webhook сервера...")
    logger.info(f"🔐 Секретный ключ: {'✅ Настроен' if WEBHOOK_SECRET and WEBHOOK_SECRET != 'your_secret_key_here' else '❌ НЕ НАСТРОЕН (используйте переменную окружения WEBHOOK_SECRET)'}")
    logger.info("📡 Сервер будет слушать на порту 8080")
    logger.info("🌐 Webhook endpoint: http://0.0.0.0:8080/webhook")
    
    # Запускаем сервер на порту 8080
    app.run(host='0.0.0.0', port=8080, debug=True)
