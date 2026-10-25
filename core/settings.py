"""Settings store: data/settings.json with migration from the legacy config.json."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import config_path, ensure_dirs, settings_path

DEFAULTS = {
    "ui": {
        "language": "bn",
        "notify_on_done": True,
        "minimize_to_tray": False,
        "open_output_after_render": True,
    },
    "ai": {
        "provider": "pollinations",
        "model": "",
        "keys": {"gemini": "", "groq": "", "openrouter": ""},
        "ollama_url": "http://localhost:11434",
        "tone": "educational",
    },
    "voice": {
        "engine": "auto",
        "lang": "bn",
        "gender": "female",
        "accent": "bd",
        "voice": "",
        "rate": 0,
        "pitch": 0,
    },
    "video": {
        "aspect": "mobile",
        "style": "cinematic",
        "caption_style": "bold",
        "duration": 45,
        "fps": 24,
        "music": True,
        "music_volume": 0.18,
        "subtitles": True,
        "voiceover": True,
        "ducking": True,
        "kenburns": True,
        "motion": "auto",
        "progress_bar": True,
        "watermark": "",
        "images": True,
        "stock_video": True,
        "image_source": "auto",
        "own_images_dir": "",
    },
    "upload": {
        "platforms": ["youtube", "facebook"],
        "visibility": "public",
        "headless": False,
        "delay_min": 30,
        "delay_max": 90,
        "daily_limit": 6,
        "dry_run": False,
        "made_for_kids": False,
    },
    "paths": {
        "output_dir": "",
        "music_dir": "",
        "images_dir": "",
    },
}


def _deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _migrate_legacy():
    """Pull the old flat config.json values into the new nested structure."""
    if not os.path.exists(config_path()):
        return {}
    try:
        with open(config_path(), encoding="utf-8") as fh:
            old = json.load(fh)
    except Exception:
        return {}
    migrated = {}
    if "visibility" in old:
        migrated.setdefault("upload", {})["visibility"] = old["visibility"]
    if "headless" in old:
        migrated.setdefault("upload", {})["headless"] = bool(old["headless"])
    if isinstance(old.get("upload_delay_sec"), list) and len(old["upload_delay_sec"]) == 2:
        migrated.setdefault("upload", {})["delay_min"] = old["upload_delay_sec"][0]
        migrated.setdefault("upload", {})["delay_max"] = old["upload_delay_sec"][1]
    if old.get("platforms"):
        migrated.setdefault("upload", {})["platforms"] = old["platforms"]
    if old.get("duration_sec"):
        migrated.setdefault("video", {})["duration"] = old["duration_sec"]
    return migrated


def load():
    ensure_dirs()
    path = settings_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
    merged = _deep_merge(_deep_merge(DEFAULTS, _migrate_legacy()), data)
    return merged


def save(cfg):
    ensure_dirs()
    with open(settings_path(), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    return cfg


def get(section, key=None, default=None):
    cfg = load()
    if key is None:
        return cfg.get(section, default)
    return cfg.get(section, {}).get(key, default)


def update(section, values):
    cfg = load()
    cfg.setdefault(section, {})
    cfg[section].update(values)
    return save(cfg)
