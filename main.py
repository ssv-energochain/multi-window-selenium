"""
Скрипт для открытия нескольких независимых окон браузера с помощью Selenium
"""
import argparse
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import os
import shutil
import uuid


# ========== НАСТРОЙКИ ПО УМОЛЧАНИЮ (можно изменить здесь) ==========
DEFAULT_URL = "https://www.google.com/"
DEFAULT_WINDOWS_COUNT = 2
DEFAULT_BROWSER = "chrome"
# ====================================================================


def prepare_chrome_profile(instance_index: int) -> str:
    """Создает изолированную копию профиля Chrome для параллельного окна."""
    base_profile = os.path.abspath(os.path.join(os.path.dirname(__file__), "chrome_profile"))
    os.makedirs(base_profile, exist_ok=True)

    clones_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "chrome_profile_clones"))
    os.makedirs(clones_root, exist_ok=True)

    profile_clone = os.path.join(clones_root, f"profile_{instance_index}_{uuid.uuid4().hex}")
    shutil.copytree(base_profile, profile_clone, dirs_exist_ok=True)

    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonCookies", "DevToolsActivePort"):
        lock_path = os.path.join(profile_clone, lock_name)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass

    return profile_clone


def create_chrome_driver(profile_path: str):
    """Создает драйвер Chrome на основе указанного профиля"""
    options_chrome = ChromeOptions()
    # Указываем путь к профилю
    os.makedirs(profile_path, exist_ok=True)

    options_chrome.add_argument(f"--user-data-dir={profile_path}")
    options_chrome.add_argument("--profile-directory=Default")
    options_chrome.add_argument("--start-maximized")
    options_chrome.add_argument("--disable-infobars")
    options_chrome.add_argument("--disable-features=DisableLoadExtensionCommandLineSwitch")
    
    options_chrome.add_argument("--disable-extensions-file-access-check")
    options_chrome.add_argument("--disable-features=ExtensionsToolbarMenu")
    options_chrome.add_argument("--allow-running-insecure-content")
    options_chrome.add_argument("--no-first-run")
    options_chrome.add_argument("--no-default-browser-check")

    driver_path = ChromeDriverManager().install()
    if not isinstance(driver_path, str):
        raise TypeError(f"Путь к драйверу должен быть строкой, получен {type(driver_path)}: {driver_path}")
    
    service = ChromeService(driver_path)
    driver = webdriver.Chrome(service=service, options=options_chrome)
    return driver


def create_firefox_driver():
    """Создает драйвер Firefox с использованием готового профиля"""
    firefox_extensions = [os.path.abspath(os.path.join(os.path.dirname(__file__), "extensions", "cryptopro.xpi"))]
    options = FirefoxOptions()
    options.add_argument('--disable-features=DisableLoadExtensionCommandLineSwitch')
    
    # Установка и проверка драйвера
    driver_path = GeckoDriverManager().install()
    if not isinstance(driver_path, str):
        raise TypeError(f"Путь к драйверу должен быть строкой, получен {type(driver_path)}: {driver_path}")
    
    service = FirefoxService(driver_path)
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()
    
    # Добавление расширений с проверками
    for extension in firefox_extensions:
        if not isinstance(extension, str):
            raise TypeError(f"Расширение должно быть строкой, получен {type(extension)}: {extension}")        
        if not extension.endswith('.xpi'):
            raise ValueError(f"Расширение Firefox должно быть .xpi файлом: {extension}")            
        if not os.path.exists(extension):
            raise FileNotFoundError(f"Файл расширения Firefox не найден: {extension}")
        
        driver.install_addon(extension, temporary=True)
    
    return driver


def open_browser_windows(url, count, browser_type="chrome"):
    """
    Открывает указанное количество окон браузера
    
    Args:
        url: URL для открытия
        count: количество окон
        browser_type: тип браузера ('chrome' или 'firefox')
    """
    drivers = []
    chrome_profiles = []
    
    print(f"Открываю {count} окон браузера {browser_type} с URL: {url}")
    
    try:
        for i in range(count):
            print(f"Открываю окно {i + 1}/{count}...")
            
            if browser_type.lower() == "chrome":
                profile_path = prepare_chrome_profile(i)
                try:
                    driver = create_chrome_driver(profile_path)
                except Exception:
                    shutil.rmtree(profile_path, ignore_errors=True)
                    raise
                chrome_profiles.append(profile_path)
            elif browser_type.lower() == "firefox":
                driver = create_firefox_driver()
            else:
                raise ValueError(f"Неподдерживаемый тип браузера: {browser_type}")
            
            driver.get(url)
            drivers.append(driver)
            print(f"Окно {i + 1} успешно открыто")
        
        print(f"\n✅ Успешно открыто {len(drivers)} окон")
        print("Нажмите Enter для закрытия всех окон...")
        
        # Улучшенная обработка ожидания
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("\nПолучен сигнал прерывания...")
        
    except Exception as e:
        import traceback
        print(f"❌ Ошибка при открытии окон: {e}")
        traceback.print_exc()
        
    finally:
        # Закрываем все окна
        print("\nЗакрываю все окна...")
        successful_closes = 0
        for i, driver in enumerate(drivers):
            try:
                driver.quit()
                successful_closes += 1
            except Exception as e:
                print(f"Не удалось закрыть окно {i + 1}: {e}")

        for profile_path in chrome_profiles:
            try:
                shutil.rmtree(profile_path)
            except Exception as e:
                print(f"Не удалось удалить временный профиль Chrome {profile_path}: {e}")

        print(f"✅ Закрыто {successful_closes}/{len(drivers)} окон")


def main():
    """Главная функция с поддержкой аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Открывает несколько независимых окон браузера с помощью Selenium"
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        default=DEFAULT_URL,
        help=f"Branch link (по умолчанию: {DEFAULT_URL})"
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=DEFAULT_WINDOWS_COUNT,
        help=f"Количество окон (по умолчанию: {DEFAULT_WINDOWS_COUNT})"
    )
    parser.add_argument(
        "-b", "--browser",
        type=str,
        choices=["chrome", "firefox"],
        default=DEFAULT_BROWSER,
        help=f"Тип браузера: chrome или firefox (по умолчанию: {DEFAULT_BROWSER})"
    )
    
    args = parser.parse_args()
    
    # Используем значения из аргументов или значения по умолчанию
    url = args.url
    count = args.count
    browser = args.browser
    
    open_browser_windows(url, count, browser)


if __name__ == "__main__":
    main()

