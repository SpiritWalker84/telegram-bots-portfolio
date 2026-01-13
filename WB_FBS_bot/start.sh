#!/bin/bash

# Скрипт для запуска WB FBS Bot с виртуальной средой

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}=== WB FBS Bot Launcher ===${NC}"

# Имя виртуальной среды
VENV_NAME="venv"
VENV_PATH="$SCRIPT_DIR/$VENV_NAME"

# Проверяем наличие виртуальной среды
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Виртуальная среда не найдена. Создаю...${NC}"
    
    # Проверяем наличие python3
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Ошибка: Python не найден!${NC}"
        exit 1
    fi
    
    # Создаем виртуальную среду
    $PYTHON_CMD -m venv "$VENV_PATH"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ошибка при создании виртуальной среды!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Виртуальная среда создана!${NC}"
fi

# Активируем виртуальную среду
echo -e "${GREEN}Активация виртуальной среды...${NC}"
source "$VENV_PATH/bin/activate"

if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при активации виртуальной среды!${NC}"
    exit 1
fi

# Обновляем pip
echo -e "${GREEN}Обновление pip...${NC}"
pip install --upgrade pip --quiet

# Проверяем наличие requirements.txt
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}Установка зависимостей...${NC}"
    pip install -r requirements.txt --quiet
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ошибка при установке зависимостей!${NC}"
        deactivate
        exit 1
    fi
else
    echo -e "${YELLOW}Предупреждение: requirements.txt не найден!${NC}"
fi

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo -e "${RED}Ошибка: .env файл не найден!${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Создайте .env файл на основе .env.example:${NC}"
        echo -e "${YELLOW}  cp .env.example .env${NC}"
        echo -e "${YELLOW}Затем заполните необходимые параметры в .env файле${NC}"
    else
        echo -e "${RED}Файл .env.example также не найден!${NC}"
    fi
    deactivate
    exit 1
fi

# Проверяем, что .env файл не пустой
if [ ! -s ".env" ]; then
    echo -e "${RED}Ошибка: .env файл пустой!${NC}"
    echo -e "${YELLOW}Заполните .env файл необходимыми параметрами${NC}"
    deactivate
    exit 1
fi

# Запускаем бота
echo -e "${GREEN}Запуск бота...${NC}"
echo -e "${GREEN}Для остановки нажмите Ctrl+C${NC}"
echo ""

python main.py

# Деактивируем виртуальную среду при выходе
deactivate
