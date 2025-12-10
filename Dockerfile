# ======================================
# Dockerfile для Crypto Signals Bot
# Версия: 1.0
# Python 3.11 + Chrome + Selenium
# ======================================

FROM python:3.11-slim-bookworm

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Создание рабочей директории
WORKDIR /app

# Установка системных зависимостей и Chrome (современный метод)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    default-jdk \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    # Установка Chrome - НОВЫЙ МЕТОД (без apt-key)
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /tmp/google-chrome-key.pub https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg /tmp/google-chrome-key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.pub

# Копирование requirements.txt
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всех файлов приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Проверка установки Chrome
RUN google-chrome --version

# Expose порт для webhook (если используется)
EXPOSE 8080

# Запуск бота
CMD ["python", "run_bot.py"]
