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
import time


# ========== НАСТРОЙКИ ПО УМОЛЧАНИЮ (можно изменить здесь) ==========
DEFAULT_URL = "https://google.com"
# DEFAULT_URL = "https://platform-portal-feature-business-trips.kube.energochain.ru/portal/login"
DEFAULT_WINDOWS_COUNT = 1
DEFAULT_BROWSER = "firefox"
# ====================================================================


def normalize_url(url: str) -> str:
    """Нормализует URL, добавляя протокол если его нет."""
    url = url.strip()
    if not url:
        return url
    
    # Проверяем наличие протокола
    if not url.startswith(("http://", "https://", "file://")):
        # Если протокола нет, добавляем https://
        url = f"https://{url}"
    
    return url


def cleanup_chrome_profile(profile_path: str) -> None:
    """Удаляет файлы блокировок и другие временные артефакты профиля Chrome."""
    os.makedirs(profile_path, exist_ok=True)
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonCookies", "DevToolsActivePort"):
        lock_path = os.path.join(profile_path, lock_name)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass


def get_base_chrome_profile() -> str:
    """Возвращает путь к основному профилю Chrome и подчищает его артефакты."""
    base_profile = os.path.abspath(os.path.join(os.path.dirname(__file__), "chrome_profile"))
    # cleanup_chrome_profile(base_profile)
    return base_profile


def prepare_chrome_profile(instance_index: int) -> str:
    """Создает изолированную копию профиля Chrome для параллельного окна."""
    base_profile = get_base_chrome_profile()

    clones_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "chrome_profile_clones"))
    os.makedirs(clones_root, exist_ok=True)

    profile_clone = os.path.join(clones_root, f"profile_{instance_index}_{uuid.uuid4().hex}")
    shutil.copytree(base_profile, profile_clone, dirs_exist_ok=True)
    cleanup_chrome_profile(profile_clone)

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
    
    # Скрываем признаки автоматизации
    options_chrome.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options_chrome.add_experimental_option("useAutomationExtension", False)
    options_chrome.add_argument("--disable-blink-features=AutomationControlled")

    driver_path = ChromeDriverManager().install()
    if not isinstance(driver_path, str):
        raise TypeError(f"Путь к драйверу должен быть строкой, получен {type(driver_path)}: {driver_path}")
    
    service = ChromeService(driver_path)
    driver = webdriver.Chrome(service=service, options=options_chrome)
    
    # Агрессивное скрытие всех признаков автоматизации через CDP
    stealth_script = """
        // Удаляем navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Восстанавливаем navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Восстанавливаем navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Добавляем window.chrome
        window.chrome = {
            runtime: {}
        };
        
        // Переопределяем permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Переопределяем getParameter для WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
    """
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": stealth_script
    })
    
    return driver


def create_firefox_driver():
    """Создает драйвер Firefox с использованием готового профиля"""
    firefox_extensions = [os.path.abspath(os.path.join(os.path.dirname(__file__), "extensions", "cryptopro.xpi"))]
    options = FirefoxOptions()
    # Убрал Chrome-аргумент, который ломал Firefox
    
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


def get_base_yandex_profile() -> str:
    """Возвращает путь к основному профилю Yandex и подчищает его артефакты."""
    base_profile = os.path.abspath(os.path.join(os.path.dirname(__file__), "yandex_profile"))
    return base_profile


def prepare_yandex_profile(instance_index: int) -> str:
    """Создает изолированную копию профиля Yandex для параллельного окна."""
    base_profile = get_base_yandex_profile()

    clones_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "yandex_profile_clones"))
    os.makedirs(clones_root, exist_ok=True)

    profile_clone = os.path.join(clones_root, f"profile_{instance_index}_{uuid.uuid4().hex}")
    shutil.copytree(base_profile, profile_clone, dirs_exist_ok=True)
    cleanup_chrome_profile(profile_clone)  # Yandex использует те же файлы блокировок

    return profile_clone


def create_yandex_driver(profile_path: str):
    """Создает драйвер Yandex Browser на основе указанного профиля.
    
    YandexDriver - это форк ChromeDriver, поэтому используем ChromeOptions.
    """
    options = ChromeOptions()
    os.makedirs(profile_path, exist_ok=True)

    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-features=DisableLoadExtensionCommandLineSwitch")
    options.add_argument("--disable-extensions-file-access-check")
    options.add_argument("--disable-features=ExtensionsToolbarMenu")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    
    # Убираем плашку "управляет автоматизированное ПО"
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Путь к yandexdriver.exe в корне проекта
    yandex_driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "yandexdriver.exe"))
    
    if not os.path.exists(yandex_driver_path):
        raise FileNotFoundError(f"YandexDriver не найден: {yandex_driver_path}")

    service = ChromeService(yandex_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Агрессивное скрытие всех признаков автоматизации через CDP
    stealth_script = """
        // Удаляем navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Восстанавливаем navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Восстанавливаем navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Добавляем window.chrome
        window.chrome = {
            runtime: {}
        };
        
        // Переопределяем permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Переопределяем getParameter для WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
    """
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": stealth_script
    })
    
    return driver


def open_browser_windows(url, count, browser_type="chrome"):
    """
    Открывает указанное количество окон браузера
    
    Args:
        url: URL для открытия
        count: количество окон
        browser_type: тип браузера ('chrome', 'firefox' или 'yandex')
    """
    drivers = []
    temp_profiles = []  # Временные профили для Chrome/Yandex
    
    print(f"Открываю {count} окон браузера {browser_type} с URL: {url}")
    try:
        for i in range(count):
            print(f"Открываю окно {i + 1}/{count}...")
            
            if browser_type.lower() == "chrome":
                use_base_profile = False
                if count == 1:
                    profile_path = get_base_chrome_profile()
                    print(f"profile_path: {profile_path}")
                    use_base_profile = True
                else:
                    profile_path = prepare_chrome_profile(i)
                    print(f"profile_path: {profile_path}")
                try:
                    driver = create_chrome_driver(profile_path)
                except Exception:
                    if not use_base_profile:
                        shutil.rmtree(profile_path, ignore_errors=True)
                    raise
                if not use_base_profile:
                    temp_profiles.append(profile_path)
                    
            elif browser_type.lower() == "yandex":
                use_base_profile = False
                if count == 1:
                    profile_path = get_base_yandex_profile()
                    print(f"profile_path: {profile_path}")
                    use_base_profile = True
                else:
                    profile_path = prepare_yandex_profile(i)
                    print(f"profile_path: {profile_path}")
                try:
                    driver = create_yandex_driver(profile_path)
                except Exception:
                    if not use_base_profile:
                        shutil.rmtree(profile_path, ignore_errors=True)
                    raise
                if not use_base_profile:
                    temp_profiles.append(profile_path)
                    
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

        # Даём время на освобождение файлов после закрытия браузеров
        if temp_profiles:
            print(f"Удаляю {len(temp_profiles)} временных профилей...")
            time.sleep(1)
            
        for profile_path in temp_profiles:
            # Retry механизм для Windows - файлы могут быть заблокированы
            for attempt in range(3):
                try:
                    shutil.rmtree(profile_path)
                    print(f"  ✓ Удалён: {os.path.basename(profile_path)}")
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        print(f"  ✗ Не удалось удалить {profile_path}: {e}")

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
        choices=["chrome", "firefox", "yandex"],
        default=DEFAULT_BROWSER,
        help=f"Тип браузера: chrome, firefox или yandex (по умолчанию: {DEFAULT_BROWSER})"
    )
    
    args = parser.parse_args()
    
    # Используем значения из аргументов или значения по умолчанию
    url = normalize_url(args.url)  # Нормализуем URL (добавляем протокол если нужно)
    count = args.count
    browser = args.browser
    
    open_browser_windows(url, count, browser)


if __name__ == "__main__":
    main()

