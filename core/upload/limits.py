"""Daily upload accounting so accounts stay healthy."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from paths import data_dir, ensure_dirs


def _log_path():
    ensure_dirs()
    return os.path.join(data_dir(), "upload_log.json")


def _load():
    path = _log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items):
    tmp = _log_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, _log_path())


def record(platform, profile, video, status="done", url="", message=""):
    items = _load()
    items.append({
        "time": time.time(),
        "day": time.strftime("%Y-%m-%d"),
        "platform": platform,
        "profile": profile,
        "video": video,
        "status": status,
        "url": url,
        "message": message,
    })
    _save(items[-2000:])
    return True


def today_count(platform=None):
    day = time.strftime("%Y-%m-%d")
    items = [item for item in _load() if item.get("day") == day and item.get("status") == "done"]
    if platform:
        items = [item for item in items if item.get("platform") == platform]
    return len(items)


def remaining(limit):
    try:
        limit = int(limit)
    except Exception:
        return 999
    if limit <= 0:
        return 999
    return max(0, limit - today_count())


def recent(days=7):
    cutoff = time.time() - days * 86400
    return [item for item in _load() if item.get("time", 0) >= cutoff]
