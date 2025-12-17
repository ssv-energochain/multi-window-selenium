"""
Скрипт для сборки exe и подготовки дистрибутива.
Запуск: python build.py
"""
import os
import sys
import shutil
import subprocess


def main():
    print("=" * 50)
    print("Сборка Multi-Window Selenium Launcher")
    print("=" * 50)
    print()
    
    # Директории
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    resources_dir = os.path.join(dist_dir, "resources")
    
    # 1. Сборка exe
    print("[1/3] Сборка exe файла...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "MultiWindowSelenium",
        "gui_app.py",
        "--noconfirm"
    ], cwd=base_dir)
    
    if result.returncode != 0:
        print("❌ Ошибка сборки!")
        return 1
    
    print("✓ exe файл собран")
    
    # 2. Создание структуры resources
    print("[2/3] Создание папки resources...")
    
    folders = [
        resources_dir,
        os.path.join(resources_dir, "extensions"),
        os.path.join(resources_dir, "chrome_profile_clones"),
        os.path.join(resources_dir, "yandex_profile_clones"),
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    
    # 3. Копирование файлов
    print("[3/3] Копирование ресурсов...")
    
    # yandexdriver.exe
    src = os.path.join(base_dir, "yandexdriver.exe")
    if os.path.exists(src):
        shutil.copy2(src, resources_dir)
        print("  ✓ yandexdriver.exe")
    else:
        print("  ⚠ yandexdriver.exe не найден")
    
    # Расширения
    ext_src = os.path.join(base_dir, "extensions")
    ext_dst = os.path.join(resources_dir, "extensions")
    if os.path.exists(ext_src):
        for item in os.listdir(ext_src):
            src_path = os.path.join(ext_src, item)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, ext_dst)
                print(f"  ✓ extensions/{item}")
    
    print()
    print("=" * 50)
    print("✅ Сборка завершена!")
    print("=" * 50)
    print()
    print(f"Дистрибутив: {dist_dir}")
    print()
    print("Содержимое:")
    print("  - MultiWindowSelenium.exe")
    print("  - resources/")
    print("      - yandexdriver.exe")
    print("      - extensions/")
    print("      - chrome_profile_clones/")
    print("      - yandex_profile_clones/")
    print()
    print("Примечание: Профили chrome_profile и yandex_profile")
    print("создаются пользователем самостоятельно при первом запуске с count=1")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

