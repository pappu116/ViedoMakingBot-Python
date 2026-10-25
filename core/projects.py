"""Project store: data/projects.json plus thumbnail helpers."""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import ensure_dirs, projects_path, thumb_dir


def _load_all():
    ensure_dirs()
    path = projects_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_all(items):
    ensure_dirs()
    tmp = projects_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, projects_path())


def create(title="", idea="", script=None, settings=None):
    item = {
        "id": uuid.uuid4().hex[:10],
        "title": title or "নতুন প্রজেক্ট",
        "idea": idea,
        "script": script or {},
        "settings": settings or {},
        "video_path": "",
        "thumbnail": "",
        "duration": 0,
        "created": time.time(),
        "updated": time.time(),
        "uploads": {},
    }
    items = _load_all()
    items.insert(0, item)
    _save_all(items)
    return item


def update(project_id, **fields):
    items = _load_all()
    for item in items:
        if item["id"] == project_id:
            item.update(fields)
            item["updated"] = time.time()
            _save_all(items)
            return item
    return None


def get(project_id):
    for item in _load_all():
        if item["id"] == project_id:
            return item
    return None


def list_all():
    return _load_all()


def delete(project_id):
    items = [i for i in _load_all() if i["id"] != project_id]
    _save_all(items)
    return True


def stats():
    items = _load_all()
    videos = [i for i in items if i.get("video_path") and os.path.exists(i["video_path"])]
    uploads = 0
    for item in items:
        uploads += len([v for v in (item.get("uploads") or {}).values() if v.get("status") == "done"])
    seconds = sum(float(i.get("duration") or 0) for i in items)
    return {
        "projects": len(items),
        "videos": len(videos),
        "uploads": uploads,
        "minutes": round(seconds / 60.0, 1),
    }


def save_thumbnail(video_path, time_sec=1.0):
    """Grab a frame with moviepy and store it in data/thumbs."""
    if not video_path or not os.path.exists(video_path):
        return ""
    ensure_dirs()
    target = os.path.join(thumb_dir(), os.path.splitext(os.path.basename(video_path))[0] + ".jpg")
    if os.path.exists(target):
        return target
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)
        try:
            frame = clip.get_frame(min(time_sec, max(0.0, clip.duration - 0.1)))
            from PIL import Image
            Image.fromarray(frame).save(target, quality=88)
        finally:
            clip.close()
        return target
    except Exception:
        return ""
