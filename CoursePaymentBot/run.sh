#!/bin/bash

# Скрипт запуска CoursePaymentBot на Linux
# Проверяет виртуальную среду, устанавливает зависимости и запускает бота

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PYTHON_CMD="python3"

# Проверка наличия Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3."
    exit 1
fi

# Создание виртуальной среды, если её нет
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Создание виртуальной среды..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✅ Виртуальная среда создана"
else
    echo "✅ Виртуальная среда найдена"
fi

# Активация виртуальной среды
echo "🔧 Активация виртуальной среды..."
source "$VENV_DIR/bin/activate"

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip --quiet

# Установка зависимостей
if [ -f "requirements.txt" ]; then
    echo "📥 Установка зависимостей из requirements.txt..."
    pip install -r requirements.txt --quiet
    echo "✅ Зависимости установлены"
else
    echo "⚠️  Файл requirements.txt не найден"
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Внимание: файл .env не найден"
    if [ -f ".env.example" ]; then
        echo "💡 Скопируйте .env.example в .env и заполните необходимые переменные"
    fi
fi

# Запуск бота
echo "🚀 Запуск CoursePaymentBot..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python main.py
