"""
app.py - Flask админ-панель для просмотра статуса бота
Простая веб-панель без торговой логики.
"""

import os
from flask import Flask, render_template_string, jsonify
from datetime import datetime

# Безопасный импорт database
try:
    from database import database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    database = None

# Безопасный импорт config
try:
    from config import config as app_config
    SECRET_KEY = app_config.FLASK_SECRET_KEY
except ImportError:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

app = Flask(__name__)
app.secret_key = SECRET_KEY


# HTML шаблон главной страницы
MAIN_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Bot Admin Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stat-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #333;
        }
        .table-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .table-card h2 {
            color: #667eea;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success {
            background: #10b981;
            color: white;
        }
        .badge-warning {
            background: #f59e0b;
            color: white;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Crypto Bot Admin Panel</h1>
            <p>Управление и мониторинг бота</p>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 Обновить</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>👥 Всего пользователей</h3>
                <div class="value">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <h3>📝 Команд выполнено</h3>
                <div class="value">{{ total_commands }}</div>
            </div>
            <div class="stat-card">
                <h3>⚡ Статус системы</h3>
                <div class="value">
                    <span class="badge badge-{{ status_class }}">{{ status }}</span>
                </div>
            </div>
        </div>
        
        <div class="table-card">
            <h2>👥 Последние пользователи</h2>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Username</th>
                        <th>Дата регистрации</th>
                    </tr>
                </thead>
                <tbody>
                    {% if users %}
                        {% for user in users[:10] %}
                        <tr>
                            <td>{{ user.user_id }}</td>
                            <td>{{ user.username or 'N/A' }}</td>
                            <td>{{ user.created_at or 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="3" style="text-align: center; color: #999;">
                                Нет данных о пользователях
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
        
        <div class="table-card">
            <h2>📝 Последние команды</h2>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Команда</th>
                        <th>Время</th>
                    </tr>
                </thead>
                <tbody>
                    {% if commands %}
                        {% for cmd in commands[:20] %}
                        <tr>
                            <td>{{ cmd.user_id }}</td>
                            <td><strong>{{ cmd.command }}</strong></td>
                            <td>{{ cmd.timestamp or 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="3" style="text-align: center; color: #999;">
                                Нет данных о командах
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Главная страница админ-панели"""
    
    if not DATABASE_AVAILABLE or not database:
        # Режим без базы данных
        return render_template_string(
            MAIN_PAGE_TEMPLATE,
            total_users=0,
            total_commands=0,
            status='stub_mode',
            status_class='warning',
            users=[],
            commands=[]
        )
    
    # Получаем данные из базы
    users = database.get_users()
    commands = database.get_commands(limit=20)
    status_data = database.get_status()
    
    return render_template_string(
        MAIN_PAGE_TEMPLATE,
        total_users=status_data.get('total_users', 0),
        total_commands=status_data.get('total_commands', 0),
        status=status_data.get('status', 'unknown'),
        status_class='success' if status_data.get('status') == 'active' else 'warning',
        users=users,
        commands=commands
    )


@app.route('/api/status')
def api_status():
    """API endpoint для получения статуса"""
    
    if not DATABASE_AVAILABLE or not database:
        return jsonify({
            'status': 'stub_mode',
            'total_users': 0,
            'total_commands': 0,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    status = database.get_status()
    return jsonify(status)


@app.route('/api/users')
def api_users():
    """API endpoint для получения списка пользователей"""
    
    if not DATABASE_AVAILABLE or not database:
        return jsonify({'users': [], 'count': 0})
    
    users = database.get_users()
    return jsonify({'users': users, 'count': len(users)})


@app.route('/api/commands')
def api_commands():
    """API endpoint для получения списка команд"""
    
    if not DATABASE_AVAILABLE or not database:
        return jsonify({'commands': [], 'count': 0})
    
    commands = database.get_commands(limit=100)
    return jsonify({'commands': commands, 'count': len(commands)})


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'available' if DATABASE_AVAILABLE and database else 'unavailable',
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("🚀 Flask Admin Panel запускается...")
    print(f"📡 Порт: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"💾 Database: {'Available' if DATABASE_AVAILABLE else 'Unavailable'}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
