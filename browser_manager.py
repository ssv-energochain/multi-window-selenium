"""
Менеджер браузеров для GUI приложения.
Управляет запуском, остановкой и очисткой браузеров.
"""
import os
import sys
import shutil
import uuid
import time
import threading
import ctypes
import subprocess
from typing import Callable, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def get_base_path() -> str:
    """Возвращает базовую директорию приложения (для exe и для разработки)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resources_path() -> str:
    """Возвращает путь к папке resources."""
    base = get_base_path()
    resources = os.path.join(base, "resources")
    if os.path.exists(resources):
        return resources
    # Для разработки - ресурсы в корне проекта
    return base


def get_short_path(long_path: str) -> str:
    """Получает короткий путь (8.3 формат) в Windows для длинных путей."""
    if sys.platform != "win32":
        return long_path
    
    try:
        # Используем GetShortPathNameW для получения короткого пути
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_unicode_buffer(260)
        result = kernel32.GetShortPathNameW(long_path, buffer, 260)
        if result > 0:
            return buffer.value
    except Exception:
        pass
    
    return long_path


def _make_long_path(path: str) -> str:
    """Добавляет префикс \\?\ для поддержки длинных путей в Windows."""
    if sys.platform != "win32":
        return path
    
    # Если путь уже имеет префикс, возвращаем как есть
    if path.startswith("\\\\?\\"):
        return path
    
    # Преобразуем относительный путь в абсолютный
    abs_path = os.path.abspath(path)
    
    # Добавляем префикс для длинных путей
    if abs_path.startswith("\\\\"):
        # UNC путь - используем \\?\UNC\
        return "\\\\?\\UNC\\" + abs_path[2:]
    else:
        # Обычный путь - используем \\?\
        return "\\\\?\\" + abs_path


def copytree_long_path(src: str, dst: str, dirs_exist_ok: bool = False) -> None:
    """Копирует дерево директорий с поддержкой длинных путей в Windows."""
    if sys.platform == "win32":
        # Используем robocopy для Windows, который поддерживает длинные пути
        try:
            # Создаем целевую директорию
            os.makedirs(dst, exist_ok=True)
            
            # Используем robocopy с поддержкой длинных путей
            # /E - копировать все поддиректории, включая пустые
            # /COPYALL - копировать все атрибуты файлов
            # /R:3 - 3 попытки при ошибках
            # /W:1 - ждать 1 секунду между попытками
            # /NFL - не логировать имена файлов
            # /NDL - не логировать имена директорий
            # /NP - не показывать прогресс
            result = subprocess.run(
                ["robocopy", src, dst, "/E", "/COPYALL", "/R:3", "/W:1", "/NFL", "/NDL", "/NP"],
                capture_output=True,
                text=True,
                timeout=300  # 5 минут максимум
            )
            
            # robocopy возвращает коды 0-7 как успешные (0 = нет файлов для копирования, 1-7 = успешно скопировано)
            if result.returncode > 7:
                # Если robocopy не сработал, пробуем стандартный способ
                raise subprocess.CalledProcessError(result.returncode, "robocopy")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Если robocopy недоступен или не сработал, пробуем стандартный способ
            try:
                shutil.copytree(src, dst, dirs_exist_ok=dirs_exist_ok)
            except OSError as e:
                # Если стандартный способ тоже не работает из-за длинных путей,
                # пробуем рекурсивное копирование с обработкой длинных путей
                _copytree_with_long_paths(src, dst, dirs_exist_ok)
    else:
        # Для не-Windows используем стандартный способ
        shutil.copytree(src, dst, dirs_exist_ok=dirs_exist_ok)


def _copytree_with_long_paths(src: str, dst: str, dirs_exist_ok: bool) -> None:
    """Рекурсивное копирование с обработкой длинных путей для проблемных файлов."""
    os.makedirs(dst, exist_ok=True)
    
    try:
        items = os.listdir(src)
    except (PermissionError, OSError):
        return
    
    for item in items:
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)
        
        try:
            if os.path.isdir(src_path):
                _copytree_with_long_paths(src_path, dst_path, dirs_exist_ok)
            else:
                try:
                    shutil.copy2(src_path, dst_path)
                except (OSError, IOError) as e:
                    # Если путь слишком длинный, используем длинный путь
                    if sys.platform == "win32" and len(src_path) > 260:
                        try:
                            src_file_long = _make_long_path(src_path)
                            dst_file_long = _make_long_path(dst_path)
                            # Создаем директорию для файла
                            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                            # Копируем файл
                            with open(src_file_long, 'rb') as fsrc:
                                with open(dst_file_long, 'wb') as fdst:
                                    shutil.copyfileobj(fsrc, fdst)
                            # Копируем метаданные (стараемся использовать обычный путь)
                            try:
                                shutil.copystat(src_path, dst_path)
                            except:
                                pass
                        except Exception:
                            # Пропускаем проблемный файл
                            pass
                    else:
                        raise
        except Exception:
            # Пропускаем проблемные файлы/папки
            continue


class BrowserManager:
    """Менеджер для управления браузерами Selenium."""
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        """
        Args:
            status_callback: Функция для отправки статусных сообщений в UI
        """
        self.drivers: List[webdriver.Remote] = []
        self.temp_profiles: List[str] = []
        self.status_callback = status_callback or print
        self._running = False
        self._lock = threading.Lock()
    
    def _log(self, message: str) -> None:
        """Отправляет сообщение в UI."""
        self.status_callback(message)
    
    def _cleanup_chrome_profile(self, profile_path: str) -> None:
        """Удаляет файлы блокировок профиля Chrome/Yandex."""
        os.makedirs(profile_path, exist_ok=True)
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonCookies", "DevToolsActivePort"):
            lock_path = os.path.join(profile_path, lock_name)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
    
    def _get_chrome_profile_path(self) -> str:
        """Возвращает путь к базовому профилю Chrome."""
        return os.path.join(get_resources_path(), "chrome_profile")
    
    def _get_yandex_profile_path(self) -> str:
        """Возвращает путь к базовому профилю Yandex."""
        return os.path.join(get_resources_path(), "yandex_profile")
    
    def _get_chrome_clones_path(self) -> str:
        """Возвращает путь к папке клонов профилей Chrome."""
        return os.path.join(get_resources_path(), "chrome_profile_clones")
    
    def _get_yandex_clones_path(self) -> str:
        """Возвращает путь к папке клонов профилей Yandex."""
        return os.path.join(get_resources_path(), "yandex_profile_clones")
    
    def _prepare_chrome_profile(self, instance_index: int) -> str:
        """Создает изолированную копию профиля Chrome."""
        base_profile = self._get_chrome_profile_path()
        clones_root = self._get_chrome_clones_path()
        os.makedirs(clones_root, exist_ok=True)
        
        profile_clone = os.path.join(clones_root, f"profile_{instance_index}_{uuid.uuid4().hex}")
        copytree_long_path(base_profile, profile_clone, dirs_exist_ok=True)
        self._cleanup_chrome_profile(profile_clone)
        
        return profile_clone
    
    def _prepare_yandex_profile(self, instance_index: int) -> str:
        """Создает изолированную копию профиля Yandex."""
        base_profile = self._get_yandex_profile_path()
        clones_root = self._get_yandex_clones_path()
        os.makedirs(clones_root, exist_ok=True)
        
        profile_clone = os.path.join(clones_root, f"profile_{instance_index}_{uuid.uuid4().hex}")
        copytree_long_path(base_profile, profile_clone, dirs_exist_ok=True)
        self._cleanup_chrome_profile(profile_clone)
        
        return profile_clone
    
    def _create_chrome_driver(self, profile_path: str) -> webdriver.Chrome:
        """Создает драйвер Chrome."""
        options = ChromeOptions()
        
        # Нормализуем и делаем абсолютным путь
        profile_path = os.path.abspath(os.path.normpath(profile_path))
        os.makedirs(profile_path, exist_ok=True)
        
        # Если путь слишком длинный (> 200 символов), используем короткий путь
        if len(profile_path) > 200:
            profile_path = get_short_path(profile_path)
        
        # Используем нормализованный путь
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
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=0")
        
        # Скрываем признаки автоматизации
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path)
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
    
    def _create_firefox_driver(self) -> webdriver.Firefox:
        """Создает драйвер Firefox."""
        extensions_path = os.path.join(get_resources_path(), "extensions", "cryptopro.xpi")
        options = FirefoxOptions()
        
        driver_path = GeckoDriverManager().install()
        service = FirefoxService(driver_path)
        driver = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        
        # Установка расширения если существует
        if os.path.exists(extensions_path):
            driver.install_addon(extensions_path, temporary=True)
        
        return driver
    
    def _create_yandex_driver(self, profile_path: str) -> webdriver.Chrome:
        """Создает драйвер Yandex Browser."""
        options = ChromeOptions()
        
        # Нормализуем и делаем абсолютным путь
        profile_path = os.path.abspath(os.path.normpath(profile_path))
        os.makedirs(profile_path, exist_ok=True)
        
        # Если путь слишком длинный (> 200 символов), используем короткий путь
        if len(profile_path) > 200:
            profile_path = get_short_path(profile_path)
        
        # Используем нормализованный путь
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
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=0")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        yandex_driver_path = os.path.join(get_resources_path(), "yandexdriver.exe")
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
    
    def start(self, url: str, count: int, browser_type: str) -> bool:
        """
        Запускает указанное количество окон браузера.
        
        Args:
            url: URL для открытия
            count: Количество окон
            browser_type: Тип браузера ('chrome', 'firefox', 'yandex')
            
        Returns:
            True если запуск успешен, False в случае ошибки
        """
        with self._lock:
            if self._running:
                self._log("⚠️ Браузеры уже запущены")
                return False
            self._running = True
        
        self._log(f"🚀 Запуск {count} окон {browser_type}...")
        
        try:
            for i in range(count):
                self._log(f"Открываю окно {i + 1}/{count}...")
                
                if browser_type.lower() == "chrome":
                    if count == 1:
                        profile_path = self._get_chrome_profile_path()
                        use_base = True
                    else:
                        profile_path = self._prepare_chrome_profile(i)
                        use_base = False
                    
                    try:
                        driver = self._create_chrome_driver(profile_path)
                    except Exception as e:
                        error_msg = str(e)
                        if "invalid argument" in error_msg.lower():
                            self._log(f"⚠️ Путь к профилю: {profile_path}")
                            self._log(f"⚠️ Длина пути: {len(profile_path)} символов")
                        if not use_base:
                            shutil.rmtree(profile_path, ignore_errors=True)
                        raise
                    
                    if not use_base:
                        self.temp_profiles.append(profile_path)
                
                elif browser_type.lower() == "yandex":
                    if count == 1:
                        profile_path = self._get_yandex_profile_path()
                        use_base = True
                    else:
                        profile_path = self._prepare_yandex_profile(i)
                        use_base = False
                    
                    try:
                        driver = self._create_yandex_driver(profile_path)
                    except Exception:
                        if not use_base:
                            shutil.rmtree(profile_path, ignore_errors=True)
                        raise
                    
                    if not use_base:
                        self.temp_profiles.append(profile_path)
                
                elif browser_type.lower() == "firefox":
                    driver = self._create_firefox_driver()
                else:
                    raise ValueError(f"Неподдерживаемый браузер: {browser_type}")
                
                driver.get(url)
                self.drivers.append(driver)
                self._log(f"✓ Окно {i + 1} открыто")
            
            self._log(f"✅ Успешно открыто {len(self.drivers)} окон")
            return True
            
        except Exception as e:
            self._log(f"❌ Ошибка: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Закрывает все открытые браузеры и удаляет временные профили."""
        self._log("🛑 Закрытие браузеров...")
        
        closed = 0
        for i, driver in enumerate(self.drivers):
            try:
                driver.quit()
                closed += 1
            except Exception as e:
                self._log(f"Не удалось закрыть окно {i + 1}: {e}")
        
        self.drivers.clear()
        
        # Удаление временных профилей
        if self.temp_profiles:
            self._log(f"Удаление {len(self.temp_profiles)} временных профилей...")
            time.sleep(0.5)
            
            for profile_path in self.temp_profiles:
                self._remove_profile_with_retry(profile_path)
            
            self.temp_profiles.clear()
        
        with self._lock:
            self._running = False
        
        self._log(f"✅ Закрыто {closed} окон")
    
    def _remove_profile_with_retry(self, profile_path: str, retries: int = 3) -> None:
        """Удаляет профиль с повторными попытками."""
        for attempt in range(retries):
            try:
                shutil.rmtree(profile_path)
                break
            except Exception:
                if attempt < retries - 1:
                    time.sleep(0.5)
    
    def cleanup_clones(self) -> tuple[int, int]:
        """
        Удаляет все клоны профилей Chrome и Yandex.
        
        Returns:
            Кортеж (удалено_chrome, удалено_yandex)
        """
        self._log("🧹 Очистка клонов профилей...")
        
        chrome_deleted = self._cleanup_clones_folder(self._get_chrome_clones_path())
        yandex_deleted = self._cleanup_clones_folder(self._get_yandex_clones_path())
        
        total = chrome_deleted + yandex_deleted
        if total > 0:
            self._log(f"✅ Удалено {total} клонов (Chrome: {chrome_deleted}, Yandex: {yandex_deleted})")
        else:
            self._log("✅ Клоны профилей отсутствуют")
        
        return chrome_deleted, yandex_deleted
    
    def _cleanup_clones_folder(self, clones_path: str) -> int:
        """Удаляет все папки внутри указанной директории клонов."""
        if not os.path.exists(clones_path):
            return 0
        
        deleted = 0
        for item in os.listdir(clones_path):
            item_path = os.path.join(clones_path, item)
            if os.path.isdir(item_path):
                try:
                    shutil.rmtree(item_path)
                    deleted += 1
                except Exception as e:
                    self._log(f"Не удалось удалить {item}: {e}")
        
        return deleted
    
    @property
    def is_running(self) -> bool:
        """Возвращает True если браузеры запущены."""
        with self._lock:
            return self._running

