@echo off
echo === iOS Calculator Setup ===
echo.

cd /d "%~dp0"

echo Установка зависимостей...
call npm install

if %errorlevel% neq 0 (
    echo.
    echo ОШИБКА при установке. Проверь подключение к интернету.
    pause
    exit /b
)

echo.
echo Запуск сервера...
echo Когда появится QR-код — сканируй его через Expo Go на телефоне.
echo.
call npx expo start

pause
