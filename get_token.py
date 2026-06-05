#!/usr/bin/env python3
"""Run this once to authorize Yandex Music via Device Flow."""
import sys
sys.path.insert(0, '/home/user/Claude')
import clap_detector
clap_detector.setup_token()
print("Готово! Теперь запускай:  python3 clap_detector.py")
