@echo off
chcp 65001 >nul
mode con: cols=80 lines=30
echo ========================================
echo Сборка Multi-Window Selenium Launcher
echo ========================================
echo.

REM Проверка виртуального окружения
if not exist venv (
    echo [1/5] Создание виртуального окружения...
    python -m venv venv
) else (
    echo [1/5] Виртуальное окружение найдено
)

echo [2/5] Активация виртуального окружения...
call venv\Scripts\activate.bat

echo [3/5] Установка зависимостей...
pip install -r requirements.txt --quiet

echo [4/5] Сборка exe файла...
pyinstaller build.spec --noconfirm

echo [5/5] Подготовка папки resources...

REM Создаём папку resources рядом с exe
if not exist dist\resources mkdir dist\resources
if not exist dist\resources\extensions mkdir dist\resources\extensions
if not exist dist\resources\chrome_profile_clones mkdir dist\resources\chrome_profile_clones
if not exist dist\resources\yandex_profile_clones mkdir dist\resources\yandex_profile_clones

REM Копируем yandexdriver.exe
if exist yandexdriver.exe (
    copy /Y yandexdriver.exe dist\resources\ >nul
    echo   - yandexdriver.exe скопирован
) else (
    echo   ! yandexdriver.exe не найден
)

REM Копируем расширения
if exist extensions\cryptopro.crx (
    copy /Y extensions\cryptopro.crx dist\resources\extensions\ >nul
    echo   - cryptopro.crx скопирован
)
if exist extensions\cryptopro.xpi (
    copy /Y extensions\cryptopro.xpi dist\resources\extensions\ >nul
    echo   - cryptopro.xpi скопирован
)

echo.
echo ========================================
echo Сборка завершена!
echo ========================================
echo.
echo Готовый дистрибутив находится в папке: dist\
echo.
echo Содержимое:
echo   - MultiWindowSelenium.exe
echo   - resources\
echo       - yandexdriver.exe
echo       - extensions\
echo       - chrome_profile_clones\
echo       - yandex_profile_clones\
echo.
echo Примечание: Профили chrome_profile и yandex_profile
echo создаются пользователем самостоятельно при первом запуске с count=1
echo.
pause

