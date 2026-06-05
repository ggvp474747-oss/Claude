#!/usr/bin/env python3
"""
Double-Clap Detector
On two claps: opens Claude Code on the last project
              and plays Back in Black on Yandex Music.
"""

import numpy as np
import sounddevice as sd
import subprocess
import time
import threading
import os
from collections import deque
from pathlib import Path


# ─── Tuning ───────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BLOCK_SIZE     = 2048
CLAP_THRESHOLD = 0.18   # peak amplitude to register a clap  (0.0–1.0)
CLAP_WINDOW    = 1.8    # seconds: both claps must land in this window
MIN_CLAP_GAP   = 0.12   # seconds: ignore echoes closer than this
COOLDOWN       = 3.5    # seconds: silence detector after a successful trigger

YANDEX_URL = (
    "https://music.yandex.ru/search?text=AC%2FDC+Back+in+Black"
)
# ──────────────────────────────────────────────────────────────────────────────

_clap_times: deque      = deque(maxlen=20)
_last_clap:  float      = 0.0
_last_fire:  float      = 0.0
_lock                   = threading.Lock()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_last_claude_project() -> str | None:
    """Return the path of the most recently used Claude Code project."""
    home = Path.home()

    # ~/.claude/projects/<encoded-path>/  — each dir is one project session
    projects_root = home / ".claude" / "projects"
    if projects_root.is_dir():
        candidates = sorted(
            (p for p in projects_root.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            # Claude encodes the real path: leading slash → empty token,
            # remaining slashes → hyphens.  Reconstruct and verify.
            raw = candidate.name
            # encoded form: "-home-user-myproject"  →  "/home/user/myproject"
            decoded = raw.replace("-", "/")
            if not decoded.startswith("/"):
                decoded = "/" + decoded
            if os.path.isdir(decoded):
                return decoded

    # Fallback: most recently touched dir in common locations
    for base in ("~/projects", "~/code", "~/dev", "~/workspace", "~"):
        base_path = Path(base).expanduser()
        if not base_path.is_dir():
            continue
        dirs = [
            d for d in base_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        if dirs:
            return str(max(dirs, key=lambda d: d.stat().st_mtime))

    return None


def _open_claude_code():
    project = _find_last_claude_project()
    cwd     = project if project and os.path.isdir(project) else None

    print(f"  → Claude Code  {('in ' + cwd) if cwd else '(no project found)'}")
    for cmd in (["claude"], ["code", "--reuse-window", cwd or "."], ["cursor", cwd or "."]):
        try:
            subprocess.Popen(cmd if cwd is None else cmd[:1], cwd=cwd)
            return
        except FileNotFoundError:
            continue
    print("  ✗ claude / code / cursor not found in PATH")


def _open_yandex_music():
    print(f"  → Yandex Music  {YANDEX_URL}")
    for cmd in (
        ["xdg-open",         YANDEX_URL],
        ["sensible-browser", YANDEX_URL],
        ["firefox",          YANDEX_URL],
        ["google-chrome",    YANDEX_URL],
        ["chromium-browser", YANDEX_URL],
    ):
        try:
            subprocess.Popen(cmd)
            return
        except FileNotFoundError:
            continue
    import webbrowser
    webbrowser.open(YANDEX_URL)


def _trigger():
    global _last_fire
    print("\n" + "═" * 52)
    print("  👏  👏   ДВОЙНОЙ ХЛОПОК — запускаем!")
    print("═" * 52)

    threads = [
        threading.Thread(target=_open_claude_code, daemon=True),
        threading.Thread(target=_open_yandex_music, daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=6)

    print("  ✓  Готово!\n")
    with _lock:
        _last_fire = time.monotonic()


# ─── Audio callback ───────────────────────────────────────────────────────────

def _is_clap(block: np.ndarray) -> bool:
    """True when the block looks like a hand-clap transient."""
    peak = float(np.max(np.abs(block)))
    if peak < CLAP_THRESHOLD:
        return False
    # Claps decay quickly: first quarter louder than last quarter
    q = len(block) // 4
    if q == 0:
        return True
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
        gap = now - _last_clap
        if gap < MIN_CLAP_GAP:
            return  # echo / double-count guard

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
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   👏  Детектор двойного хлопка  👏              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  Два хлопка →")
    print("    1. Claude Code  (последний проект)")
    print("    2. Back in Black  на Яндекс Музыке")
    print()
    print(f"  threshold : {CLAP_THRESHOLD}   window : {CLAP_WINDOW}s"
          f"   cooldown : {COOLDOWN}s")
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
