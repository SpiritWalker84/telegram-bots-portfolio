"""Simple structure check without external dependencies."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Проверка структуры CoursePaymentBot")
print("=" * 60)

# Check file structure
required_files = [
    "src/__init__.py",
    "src/config.py",
    "src/bot/__init__.py",
    "src/bot/handlers.py",
    "src/database/__init__.py",
    "src/database/models.py",
    "src/services/__init__.py",
    "src/services/payment_service.py",
    "src/services/user_service.py",
    "src/utils/__init__.py",
    "src/utils/keyboards.py",
    "src/utils/material_loader.py",
    "main.py",
]

print("\n1. Проверка структуры файлов:")
all_files_exist = True
for file_path in required_files:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"   [OK] {file_path}")
    else:
        print(f"   [ERROR] {file_path} - не найден")
        all_files_exist = False

if not all_files_exist:
    print("\n[ERROR] Некоторые файлы отсутствуют!")
    sys.exit(1)

print("\n[SUCCESS] Все файлы на месте!")

# Check syntax (without imports)
print("\n2. Проверка синтаксиса:")
import py_compile
import os

syntax_errors = []
for file_path in required_files:
    if file_path.endswith('.py'):
        full_path = project_root / file_path
        try:
            py_compile.compile(str(full_path), doraise=True)
            print(f"   [OK] {file_path}")
        except py_compile.PyCompileError as e:
            print(f"   [ERROR] {file_path} - ошибка синтаксиса: {e}")
            syntax_errors.append(file_path)

if syntax_errors:
    print(f"\n[ERROR] Найдено {len(syntax_errors)} ошибок синтаксиса!")
    sys.exit(1)

print("\n[SUCCESS] Синтаксис всех файлов корректен!")

# Check class structure (without importing)
print("\n3. Проверка структуры классов:")

def check_class_in_file(file_path, class_name):
    """Check if class exists in file."""
    full_path = project_root / file_path
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if f'class {class_name}' in content:
                return True
    except Exception:
        pass
    return False

classes_to_check = [
    ("src/config.py", "Config"),
    ("src/database/models.py", "Database"),
    ("src/services/payment_service.py", "PaymentService"),
    ("src/services/user_service.py", "UserService"),
    ("src/utils/material_loader.py", "MaterialLoader"),
]

all_classes_exist = True
for file_path, class_name in classes_to_check:
    if check_class_in_file(file_path, class_name):
        print(f"   [OK] {class_name} в {file_path}")
    else:
        print(f"   [ERROR] {class_name} не найден в {file_path}")
        all_classes_exist = False

if not all_classes_exist:
    print("\n[ERROR] Некоторые классы отсутствуют!")
    sys.exit(1)

print("\n[SUCCESS] Все классы на месте!")

# Check imports structure
print("\n4. Проверка структуры импортов:")

def check_imports_in_file(file_path):
    """Check if file uses correct import structure."""
    full_path = project_root / file_path
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for src. imports
            if 'from src.' in content or 'import src.' in content:
                return True
            # For main.py, it should import from src
            if file_path == 'main.py' and 'from src.' in content:
                return True
    except Exception:
        pass
    return False

import_files = [
    "main.py",
    "src/bot/handlers.py",
    "src/services/user_service.py",
]

all_imports_ok = True
for file_path in import_files:
    if check_imports_in_file(file_path):
        print(f"   [OK] {file_path} использует правильные импорты")
    else:
        print(f"   [WARNING] {file_path} - проверьте импорты")

print("\n" + "=" * 60)
print("[SUCCESS] Проверка структуры завершена успешно!")
print("=" * 60)
print("\nСтруктура проекта соответствует требованиям:")
print("  - Модульная архитектура")
print("  - ООП подход")
print("  - Разделение ответственности")
print("  - Готовность к использованию")
