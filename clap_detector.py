#!/usr/bin/env python3
"""
Double-Clap Detector
On two claps: opens Claude Code on the last project
              and plays Back in Black by AC/DC via Yandex Music API.

Token setup (first run):
  python3 clap_detector.py --setup-token
Or set env var:
  export YANDEX_TOKEN=<your_token>
"""

import numpy as np
import sounddevice as sd
import subprocess
import time
import threading
import os
import sys
import json
from collections import deque
from pathlib import Path


# ─── Tuning ───────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BLOCK_SIZE     = 2048
CLAP_THRESHOLD = 0.18   # peak amplitude to register a clap  (0.0–1.0)
CLAP_WINDOW    = 1.8    # seconds: both claps must land in this window
MIN_CLAP_GAP   = 0.12   # seconds: ignore echoes closer than this
COOLDOWN       = 3.5    # seconds: silence detector after a successful trigger

TRACK_QUERY    = "AC/DC Back in Black"
TOKEN_FILE     = Path.home() / ".config" / "clap_detector" / "token.json"

# Fallback browser URL if API/player unavailable
YANDEX_URL     = "https://music.yandex.ru/search?text=AC%2FDC+Back+in+Black"
# ──────────────────────────────────────────────────────────────────────────────

_clap_times: deque = deque(maxlen=20)
_last_clap:  float = 0.0
_last_fire:  float = 0.0
_lock              = threading.Lock()


# ─── Token management ─────────────────────────────────────────────────────────

def _load_token() -> str | None:
    if token := os.environ.get("YANDEX_TOKEN"):
        return token.strip()
    if TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text())
            return data.get("token", "").strip() or None
        except Exception:
            pass
    return None


def _save_token(token: str):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({"token": token}))
    TOKEN_FILE.chmod(0o600)


def setup_token():
    """Get Yandex Music OAuth token: tries Device Flow, falls back to manual URL."""
    from yandex_music import Client  # type: ignore

    print()
    print("  Авторизация Яндекс Музыки")
    print("  ─────────────────────────────────────────")

    client = Client()

    # ── Method 1: Device Flow (works if Yandex doesn't block the host) ──────
    def show_code(code):
        print()
        print(f"  Открой в браузере → {code.verification_url}")
        print(f"  Введи код          → {code.user_code}")
        print()
        print(f"  Жду подтверждения ({code.expires_in // 60} мин)…")
        for launcher in ("xdg-open", "sensible-browser", "firefox", "google-chrome"):
            try:
                subprocess.Popen([launcher, code.verification_url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("  (браузер открыт автоматически)")
                break
            except FileNotFoundError:
                continue

    try:
        oauth = client.device_auth(show_code, timeout=300)
        _save_token(oauth.access_token)
        print(f"\n  ✓ Токен получен и сохранён → {TOKEN_FILE}")
        print()
        return
    except Exception:
        pass  # fall through to manual method

    # ── Method 2: Manual URL (universal fallback) ────────────────────────────
    MANUAL_URL = (
        "https://oauth.yandex.ru/authorize"
        "?response_type=token"
        "&client_id=23cabbbdc6cd418abb4b39c32c41195d"
    )
    print()
    print("  Device Flow недоступен. Используем ручной способ:")
    print()
    print(f"  1. Открой:  {MANUAL_URL}")
    print("  2. Войди в Яндекс и разреши доступ.")
    print("  3. Скопируй значение  access_token=...  из адресной строки.")
    print()
    for launcher in ("xdg-open", "sensible-browser", "firefox", "google-chrome"):
        try:
            subprocess.Popen([launcher, MANUAL_URL],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("  (браузер открыт автоматически)")
            break
        except FileNotFoundError:
            continue

    token = input("\n  Вставь токен: ").strip()
    if not token:
        print("  Токен не введён — выход.")
        sys.exit(1)
    _save_token(token)
    print(f"\n  ✓ Сохранено → {TOKEN_FILE}")
    print()


# ─── Music playback ───────────────────────────────────────────────────────────

def _get_stream_url(token: str) -> str | None:
    """Use yandex-music library to resolve a direct stream URL for the track."""
    try:
        from yandex_music import Client  # type: ignore
    except ImportError:
        return None

    try:
        client = Client(token).init()
        results = client.search(TRACK_QUERY, type_="track")
        if not results or not results.tracks or not results.tracks.results:
            print("  ✗ Трек не найден через API")
            return None

        track = results.tracks.results[0]
        title = f"{track.artists[0].name if track.artists else '?'} – {track.title}"
        print(f"  → Найдено: {title}")

        infos = track.get_download_info()
        if not infos:
            return None
        # Pick highest bitrate
        best = max(infos, key=lambda x: x.bitrate_in_kbps)
        return best.get_direct_link()
    except Exception as exc:
        print(f"  ✗ Ошибка API: {exc}")
        return None


def _play_url(url: str) -> bool:
    """Play an audio URL with the first available system player."""
    players = [
        ["mpv", "--no-video", url],
        ["vlc", "--intf", "dummy", url],
        ["ffplay", "-nodisp", "-autoexit", url],
        ["mplayer", url],
    ]
    for cmd in players:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  → Воспроизводит: {cmd[0]}")
            return True
        except FileNotFoundError:
            continue
    return False


def _play_track():
    token = _load_token()

    if token:
        url = _get_stream_url(token)
        if url and _play_url(url):
            return
        print("  ⚠ Не удалось воспроизвести через API, открываю браузер…")
    else:
        print("  ⚠ Токен не настроен (запусти --setup-token), открываю браузер…")

    # Browser fallback
    for cmd in (
        ["xdg-open",         YANDEX_URL],
        ["sensible-browser", YANDEX_URL],
        ["firefox",          YANDEX_URL],
        ["google-chrome",    YANDEX_URL],
    ):
        try:
            subprocess.Popen(cmd)
            print(f"  → Яндекс Музыка в браузере")
            return
        except FileNotFoundError:
            continue
    import webbrowser
    webbrowser.open(YANDEX_URL)


# ─── Claude Code ──────────────────────────────────────────────────────────────

def _find_last_claude_project() -> str | None:
    home = Path.home()
    projects_root = home / ".claude" / "projects"
    if projects_root.is_dir():
        candidates = sorted(
            (p for p in projects_root.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            raw     = candidate.name
            decoded = raw.replace("-", "/")
            if not decoded.startswith("/"):
                decoded = "/" + decoded
            if os.path.isdir(decoded):
                return decoded

    for base in ("~/projects", "~/code", "~/dev", "~/workspace", "~"):
        base_path = Path(base).expanduser()
        if not base_path.is_dir():
            continue
        dirs = [d for d in base_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if dirs:
            return str(max(dirs, key=lambda d: d.stat().st_mtime))
    return None


def _open_claude_code():
    project = _find_last_claude_project()
    cwd     = project if project and os.path.isdir(project) else None
    print(f"  → Claude Code  {('in ' + cwd) if cwd else '(no project found)'}")
    for cmd in (["claude"], ["code", "--reuse-window"], ["cursor"]):
        try:
            subprocess.Popen(cmd, cwd=cwd)
            return
        except FileNotFoundError:
            continue
    print("  ✗ claude / code / cursor не найдены в PATH")


# ─── Trigger ─────────────────────────────────────────────────────────────────

def _trigger():
    global _last_fire
    print("\n" + "═" * 52)
    print("  👏  👏   ДВОЙНОЙ ХЛОПОК — запускаем!")
    print("═" * 52)

    t1 = threading.Thread(target=_open_claude_code, daemon=True)
    t2 = threading.Thread(target=_play_track,       daemon=True)
    t1.start(); t2.start()
    t1.join(timeout=8); t2.join(timeout=8)

    print("  ✓  Готово!\n")
    with _lock:
        _last_fire = time.monotonic()


# ─── Audio callback ───────────────────────────────────────────────────────────

def _is_clap(block: np.ndarray) -> bool:
    peak = float(np.max(np.abs(block)))
    if peak < CLAP_THRESHOLD:
        return False
    q    = len(block) // 4
    rise = float(np.max(np.abs(block[:q])))
    tail = float(np.max(np.abs(block[-q:])))
    return rise > tail * 0.5


def _audio_cb(indata: np.ndarray, frames: int, time_info, status):
    global _last_clap

    if status:
        print(f"[audio] {status}")

    mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
    now  = time.monotonic()

    with _lock:
        if now - _last_fire < COOLDOWN:
            return

    if not _is_clap(mono):
        return

    with _lock:
        if now - _last_clap < MIN_CLAP_GAP:
            return
        _last_clap = now
        _clap_times.append(now)
        recent = [t for t in _clap_times if now - t <= CLAP_WINDOW]
        count  = len(recent)

    peak = float(np.max(np.abs(mono)))
    print(f"  👏  хлопок #{count}  (peak={peak:.2f})")

    if count >= 2:
        with _lock:
            _clap_times.clear()
        threading.Thread(target=_trigger, daemon=True).start()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    if "--setup-token" in sys.argv:
        setup_token()
        return

    token_status = "✓ настроен" if _load_token() else "✗ не настроен (запусти --setup-token)"

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   👏  Детектор двойного хлопка  👏              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  Два хлопка →")
    print("    1. Claude Code  (последний проект)")
    print("    2. AC/DC – Back in Black  (Яндекс Музыка)")
    print()
    print(f"  Токен YM  : {token_status}")
    print(f"  threshold : {CLAP_THRESHOLD}   window : {CLAP_WINDOW}s   cooldown : {COOLDOWN}s")
    print()
    print("  Ctrl+C — остановить")
    print("─" * 52)

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            callback=_audio_cb,
            dtype=np.float32,
        ):
            print("  🎤  Слушаю…\n")
            while True:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n  Остановлено.")
    except sd.PortAudioError as exc:
        print(f"\n  Ошибка микрофона: {exc}")
        print("  Проверь, что микрофон подключён и разрешён.")


if __name__ == "__main__":
    main()
