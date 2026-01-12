"""
GUI приложение для управления браузерами Selenium.
"""
import customtkinter as ctk
import threading
from browser_manager import BrowserManager
from config_manager import ConfigManager


class BrowserLauncherApp(ctk.CTk):
    """Главное окно приложения."""
    
    BROWSERS = ["Chrome", "Firefox", "Yandex"]
    
    def __init__(self):
        super().__init__()
        
        # Менеджеры
        self.config = ConfigManager()
        
        # Настройка окна
        self.title("Multi-Window Selenium Launcher")
        self._restore_window_geometry()
        self.resizable(True, True)
        
        # Получаем текущую ширину окна и устанавливаем её как минимальную высоту
        self.update_idletasks()  # Обновляем для получения актуальных размеров
        current_width = self.winfo_width()
        self.minsize(400, current_width)
        
        # Тёмная тема
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.browser_manager = BrowserManager(status_callback=self._update_status)
        
        # UI
        self._create_widgets()
        self._load_settings()
        
        # Отслеживание изменений размера и положения окна
        self.bind("<Configure>", self._on_window_configure)
        
        # Обработка закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """Создаёт все виджеты интерфейса."""
        # Основной контейнер
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # === URL ===
        url_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        url_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(url_frame, text="URL страницы:", font=("Segoe UI", 13)).pack(anchor="w")
        
        url_input_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_input_frame.pack(fill="x", pady=(5, 0))
        
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="https://example.com", height=36)
        self.url_entry.pack(side="left", fill="x", expand=True)
        
        self.smoke_btn = ctk.CTkButton(
            url_input_frame,
            text="смоки",
            command=self._on_smoke_click,
            height=36,
            width=80,
            fg_color="#5a5a5a",
            hover_color="#454545"
        )
        self.smoke_btn.pack(side="left", padx=(10, 0))
        
        self.save_url_var = ctk.BooleanVar(value=False)
        self.save_url_checkbox = ctk.CTkCheckBox(
            url_input_frame, 
            text="Сохранять", 
            variable=self.save_url_var,
            width=100,
            checkbox_width=20,
            checkbox_height=20
        )
        self.save_url_checkbox.pack(side="right", padx=(10, 0))
        
        # === Количество окон ===
        count_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        count_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(count_frame, text="Количество окон:", font=("Segoe UI", 13)).pack(anchor="w")
        
        self.count_var = ctk.StringVar(value="1")
        self.count_entry = ctk.CTkEntry(
            count_frame, 
            textvariable=self.count_var,
            height=36,
            width=100
        )
        self.count_entry.pack(anchor="w", pady=(5, 0))
        
        # Валидация ввода - только цифры
        self.count_var.trace_add("write", self._validate_count)
        
        # === Выбор браузера ===
        browser_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        browser_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(browser_frame, text="Браузер:", font=("Segoe UI", 13)).pack(anchor="w")
        
        self.browser_var = ctk.StringVar(value="Chrome")
        self.browser_combo = ctk.CTkComboBox(
            browser_frame,
            values=self.BROWSERS,
            variable=self.browser_var,
            height=36,
            width=200,
            state="readonly"
        )
        self.browser_combo.pack(anchor="w", pady=(5, 0))
        
        # === Кнопки ===
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 15))
        
        self.start_btn = ctk.CTkButton(
            buttons_frame, 
            text="▶ Старт", 
            command=self._on_start,
            height=40,
            fg_color="#2d8c3c",
            hover_color="#236b2f"
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.stop_btn = ctk.CTkButton(
            buttons_frame, 
            text="■ Стоп", 
            command=self._on_stop,
            height=40,
            fg_color="#c9302c",
            hover_color="#a02622",
            state="disabled"
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=5)
        
        self.cleanup_btn = ctk.CTkButton(
            buttons_frame, 
            text="🧹 Очистка", 
            command=self._on_cleanup,
            height=40,
            fg_color="#5a5a5a",
            hover_color="#454545"
        )
        self.cleanup_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        # === Статус ===
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        ctk.CTkLabel(status_frame, text="Статус:", font=("Segoe UI", 12)).pack(anchor="w", padx=5, pady=(5, 0))
        
        self.status_text = ctk.CTkTextbox(
            status_frame, 
            height=120,
            font=("Consolas", 10),
            state="disabled",
            wrap="word"
        )
        self.status_text.pack(fill="both", expand=True, padx=5, pady=(5, 5))
        
        # Начальное сообщение
        self._update_status("Готов к работе. Введите параметры и нажмите 'Старт'.")
    
    def _restore_window_geometry(self):
        """Восстанавливает размер и положение окна из конфига."""
        width = self.config.window_width
        height = self.config.window_height
        x = self.config.window_x
        y = self.config.window_y
        
        if x is not None and y is not None:
            self.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.geometry(f"{width}x{height}")
    
    def _on_window_configure(self, event):
        """Обработчик изменения размера или положения окна."""
        # Сохраняем только если это изменение главного окна (не дочерних виджетов)
        if event.widget == self:
            # Используем after для отложенного сохранения, чтобы не спамить при каждом изменении
            if not hasattr(self, '_geometry_save_scheduled'):
                self._geometry_save_scheduled = True
                self.after(500, self._save_window_geometry)
    
    def _save_window_geometry(self):
        """Сохраняет текущий размер и положение окна."""
        try:
            width = self.winfo_width()
            height = self.winfo_height()
            x = self.winfo_x()
            y = self.winfo_y()
            
            self.config.save_window_geometry(width, height, x, y)
        finally:
            self._geometry_save_scheduled = False
    
    def _load_settings(self):
        """Загружает настройки из конфигурации."""
        self.url_entry.insert(0, self.config.url)
        self.save_url_var.set(self.config.save_url)
        self.count_var.set(str(self.config.window_count))
        
        # Браузер - преобразуем в правильный регистр для ComboBox
        browser = self.config.browser.capitalize()
        if browser in self.BROWSERS:
            self.browser_var.set(browser)
    
    def _save_settings(self):
        """Сохраняет текущие настройки."""
        try:
            count = int(self.count_var.get() or "1")
        except ValueError:
            count = 1
        
        self.config.update_and_save(
            url=self.url_entry.get(),
            save_url=self.save_url_var.get(),
            browser=self.browser_var.get().lower(),
            window_count=count
        )
    
    def _validate_count(self, *args):
        """Валидация поля количества окон - только цифры."""
        value = self.count_var.get()
        # Оставляем только цифры
        filtered = ''.join(c for c in value if c.isdigit())
        if filtered != value:
            self.count_var.set(filtered)
    
    def _normalize_url(self, url: str) -> str:
        """Нормализует URL, добавляя протокол если его нет."""
        url = url.strip()
        if not url:
            return url
        
        # Проверяем наличие протокола
        if not url.startswith(("http://", "https://", "file://")):
            # Если протокола нет, добавляем https://
            url = f"https://{url}"
        
        return url
    
    def _get_validated_inputs(self) -> tuple[str, int, str] | None:
        """Проверяет и возвращает введённые данные или None при ошибке."""
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("❌ Введите URL страницы")
            return None
        
        # Нормализуем URL (добавляем протокол если нужно)
        url = self._normalize_url(url)
        
        try:
            count = int(self.count_var.get() or "0")
            if count < 1:
                self._update_status("❌ Количество окон должно быть >= 1")
                return None
        except ValueError:
            self._update_status("❌ Введите корректное число окон")
            return None
        
        browser = self.browser_var.get()
        if not browser:
            self._update_status("❌ Выберите браузер")
            return None
        
        return url, count, browser.lower()
    
    def _update_status(self, message: str):
        """Обновляет статусное поле (thread-safe)."""
        def update():
            self.status_text.configure(state="normal")
            self.status_text.insert("end", message + "\n")
            self.status_text.see("end")
            self.status_text.configure(state="disabled")
        
        # Если вызов из другого потока
        if threading.current_thread() is not threading.main_thread():
            self.after(0, update)
        else:
            update()
    
    def _set_buttons_state(self, running: bool):
        """Устанавливает состояние кнопок."""
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.cleanup_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.cleanup_btn.configure(state="normal")
    
    def _on_start(self):
        """Обработчик кнопки Старт."""
        inputs = self._get_validated_inputs()
        if not inputs:
            return
        
        url, count, browser = inputs
        
        # Обновляем поле ввода нормализованным URL
        current_url = self.url_entry.get().strip()
        normalized = self._normalize_url(current_url)
        if normalized != current_url:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, normalized)
        
        self._save_settings()
        self._set_buttons_state(running=True)
        
        # Запуск в отдельном потоке чтобы не блокировать UI
        def start_browsers():
            success = self.browser_manager.start(url, count, browser)
            if not success:
                self.after(0, lambda: self._set_buttons_state(running=False))
        
        threading.Thread(target=start_browsers, daemon=True).start()
    
    def _on_stop(self):
        """Обработчик кнопки Стоп."""
        def stop_browsers():
            self.browser_manager.stop()
            self.after(0, lambda: self._set_buttons_state(running=False))
        
        threading.Thread(target=stop_browsers, daemon=True).start()
    
    def _on_cleanup(self):
        """Обработчик кнопки Очистка."""
        def cleanup():
            self.browser_manager.cleanup_clones()
        
        threading.Thread(target=cleanup, daemon=True).start()
    
    def _on_smoke_click(self):
        """Обработчик кнопки смоки - заменяет URL на smoke test адрес."""
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, "https://platform-app-feature-smoke-tests.kube.energochain.ru/portal/login")
    
    def _on_closing(self):
        """Обработчик закрытия окна."""
        self._save_settings()
        self._save_window_geometry()
        if self.browser_manager.is_running:
            self.browser_manager.stop()
        self.destroy()


def main():
    app = BrowserLauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()

