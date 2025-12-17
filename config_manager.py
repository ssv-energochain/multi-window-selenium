"""
Менеджер конфигурации для сохранения настроек приложения.
"""
import json
import os
import sys
from typing import Optional


def get_config_path() -> str:
    """Возвращает путь к файлу конфигурации."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


class ConfigManager:
    """Менеджер для сохранения и загрузки настроек приложения."""
    
    DEFAULT_CONFIG = {
        "url": "",
        "save_url": False,
        "browser": "chrome",
        "window_count": 1,
        "window_width": 520,
        "window_height": 450,
        "window_x": None,
        "window_y": None
    }
    
    def __init__(self):
        self.config_path = get_config_path()
        self._config = self._load()
    
    def _load(self) -> dict:
        """Загружает конфигурацию из файла."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Объединяем с дефолтными значениями
                    return {**self.DEFAULT_CONFIG, **loaded}
            except (json.JSONDecodeError, IOError):
                pass
        return self.DEFAULT_CONFIG.copy()
    
    def save(self) -> None:
        """Сохраняет конфигурацию в файл."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    @property
    def url(self) -> str:
        """Возвращает сохранённый URL (или пустую строку если save_url=False)."""
        if self._config.get("save_url", False):
            return self._config.get("url", "")
        return ""
    
    @url.setter
    def url(self, value: str) -> None:
        """Устанавливает URL."""
        self._config["url"] = value
    
    @property
    def save_url(self) -> bool:
        """Возвращает флаг сохранения URL."""
        return self._config.get("save_url", False)
    
    @save_url.setter
    def save_url(self, value: bool) -> None:
        """Устанавливает флаг сохранения URL."""
        self._config["save_url"] = value
    
    @property
    def browser(self) -> str:
        """Возвращает выбранный браузер."""
        return self._config.get("browser", "chrome")
    
    @browser.setter
    def browser(self, value: str) -> None:
        """Устанавливает браузер."""
        self._config["browser"] = value
    
    @property
    def window_count(self) -> int:
        """Возвращает количество окон."""
        return self._config.get("window_count", 1)
    
    @window_count.setter
    def window_count(self, value: int) -> None:
        """Устанавливает количество окон."""
        self._config["window_count"] = max(1, value)
    
    @property
    def window_width(self) -> int:
        """Возвращает ширину окна."""
        return self._config.get("window_width", 520)
    
    @window_width.setter
    def window_width(self, value: int) -> None:
        """Устанавливает ширину окна."""
        self._config["window_width"] = max(400, value)
    
    @property
    def window_height(self) -> int:
        """Возвращает высоту окна."""
        return self._config.get("window_height", 450)
    
    @window_height.setter
    def window_height(self, value: int) -> None:
        """Устанавливает высоту окна."""
        self._config["window_height"] = max(300, value)
    
    @property
    def window_x(self) -> Optional[int]:
        """Возвращает позицию X окна."""
        return self._config.get("window_x")
    
    @window_x.setter
    def window_x(self, value: Optional[int]) -> None:
        """Устанавливает позицию X окна."""
        if value is not None:
            self._config["window_x"] = max(0, value)
        else:
            self._config["window_x"] = None
    
    @property
    def window_y(self) -> Optional[int]:
        """Возвращает позицию Y окна."""
        return self._config.get("window_y")
    
    @window_y.setter
    def window_y(self, value: Optional[int]) -> None:
        """Устанавливает позицию Y окна."""
        if value is not None:
            self._config["window_y"] = max(0, value)
        else:
            self._config["window_y"] = None
    
    def update_and_save(self, url: str, save_url: bool, browser: str, window_count: int) -> None:
        """Обновляет все настройки и сохраняет в файл."""
        self.url = url
        self.save_url = save_url
        self.browser = browser
        self.window_count = window_count
        self.save()
    
    def save_window_geometry(self, width: int, height: int, x: int, y: int) -> None:
        """Сохраняет размер и положение окна."""
        self.window_width = width
        self.window_height = height
        self.window_x = x
        self.window_y = y
        self.save()

