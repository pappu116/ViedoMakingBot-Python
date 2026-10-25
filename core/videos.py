"""Real stock footage from Wikimedia Commons (free, no API key).

Commons hosts freely licensed .webm/.ogv clips. We search by the scene's visual
keywords, pick a sensible resolution transcode and cache the file on disk.
"""
import hashlib
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import cache_dir, ensure_dirs

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YTFBStudio/1.0 (free content tool)"
TIMEOUT = 120
MIN_SECONDS = 2.0
MAX_SECONDS = 30.0
TARGET_HEIGHT = 720

STYLE_NOISE = re.compile(
    r"\b(cinematic|dramatic|photorealistic|vertical composition|highly detailed|film still|"
    r"35mm|shallow depth of field|natural light|studio quality|illustration|infographic|"
    r"vibrant|colorful|bold outlines|flat 2d|pencil sketch|hand drawn|moody|high contrast|"
    r"deep shadows|emotional|energetic|bright|clean modern|no text|watermark|logo)\b", re.I)


def videos_cache_dir():
    ensure_dirs()
    path = os.path.join(cache_dir(), "videos")
    os.makedirs(path, exist_ok=True)
    return path


def _cache_path(query, variant):
    digest = hashlib.md5(f"{query}|v{variant}".encode("utf-8")).hexdigest()[:24]
    return os.path.join(videos_cache_dir(), f"{digest}.webm")


def _query_from_prompt(prompt):
    text = STYLE_NOISE.sub(" ", str(prompt or ""))
    text = re.sub(r"[^\w\s\u0980-\u09FF]", " ", text)
    words = [w for w in text.split() if len(w) > 2]
    return " ".join(words[:4]).strip()


def _pick_transcode(info):
    """Choose the best available transcode URL (prefer ~720p, then smaller)."""
    derivatives = info.get("derivatives") or []
    candidates = []
    for item in derivatives:
        src = item.get("src") or ""
        if not src or not src.lower().endswith((".webm", ".ogv", ".mp4")):
            continue
        height = int(item.get("height") or 0)
        width = int(item.get("width") or 0)
        if height <= 0 or width <= 0:
            continue
        candidates.append({"url": src, "height": height, "width": width,
                           "type": item.get("type") or ""})
    if not candidates:
        url = info.get("url")
        if url and url.lower().endswith((".webm", ".ogv", ".mp4")):
            candidates.append({"url": url, "height": 1080, "width": 1920, "type": ""})
        else:
            return None
    usable = [c for c in candidates if 360 <= c["height"] <= 1080]
    pool = usable or candidates
    pool.sort(key=lambda item: abs(item["height"] - TARGET_HEIGHT))
    return pool[0]


def search(query, limit=8, progress=None):
    """Return candidate clips for a search phrase."""
    import requests

    query = _query_from_prompt(query)
    if not query:
        return []
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:video {query}", "gsrnamespace": "6",
        "gsrlimit": str(max(2, min(20, limit))),
        "prop": "videoinfo",
        "viprop": "url|size|mime|derivatives|user",
    }
    try:
        resp = requests.get(WIKIMEDIA_API, params=params,
                            headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        pages = (resp.json().get("query") or {}).get("pages") or {}
    except Exception as exc:
        if progress:
            progress(f"স্টক ভিডিও খোঁজা যায়নি: {exc}")
        return []

    results = []
    for page in pages.values():
        info = (page.get("videoinfo") or [{}])[0]
        if not info:
            continue
        duration = float(info.get("duration") or 0)
        if duration and not (MIN_SECONDS <= duration <= MAX_SECONDS):
            continue
        transcode = _pick_transcode(info)
        if not transcode:
            continue
        transcode["title"] = (page.get("title") or "").replace("File:", "")
        transcode["duration"] = duration
        results.append(transcode)
    return results


VIDEO_NOUNS = {
    "river", "boat", "water", "sea", "ocean", "beach", "wave", "rain", "cloud", "clouds",
    "sky", "sun", "sunrise", "sunset", "moon", "star", "stars", "night", "mountain",
    "mountains", "hill", "hills", "forest", "tree", "trees", "flower", "flowers", "bird",
    "birds", "field", "farm", "farmer", "rice", "paddy", "village", "city", "street",
    "road", "traffic", "train", "bus", "car", "market", "shop", "food", "tea", "coffee",
    "people", "person", "child", "children", "man", "woman", "crowd", "dance", "music",
    "sport", "running", "walking", "fire", "smoke", "fog", "snow", "desert", "camel",
    "horse", "cow", "dog", "cat", "fish", "cooking", "factory", "machine", "computer",
    "phone", "book", "reading", "money", "office", "hospital", "temple", "mosque",
    "bridge", "building", "window", "light", "lights", "garden", "lake", "waterfall",
}


def _best_single_term(words):
    for word in words:
        if word.lower() in VIDEO_NOUNS:
            return word.lower()
    return words[-1].lower() if words else ""


def _query_variants(prompt):
    """Progressively shorter queries — Commons search is strict about word count."""
    text = STYLE_NOISE.sub(" ", str(prompt or ""))
    text = re.sub(r"[^\w\s\u0980-\u09FF]", " ", text)
    words = [w for w in text.split() if len(w) > 2]
    variants = []
    for size in (4, 3, 2):
        candidate = " ".join(words[:size]).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    single = _best_single_term(words)
    if single and single not in variants:
        variants.append(single)
    return variants


MIN_INTERVAL = 3.5          # seconds between downloads from upload.wikimedia.org
_download_free_at = 0.0     # global throttle: Wikimedia 429s on rapid downloads


def _polite_wait():
    global _download_free_at
    wait = _download_free_at - time.time()
    if wait > 0:
        time.sleep(min(wait, 60.0))
    _download_free_at = time.time() + MIN_INTERVAL


def _block_for(seconds):
    global _download_free_at
    _download_free_at = max(_download_free_at, time.time() + max(1.0, seconds))


def _download_file(url, path, progress=None, attempts=2):
    import requests

    for attempt in range(max(1, attempts)):
        _polite_wait()
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                                timeout=TIMEOUT, stream=True)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                delay = int(retry_after) if str(retry_after or "").isdigit() else 8 + attempt * 6
                if progress:
                    progress(f"সার্ভার ব্যস্ত — {delay} সেকেন্ড অপেক্ষা")
                _block_for(delay)
                continue
            resp.raise_for_status()
            tmp = path + ".part"
            written = 0
            with open(tmp, "wb") as handle:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)
                    if written > 80 * 1024 * 1024:
                        raise RuntimeError("ফাইল খুব বড়")
            if written < 50000:
                raise RuntimeError("ফাইল খুব ছোট")
            os.replace(tmp, path)
            return True, ""
        except Exception as exc:
            if attempt < attempts - 1:
                _block_for(3 + attempt * 3)
                continue
            return False, str(exc)
    return False, "রেট লিমিট"


def fetch_clip(prompt, variant=0, progress=None, retries=2):
    """Download one cached clip for the prompt. Returns (path, note)."""
    variants = _query_variants(prompt)
    if not variants:
        return None, "কুয়েরি নেই"
    for query in variants:
        path = _cache_path(query, variant)
        if os.path.exists(path) and os.path.getsize(path) > 50000:
            return path, "ভিডিও ক্লিপ (ক্যাশ)"

    candidates = []
    used_variant = variants[0]
    for query in variants:
        candidates = search(query, progress=progress)
        if candidates:
            used_variant = query
            break
    if not candidates:
        return None, "ভিডিও পাওয়া যায়নি"

    path = _cache_path(used_variant, variant)
    start = variant % len(candidates)
    ordered = candidates[start:] + candidates[:start]
    for candidate in ordered[:3]:
        if progress:
            progress(f"ভিডিও ক্লিপ নামছে ({candidate['height']}p)…")
        ok, error = _download_file(candidate["url"], path, progress=progress)
        if ok:
            return path, "ভিডিও ক্লিপ"
        if progress:
            progress(f"ক্লিপ নামানো যায়নি: {error}")
    return None, "ভিডিও নামানো যায়নি"


def clip_duration(path):
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(path)
        duration = float(clip.duration or 0)
        clip.close()
        return duration
    except Exception:
        return 0.0
