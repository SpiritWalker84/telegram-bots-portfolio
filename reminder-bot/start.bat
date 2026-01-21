@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

REM Проверка наличия виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo ✅ Виртуальное окружение найдено
    call venv\Scripts\activate.bat
    echo ✅ Виртуальное окружение активировано
    python -u main.py
    goto :end
)

echo ⚠️ Виртуальное окружение не найдено
echo 📦 Создание виртуального окружения...

REM Попытка использовать py launcher для создания venv
where py >nul 2>&1
if not errorlevel 1 (
    echo ✅ Используется py launcher для создания venv...
    py -m venv venv
    if errorlevel 1 (
        echo ❌ Ошибка при создании виртуального окружения!
        pause
        exit /b 1
    )
    
    echo ✅ Виртуальное окружение создано
    echo 📥 Активация виртуального окружения...
    call venv\Scripts\activate.bat
    
    echo 📦 Установка зависимостей...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Ошибка при установке зависимостей!
        pause
        exit /b 1
    )
    
    echo ✅ Зависимости установлены
    echo 🚀 Запуск бота...
    python -u main.py
    goto :end
)

echo py launcher не найден, поиск Python...
REM Поиск Python в стандартных местах Windows
set PYTHON_EXE=

REM Проверка стандартных путей
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
) else if exist "C:\Python312\python.exe" (
    set PYTHON_EXE=C:\Python312\python.exe
) else if exist "C:\Python311\python.exe" (
    set PYTHON_EXE=C:\Python311\python.exe
) else if exist "C:\Python310\python.exe" (
    set PYTHON_EXE=C:\Python310\python.exe
)

if defined PYTHON_EXE (
    echo ✅ Python найден: %PYTHON_EXE%
    echo 📦 Создание виртуального окружения...
    "%PYTHON_EXE%" -m venv venv
    if errorlevel 1 (
        echo ❌ Ошибка при создании виртуального окружения!
        pause
        exit /b 1
    )
    
    echo ✅ Виртуальное окружение создано
    echo 📥 Активация виртуального окружения...
    call venv\Scripts\activate.bat
    
    echo 📦 Установка зависимостей...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Ошибка при установке зависимостей!
        pause
        exit /b 1
    )
    
    echo ✅ Зависимости установлены
    echo 🚀 Запуск бота...
    python -u main.py
    goto :end
)

echo ❌ Python не найден!
echo Пожалуйста, убедитесь что Python установлен и доступен через 'py' или добавлен в PATH
pause
exit /b 1

:end
pause
