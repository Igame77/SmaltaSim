@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Запуск тренажера-симулятора Vkm.ComplexSim (PyGame)...
uv run python main.py
if errorlevel 1 (
    echo Ошибка при запуске. Убедитесь, что uv установлен или запустите через python.
    pause
)
