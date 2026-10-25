"""Scene visuals with a key-free cascade.

Order (auto): user folder -> Pollinations AI -> Wikimedia Commons -> Picsum -> gradient.
Pollinations allows only one free image per 45s per IP, so once that limit is hit we
stop asking for the rest of the run instead of stalling.
"""
import hashlib
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import ensure_dirs, images_cache_dir

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
PICSUM_URL = "https://picsum.photos/{width}/{height}"
TIMEOUT = 90
MAX_PROMPT = 320
NEGATIVE = "no text, no watermark, no logo, no caption, no letters"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YTFBStudio/1.0 (free content tool)"
STYLE_NOISE = re.compile(
    r"\b(cinematic|dramatic|photorealistic|photograph|vertical composition|highly detailed|"
    r"film still|35mm|shallow depth of field|natural light|studio quality|illustration|"
    r"infographic style|vibrant|colorful|bold outlines|flat 2d|pencil sketch|hand drawn|"
    r"moody|high contrast|deep shadows|emotional|energetic|bright|clean modern)\b",
    re.I)

_pollinations_blocked_until = 0.0
IMAGE_SOURCES = [
    ("auto", "স্বয়ংক্রিয় (সেরা যেটা পাওয়া যায়)"),
    ("ai", "শুধু AI ছবি"),
    ("art", "AI আর্ট (অ্যানিমেশন স্টাইলের জন্য)"),
    ("stock", "স্টক ফটো (Wikimedia/Picsum)"),
    ("own", "নিজের ছবির ফোল্ডার"),
    ("none", "ছবি ছাড়া (গ্রেডিয়েন্ট)"),
]


STYLE_PALETTES = {
    "anime": [((150, 190, 255), (255, 205, 235)), ((110, 150, 230), (255, 232, 190)),
              ((170, 210, 255), (200, 255, 232))],
    "cartoon2d": [((255, 205, 80), (255, 120, 110)), ((110, 200, 255), (255, 240, 120)),
                  ((180, 255, 160), (90, 190, 255))],
    "whiteboard": [((252, 252, 250), (232, 236, 232))],
    "sketch": [((246, 241, 231), (222, 212, 194))],
    "puppet": [((255, 196, 150), (232, 118, 92))],
    "slide": [((14, 22, 46), (54, 76, 138))],
}


def style_palette(style):
    """A gradient palette that at least matches the chosen look."""
    options = STYLE_PALETTES.get(str(style or ""))
    if not options:
        return None
    return random.choice(options)


def _cache_path(key, width, height, suffix=".jpg"):
    ensure_dirs()
    digest = hashlib.md5(f"{key}|{width}x{height}".encode("utf-8")).hexdigest()[:24]
    return os.path.join(images_cache_dir(), f"{digest}{suffix}")


def _is_cached(path):
    return bool(path) and os.path.exists(path) and os.path.getsize(path) > 4096


def _download(url, path, params=None, headers=None, retries=2, pause=1.2):
    import requests
    last = None
    send_headers = {"User-Agent": USER_AGENT}
    send_headers.update(headers or {})
    for attempt in range(max(1, retries)):
        try:
            resp = requests.get(url, params=params, headers=send_headers, timeout=TIMEOUT)
            if resp.status_code == 402:
                return None, resp.text
            resp.raise_for_status()
            if len(resp.content) < 4096:
                raise RuntimeError("ডেটা খুব ছোট")
            tmp = path + ".part"
            with open(tmp, "wb") as fh:
                fh.write(resp.content)
            os.replace(tmp, path)
            return path, ""
        except Exception as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(pause)
    return None, str(last or "ডাউনলোড ব্যর্থ")


# ------------------------------------------------------------------ sources
def _retry_hint(body):
    match = re.search(r"retry after (\d+)", body or "", re.I)
    return int(match.group(1)) if match else 45


def fetch_pollinations(prompt, width, height, seed=None, token="", model="flux", retries=3,
                       progress=None):
    global _pollinations_blocked_until
    if time.time() < _pollinations_blocked_until:
        return None, "লিমিট"
    prompt = " ".join(str(prompt or "").split())[:MAX_PROMPT]
    if not prompt:
        return None, "প্রম্পট নেই"
    seed = random.randint(0, 10 ** 6) if seed is None else int(seed)
    path = _cache_path(f"pollinations|{prompt}|{seed}|{model}", width, height)
    if _is_cached(path):
        return path, "AI ছবি"
    if progress:
        progress("AI ছবি আনা হচ্ছে…")

    import requests
    url = POLLINATIONS_URL.format(prompt=requests.utils.quote(f"{prompt}, {NEGATIVE}"))
    params = {"width": width, "height": height, "seed": seed, "model": model, "nologo": "true"}
    headers = {}
    if token:
        params["token"] = token
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(max(1, retries)):
        path, error = _download(url, path, params=params, headers=headers, retries=1)
        if path:
            return path, "AI ছবি"
        if "FREE_LIMIT" in (error or "") or "402" in (error or ""):
            wait = _retry_hint(error)
            _pollinations_blocked_until = time.time() + max(5, wait)
            if token:
                _pollinations_blocked_until = time.time() + 5
            return None, "লিমিট"
        params["seed"] = seed + attempt + 1
        path = _cache_path(f"pollinations|{prompt}|{params['seed']}|{model}", width, height)
        if attempt < retries - 1:
            time.sleep(2.0 + attempt * 3.0)
    return None, error or "ব্যর্থ"


def _search_query(prompt):
    text = STYLE_NOISE.sub(" ", str(prompt or ""))
    text = re.sub(r"[^\w\s\u0980-\u09FF]", " ", text)
    words = [w for w in text.split() if len(w) > 2]
    return " ".join(words[:6]).strip()


def fetch_wikimedia(prompt, width, height, progress=None, token=None, variant=0):
    """Search Commons for a topic-relevant photo; shortens the query if needed."""
    import requests

    base_words = _search_query(prompt).split()
    if not base_words:
        return None, "কুয়েরি নেই"

    attempts = []
    for size in (6, 3, 2):
        candidate = " ".join(base_words[:size])
        if candidate and candidate not in attempts:
            attempts.append(candidate)

    last_note = "কিছু পাওয়া যায়নি"
    for query in attempts:
        path = _cache_path(f"wikimedia|{query}|v{variant}", width, height)
        if _is_cached(path):
            return path, "স্টক (ক্যাশ)"

        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6", "gsrlimit": "12",
            "prop": "imageinfo", "iiprop": "url|size|mime",
            "iiurlwidth": str(min(1600, max(width, 1080))),
        }
        try:
            resp = requests.get(WIKIMEDIA_API, params=params,
                                headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            pages = (resp.json().get("query") or {}).get("pages") or {}
        except Exception as exc:
            last_note = f"উইকি ব্যর্থ: {exc}"
            continue

        candidates = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            mime = info.get("mime") or ""
            if not url or "image" not in mime or "svg" in mime:
                continue
            pixels = (info.get("width") or 0) * (info.get("height") or 0)
            if pixels < 640 * 480:
                continue
            candidates.append((url, pixels))
        if not candidates:
            last_note = "কিছু পাওয়া যায়নি"
            continue

        candidates.sort(key=lambda item: item[1], reverse=True)
        start = variant % len(candidates) if candidates else 0
        ordered = candidates[start:] + candidates[:start]
        for url, _pixels in ordered[:3]:
            if progress:
                progress("স্টক ছবি আনা হচ্ছে…")
            saved, error = _download(url, path, retries=2)
            if saved:
                return saved, "স্টক ছবি"
            last_note = f"ডাউনলোড ব্যর্থ: {error}"
    return None, last_note


def fetch_picsum(prompt, width, height, index=0, progress=None, variant=0):
    path = _cache_path(f"picsum|{index}|v{variant}", width, height)
    if _is_cached(path):
        return path, "র‍্যান্ডম (ক্যাশ)"
    seed = abs(hash(f"{prompt}|{index}|{variant}")) % 9000
    url = f"https://picsum.photos/seed/{seed}/{width}/{height}"
    saved, error = _download(url, path, retries=2)
    if saved:
        return saved, "র‍্যান্ডম ছবি"
    return None, error


# ------------------------------------------------------------------- helpers
def own_images(folder):
    if not folder or not os.path.isdir(folder):
        return []
    exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(exts)]


def procedural_background(width, height, seed=None, palette=None):
    from PIL import Image, ImageDraw, ImageFilter

    rng = random.Random(seed if seed is not None else random.randint(0, 10 ** 6))
    if not palette:
        palette = rng.choice([
            ((14, 22, 48), (76, 29, 149)),
            ((8, 20, 40), (13, 148, 136)),
            ((30, 14, 48), (190, 24, 93)),
            ((12, 18, 32), (37, 99, 235)),
            ((24, 16, 12), (217, 119, 6)),
        ])
    c1, c2 = palette
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / max(1, height - 1)
        draw.line([(0, y), (width, y)],
                  fill=(int(c1[0] + (c2[0] - c1[0]) * ratio),
                        int(c1[1] + (c2[1] - c1[1]) * ratio),
                        int(c1[2] + (c2[2] - c1[2]) * ratio)))
    blobs = Image.new("RGB", (width, height), (0, 0, 0))
    bdraw = ImageDraw.Draw(blobs)
    for _ in range(5):
        radius = rng.randint(width // 6, width // 2)
        cx, cy = rng.randint(0, width), rng.randint(0, height)
        shade = rng.randint(30, 90)
        bdraw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                      fill=(shade, shade // 2, min(255, shade * 2)))
    blobs = blobs.filter(ImageFilter.GaussianBlur(width // 8))
    return Image.blend(img, blobs, 0.35)


def scene_visual(prompt, width, height, index=0, source="auto", own_dir=None,
                 allow_network=True, progress=None, token="", variant=0, style=None):
    """Resolve one scene visual -> (PIL.Image, note, path)."""
    from PIL import Image

    def load(path, note):
        try:
            return Image.open(path).convert("RGB"), note, path
        except Exception:
            return None, "", None

    files = own_images(own_dir)
    if source == "own":
        if files:
            path = files[(index + variant) % len(files)]
            image, note, got = load(path, "নিজের ছবি")
            if image is not None:
                return image, note, got
        return procedural_background(width, height, index + variant), "নিজের ছবি নেই — গ্রেডিয়েন্ট", None

    if source == "none":
        return procedural_background(width, height, index + variant), "গ্রেডিয়েন্ট", None

    if source == "art":
        # illustrated styles: never pull in real photos, they break the look
        if allow_network:
            path, note = fetch_pollinations(
                prompt, width, height, seed=1000 + index * 37 + variant * 7919,
                token=token, progress=progress)
            if path:
                image, _n, got = load(path, "")
                if image is not None:
                    return image, note, got
            elif note == "লিমিট" and progress:
                progress("AI ছবির ফ্রি লিমিট শেষ — স্টাইল অনুযায়ী ব্যাকগ্রাউন্ড ব্যবহার হবে")
        return (procedural_background(width, height, index + variant,
                                      palette=style_palette(style)),
                "স্টাইল ব্যাকগ্রাউন্ড", None)

    if source == "auto" and files:
        path = files[(index + variant) % len(files)]
        image, note, got = load(path, "নিজের ছবি")
        if image is not None:
            return image, note, got

    if allow_network:
        if source in ("auto", "ai"):
            path, note = fetch_pollinations(
                prompt, width, height, seed=1000 + index * 37 + variant * 7919,
                token=token, progress=progress)
            if path:
                image, _n, got = load(path, "")
                if image is not None:
                    return image, note, got
            elif note == "লিমিট" and progress:
                progress("AI ছবির ফ্রি লিমিট শেষ — বিকল্প ছবি ব্যবহার করা হচ্ছে")

        if source in ("auto", "stock", "ai"):
            path, note = fetch_wikimedia(prompt, width, height, progress=progress,
                                         variant=variant)
            if path:
                image, _n, got = load(path, "")
                if image is not None:
                    return image, note, got

        if source in ("auto", "stock"):
            path, note = fetch_picsum(prompt, width, height, index=index,
                                      progress=progress, variant=variant)
            if path:
                image, _n, got = load(path, "")
                if image is not None:
                    return image, note, got

    if files:
        image, note, got = load(files[(index + variant) % len(files)], "নিজের ছবি")
        if image is not None:
            return image, note, got

    return procedural_background(width, height, index + variant), "ব্যাকগ্রাউন্ড (গ্রেডিয়েন্ট)", None


def cover_resize(img, width, height, zoom=1.0, offset=(0.0, 0.0)):
    """Scale-crop an image to exactly fill width x height with optional zoom/pan."""
    from PIL import Image

    target_w, target_h = max(1, int(width * zoom)), max(1, int(height * zoom))
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    resized = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
    max_x = max(0, new_w - width)
    max_y = max(0, new_h - height)
    center_x = (new_w - width) // 2 + int(max_x * offset[0] * 0.5)
    center_y = (new_h - height) // 2 + int(max_y * offset[1] * 0.5)
    left = min(max(0, center_x), max_x)
    top = min(max(0, center_y), max_y)
    return resized.crop((left, top, left + width, top + height))
