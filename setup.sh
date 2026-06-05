#!/usr/bin/env bash
# One-shot install for clap_detector.py

set -euo pipefail

echo "=== Установка Clap Detector ==="

# System audio library (PortAudio — required by sounddevice)
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y portaudio19-dev python3-pip
elif command -v dnf &>/dev/null; then
    sudo dnf install -y portaudio-devel python3-pip
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm portaudio python-pip
fi

# Python deps
pip install --user -r requirements.txt

echo ""
echo "=== Готово! Запуск ==="
echo "  python3 clap_detector.py"
echo ""
echo "Настройка (если порог срабатывает не на хлопки):"
echo "  Отредактируй CLAP_THRESHOLD в clap_detector.py"
echo "  0.18 — умолчание. Меньше = чувствительнее."
