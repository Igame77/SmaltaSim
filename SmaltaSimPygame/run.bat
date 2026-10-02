@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Запуск тренажера-симулятора Vkm.ComplexSim (PyGame)...

where uv >nul 2>nul
if %errorlevel% equ 0 (
    uv run python main.py
    if %errorlevel% equ 0 goto :eof
)

python main.py
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить симулятор.
    echo Убедитесь, что установлен Python и библиотека pygame-ce:
    echo   pip install pygame-ce
    echo Или запустите готовый автономный файл SmaltaSim.exe
    pause
)
