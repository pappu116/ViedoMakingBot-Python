"""Render planner: turns a script + voice timings into scenes, captions and assets."""
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import images as image_lib
from core import script as script_lib
from core import textrender

ASPECTS = {
    "mobile": (1080, 1920),
    "shorts": (1080, 1920),
    "reels": (1080, 1920),
    "vertical": (1080, 1920),
    "landscape": (1920, 1080),
    "desktop": (1920, 1080),
    "youtube": (1920, 1080),
    "square": (1080, 1080),
}

ASPECT_LABELS = {
    "mobile": {"bn": "Mobile (9:16)", "en": "Mobile (9:16)"},
    "landscape": {"bn": "YouTube (16:9)", "en": "YouTube (16:9)"},
    "square": {"bn": "Square (1:1)", "en": "Square (1:1)"},
}

STYLE_PRESETS = {
    "cinematic": {"label_bn": "সিনেমাটিক", "label_en": "Cinematic", "swatch": "#7C3AED",
                  "tint": "#0B1020", "tint_alpha": 30, "brightness": 0.98, "contrast": 1.14,
                  "saturation": 1.0, "vignette": 0.5, "box": "#000000B8", "accent": "#8B5CF6",
                  "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.3},
    "dramatic": {"label_bn": "ড্রামাটিক", "label_en": "Dramatic", "swatch": "#DC2626",
                 "tint": "#120303", "tint_alpha": 50, "brightness": 0.88, "contrast": 1.32,
                 "saturation": 0.82, "vignette": 0.72, "box": "#1A0000C4", "accent": "#EF4444",
                 "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.28},
    "educational": {"label_bn": "শিক্ষামূলক", "label_en": "Educational", "swatch": "#16A34A",
                    "tint": "#F2FFF6", "tint_alpha": 8, "brightness": 1.03, "contrast": 1.1,
                    "saturation": 1.04, "vignette": 0.15, "box": "#FFFFFFF0", "accent": "#16A34A",
                    "text": "#0F172A", "uppercase": False, "line_spacing": 1.32},
    "tutorial": {"label_bn": "টিউটোরিয়াল", "label_en": "Tutorial", "swatch": "#0891B2",
                 "tint": "#FFFFFF", "tint_alpha": 0, "brightness": 1.04, "contrast": 1.16,
                 "saturation": 1.0, "vignette": 0.2, "box": "#0F172AE0", "accent": "#0EA5E9",
                 "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.3},
    "vibrant": {"label_bn": "উজ্জ্বল", "label_en": "Vibrant", "swatch": "#F59E0B",
                "tint": "#1A0F00", "tint_alpha": 16, "brightness": 1.05, "contrast": 1.1,
                "saturation": 1.24, "vignette": 0.18, "box": "#0000009E", "accent": "#F59E0B",
                "text": "#FFFFFF", "uppercase": True, "line_spacing": 1.26},
    "anime": {"label_bn": "অ্যানিমে", "label_en": "Anime", "swatch": "#EC4899",
              "tint": "#160B20", "tint_alpha": 22, "brightness": 1.02, "contrast": 1.06,
              "saturation": 1.12, "vignette": 0.2, "box": "#2E0A2EB4", "accent": "#EC4899",
              "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.3},
    "cartoon2d": {"label_bn": "কার্টুন", "label_en": "Cartoon 2D", "swatch": "#FBBF24",
                  "tint": "#0A3A5C", "tint_alpha": 30, "brightness": 1.08, "contrast": 1.2,
                  "saturation": 1.55, "posterize": 4, "vignette": 0.12, "box": "#000000A8",
                  "accent": "#FBBF24", "text": "#FFFFFF", "uppercase": False,
                  "line_spacing": 1.28},
    "whiteboard": {"label_bn": "হোয়াইটবোর্ড", "label_en": "Whiteboard", "swatch": "#E5E7EB",
                   "tint": "#FFFFFF", "tint_alpha": 26, "brightness": 1.08, "contrast": 1.0,
                   "saturation": 0.72, "vignette": 0.05, "box": "#FFFFFFF2", "accent": "#111827",
                   "text": "#111827", "uppercase": False, "line_spacing": 1.34},
    "sketch": {"label_bn": "স্কেচ", "label_en": "Sketch", "swatch": "#D6C9A8",
               "tint": "#EFE6D2", "tint_alpha": 28, "brightness": 1.0, "contrast": 1.14,
               "saturation": 0.5, "vignette": 0.16, "box": "#FFFAF0E6", "accent": "#78716C",
               "text": "#1F2937", "uppercase": False, "line_spacing": 1.34},
    "realistic": {"label_bn": "রিয়ালিস্টিক", "label_en": "Realistic", "swatch": "#0EA5E9",
                  "tint": "#04121F", "tint_alpha": 12, "brightness": 1.0, "contrast": 1.07,
                  "saturation": 1.02, "vignette": 0.22, "box": "#000000AA", "accent": "#0EA5E9",
                  "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.3},
    "slide": {"label_bn": "স্লাইড", "label_en": "Slide", "swatch": "#6366F1",
              "tint": "#0B1220", "tint_alpha": 40, "brightness": 1.0, "contrast": 0.98,
              "saturation": 0.8, "vignette": 0.1, "box": "#0F172AE0", "accent": "#6366F1",
              "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.32},
    "puppet": {"label_bn": "পাপেট", "label_en": "Puppet", "swatch": "#EA580C",
               "tint": "#2A1000", "tint_alpha": 34, "brightness": 1.04, "contrast": 1.14,
               "saturation": 1.26, "vignette": 0.24, "box": "#000000B0", "accent": "#EA580C",
               "text": "#FFFFFF", "uppercase": False, "line_spacing": 1.3},
}

PUNCTUATION = "।,!?;:॥"

DEFAULT_CAPTION_WORDS = 5
DEFAULT_CAPTION_CHARS = 32

MOTION_PRESETS = {
    "auto": {"label_bn": "স্বয়ংক্রিয় (মিশ্র)", "label_en": "Auto (mixed)"},
    "kenburns": {"label_bn": "Ken Burns (জুম + প্যান)", "label_en": "Ken Burns (zoom + pan)"},
    "zoom_in": {"label_bn": "Zoom-In (ধীরে কাছে)", "label_en": "Zoom-In"},
    "zoom_out": {"label_bn": "Zoom-Out (ধীরে দূরে)", "label_en": "Zoom-Out"},
    "pan": {"label_bn": "Pan (পাশে সরানো)", "label_en": "Pan"},
    "none": {"label_bn": "স্থির (নড়াচড়া নেই)", "label_en": "Static"},
}
DEFAULT_MOTION = "auto"


def motion_names():
    return list(MOTION_PRESETS)


def motion_label(motion, ui_lang="bn"):
    preset = MOTION_PRESETS.get(motion, MOTION_PRESETS[DEFAULT_MOTION])
    return preset.get("label_" + ui_lang) or preset["label_en"]


DEFAULT_OPTS = {
    "aspect": "mobile",
    "style": "cinematic",
    "caption_style": "bold",
    "duration": 45,
    "fps": 24,
    "kenburns": True,
    "motion": DEFAULT_MOTION,
    "subtitles": True,
    "progress_bar": True,
    "watermark": "",
    "images": True,
    "stock_video": True,
    "image_source": "auto",
    "own_images_dir": "",
    "allow_network": True,
    "caption_words": DEFAULT_CAPTION_WORDS,
    "title_hold": 0.6,
    "cta_hold": 2.5,
}

_vignette_cache = {}


ILLUSTRATED_STYLES = {"anime", "cartoon2d", "whiteboard", "sketch", "puppet", "slide"}


def style_is_illustrated(style):
    """Animation/cartoon looks must not be mixed with real photos or footage."""
    return str(style or "") in ILLUSTRATED_STYLES


def _is_dark(hex_color):
    value = str(hex_color or "#000000").lstrip("#")[:6]
    try:
        red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return True
    return (0.299 * red + 0.587 * green + 0.114 * blue) < 128


def style_label(style, ui_lang="bn"):
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic"])
    return preset.get("label_" + ui_lang) or preset["label_en"]


def resolve_size(aspect):
    return ASPECTS.get(str(aspect).lower(), ASPECTS["mobile"])


# ------------------------------------------------------------------ timing
def _segment_word_counts(script):
    hook_words = len(script.get("hook", "").split())
    scene_words = [max(1, len(s.get("text", "").split())) for s in script.get("scenes", [])]
    cta_words = len(script.get("cta", "").split())
    return hook_words, scene_words, cta_words


def build_timeline(script, audio, opts):
    """Split the spoken audio into [title, scene..., cta] time ranges."""
    hook_w, scene_w, cta_w = _segment_word_counts(script)
    words = (audio or {}).get("words") or []
    total = float((audio or {}).get("duration") or 0.0)
    counts = [max(1, hook_w)] + [max(1, w) for w in scene_w] + [max(1, cta_w)]
    expected = sum(counts)
    # Sentence-level boundaries (or no timings at all) cannot be sliced per word.
    if words and len(words) < expected * 0.6:
        words = []

    if words and total > 0:
        ranges, cursor = [], 0
        for index, count in enumerate(counts):
            chunks = words[cursor:cursor + count]
            if not chunks:
                start = ranges[-1][1] if ranges else 0.0
                ranges.append((start, start))
                continue
            start = float(chunks[0].get("start", 0.0))
            end = float(chunks[-1].get("end", start))
            if index == 0:
                start = 0.0
            ranges.append((start, end))
            cursor += count
        ranges = _fix_overlaps(ranges)
        if ranges:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], total))
    else:
        weights = counts
        span = total or float(opts.get("duration") or 45)
        ranges, cursor = [], 0.0
        weight_sum = sum(weights)
        for weight in weights:
            length = span * weight / weight_sum
            ranges.append((cursor, cursor + length))
            cursor += length

    if not ranges:
        ranges = [(0.0, float(opts.get("duration") or 45))]

    # keep the title card visible for at least a moment, likewise the CTA
    title_min = float(opts.get("title_hold") or 0.6)
    if ranges[0][1] - ranges[0][0] < title_min:
        ranges[0] = (ranges[0][0], ranges[0][0] + title_min)
    cta_min = float(opts.get("cta_hold") or 2.5)
    if len(ranges) > 1 and ranges[-1][1] - ranges[-1][0] < cta_min:
        ranges[-1] = (ranges[-1][0], ranges[-1][0] + cta_min)
    return ranges


def _fix_overlaps(ranges):
    fixed = []
    for start, end in ranges:
        if fixed and start < fixed[-1][1]:
            start = fixed[-1][1]
        if end < start:
            end = start
        fixed.append((round(start, 3), round(end, 3)))
    return fixed


def caption_chunks(words, text, max_words=DEFAULT_CAPTION_WORDS, max_chars=DEFAULT_CAPTION_CHARS):
    """Group words into readable caption chunks, keeping per-word timings.

    edge-tts word boundaries drop punctuation, so when the token count matches the
    script text we borrow the punctuated words for boundary detection. Chunks never
    cross a sentence break and are split evenly inside a sentence.
    """
    text_words = [token for token in re.split(r"\s+", (text or "").strip()) if token]

    if words and len(text_words) == len(words):
        words = [dict(word, text=token) for word, token in zip(words, text_words)]

    if not words:
        words = [{"text": token, "start": None, "end": None} for token in text_words]

    groups, current = [], []
    for word in words:
        token = str(word.get("text", "")).strip()
        if not token:
            continue
        current.append(word)
        if token[-1] in PUNCTUATION:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    chunks = []
    for group in groups:
        chunks.extend(_split_group(group, max_words, max_chars))
    return chunks


def _split_group(words, max_words, max_chars):
    """Split one punctuation-bounded phrase into evenly balanced pieces."""
    texts = [str(word.get("text", "")).strip() for word in words]
    if len(words) <= max_words and len(" ".join(texts)) <= max_chars:
        return [_chunk_from(words)]

    count = max(1, math.ceil(len(words) / max_words))
    while count < len(words) - 1:
        size = math.ceil(len(words) / count)
        pieces = [words[i:i + size] for i in range(0, len(words), size)]
        if len(pieces) <= count and all(
                len(" ".join(str(w.get("text", "")) for w in piece)) <= max_chars
                for piece in pieces):
            break
        count += 1

    size = max(1, math.ceil(len(words) / count))
    pieces = [words[i:i + size] for i in range(0, len(words), size)]
    return [_chunk_from(piece) for piece in pieces if piece]


def _chunk_from(words):
    tokens = []
    for word in words:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        start = word.get("start")
        end = word.get("end")
        tokens.append({
            "text": text,
            "start": None if start is None else float(start),
            "end": None if end is None else float(end),
        })
    return {
        "text": " ".join(token["text"] for token in tokens),
        "tokens": tokens,
        "start": tokens[0]["start"] if tokens else None,
        "end": tokens[-1]["end"] if tokens else None,
    }


def _words_between(words, start, end):
    out = []
    for word in words:
        mid = (float(word.get("start", 0)) + float(word.get("end", 0))) / 2.0
        if start - 0.15 <= mid <= end + 0.15:
            out.append(word)
    return out


# ------------------------------------------------------------------ visuals
def _vignette_mask(width, height, strength):
    key = (width, height, round(strength, 2))
    if key in _vignette_cache:
        return _vignette_cache[key]
    import numpy as np
    ys = np.linspace(-1.0, 1.0, height)[:, None]
    xs = np.linspace(-1.0, 1.0, width)[None, :]
    radius = np.sqrt(xs ** 2 + ys ** 2)
    mask = 1.0 - np.clip((radius - 0.45) / 0.95, 0.0, 1.0) * strength
    _vignette_cache.clear()
    _vignette_cache[key] = mask
    return mask


def grade_image(img, preset, width, height, seed=0, position="center", vertical_bias=0.0):
    """Cover-crop, colour grade and add readability shading."""
    import numpy as np
    from PIL import Image, ImageEnhance, ImageOps

    offsets = {
        "top": (0.0, -1.0),
        "center": (0.0, max(-1.0, min(1.0, vertical_bias))),
        "bottom": (0.0, 1.0),
    }
    offset = offsets.get(position, (0.0, vertical_bias))
    frame = image_lib.cover_resize(img, width, height, zoom=1.0, offset=offset)

    if preset.get("saturation") is not None:
        frame = ImageEnhance.Color(frame).enhance(preset["saturation"])
    if preset.get("contrast") is not None:
        frame = ImageEnhance.Contrast(frame).enhance(preset["contrast"])
    if preset.get("brightness") is not None:
        frame = ImageEnhance.Brightness(frame).enhance(preset["brightness"])
    if preset.get("posterize"):
        # flat colour bands are what actually makes a frame read as "cartoon"
        frame = ImageOps.posterize(frame, int(preset["posterize"]))

    tint = preset.get("tint")
    alpha = float(preset.get("tint_alpha", 0)) / 255.0
    if tint and alpha > 0:
        from PySide6.QtGui import QColor
        color = QColor(tint)
        tint_layer = Image.new("RGB", frame.size, (color.red(), color.green(), color.blue()))
        frame = Image.blend(frame, tint_layer, alpha)

    strength = float(preset.get("vignette", 0.0))
    if strength > 0:
        mask = _vignette_mask(width, height, strength)
        arr = np.asarray(frame, dtype=np.float32)
        arr *= mask[:, :, None]
        frame = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))

    # bottom shading so captions stay readable on busy photos
    if preset.get("box") and str(preset["box"]).upper().startswith("#0000"):
        shade_h = int(height * 0.42)
        grad = Image.new("L", (1, shade_h))
        for y in range(shade_h):
            grad.putpixel((0, y), int(150 * (y / max(1, shade_h - 1)) ** 1.6))
        grad = grad.resize((width, shade_h))
        overlay = Image.new("RGB", (width, shade_h), (0, 0, 0))
        bottom = frame.crop((0, height - shade_h, width, height))
        frame.paste(Image.composite(overlay, bottom, grad), (0, height - shade_h))
    return frame


def _kenburns_params(index, enabled, rng, motion="auto"):
    """Camera movement for one shot.

    motion: auto | kenburns | zoom_in | zoom_out | pan | none
    """
    if not enabled or motion == "none":
        return {"zoom_from": 1.0, "zoom_to": 1.0, "pan_from": (0.0, 0.0), "pan_to": (0.0, 0.0)}

    amount = rng.uniform(0.06, 0.12)

    if motion == "zoom_in":
        return {"zoom_from": 1.0, "zoom_to": 1.0 + amount, "pan_from": (0.0, 0.0),
                "pan_to": (0.0, 0.0)}
    if motion == "zoom_out":
        return {"zoom_from": 1.0 + amount, "zoom_to": 1.0, "pan_from": (0.0, 0.0),
                "pan_to": (0.0, 0.0)}
    if motion == "pan":
        direction = 1 if index % 2 == 0 else -1
        return {"zoom_from": 1.06, "zoom_to": 1.06,
                "pan_from": (-0.8 * direction, 0.0), "pan_to": (0.8 * direction, 0.0)}
    if motion == "kenburns":
        direction = index % 2
        if direction == 0:
            return {"zoom_from": 1.0, "zoom_to": 1.0 + amount,
                    "pan_from": (-0.3, -0.2), "pan_to": (0.3, 0.2)}
        return {"zoom_from": 1.0 + amount, "zoom_to": 1.0,
                "pan_from": (0.3, 0.2), "pan_to": (-0.3, -0.2)}

    # auto: vary the direction so consecutive scenes never look identical
    direction = index % 4
    if direction == 0:
        return {"zoom_from": 1.0, "zoom_to": 1.0 + amount, "pan_from": (-0.25, -0.15), "pan_to": (0.25, 0.15)}
    if direction == 1:
        return {"zoom_from": 1.0 + amount, "zoom_to": 1.0, "pan_from": (0.25, 0.2), "pan_to": (-0.25, -0.2)}
    if direction == 2:
        return {"zoom_from": 1.0, "zoom_to": 1.0 + amount * 0.8, "pan_from": (0.0, -0.3), "pan_to": (0.0, 0.3)}
    return {"zoom_from": 1.0 + amount * 0.8, "zoom_to": 1.0, "pan_from": (-0.2, 0.25), "pan_to": (0.2, -0.25)}


def build_plan(script, audio, opts=None, work_dir=None, progress=None, cancel=None):
    """Create every image asset and return the render plan."""
    opts = {**DEFAULT_OPTS, **(opts or {})}
    width, height = resolve_size(opts.get("aspect"))
    style = opts.get("style", "cinematic")
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic"])
    rng = random.Random(f"{script.get('title', '')}|{style}|{width}x{height}")

    work_dir = work_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "_work")
    backgrounds = os.path.join(work_dir, "backgrounds")
    captions_dir = os.path.join(work_dir, "captions")
    cards_dir = os.path.join(work_dir, "cards")
    bars_dir = os.path.join(work_dir, "bars")
    for folder in (backgrounds, captions_dir, cards_dir, bars_dir):
        os.makedirs(folder, exist_ok=True)

    textrender.load_fonts()
    timeline = build_timeline(script, audio, opts)
    words = (audio or {}).get("words") or []
    scenes = script.get("scenes") or [{"text": script.get("body", ""), "image_prompt": ""}]

    caption_style = opts.get("caption_style") or textrender.DEFAULT_CAPTION_STYLE
    if caption_style not in textrender.CAPTION_STYLES:
        caption_style = textrender.DEFAULT_CAPTION_STYLE
    motion = opts.get("motion") or DEFAULT_MOTION
    if motion not in MOTION_PRESETS:
        motion = DEFAULT_MOTION
    # headline-sized captions: ~7% of the frame width on vertical video
    caption_size = max(34, int(width * (0.070 if width <= height else 0.050)))
    title_size = max(40, int(width * (0.082 if width <= height else 0.058)))
    caption_pos = "bottom"

    shots = []
    scene_visuals = []

    def _cancelled():
        return bool(cancel and cancel())

    # ---- background per scene
    for index, scene in enumerate(scenes):
        if _cancelled():
            raise RuntimeError("বাতিল করা হয়েছে")
        if progress:
            progress(0.10 + 0.25 * index / max(1, len(scenes)),
                     f"দৃশ্য {index + 1}/{len(scenes)} তৈরি হচ্ছে")
        prompt = scene.get("image_prompt") or script_lib.make_image_prompt(
            scene.get("text", ""), script.get("topic", ""), style, index, script.get("lang", "en"))

        source_mode = opts.get("image_source", "auto")
        illustrated = style_is_illustrated(style)
        if illustrated and source_mode in ("auto", "ai"):
            # an anime/cartoon video must not be filled with real photographs
            source_mode = "art"
        allow_network = bool(opts.get("allow_network", True)) and bool(opts.get("images", True))
        clip_path = None
        matched = bool(scene.get("matched", True))
        if (opts.get("stock_video", True) and allow_network and not illustrated and matched
                and source_mode in ("auto", "stock")):
            from core import videos as stock_lib
            # search with the scene's own keywords, not the whole styled prompt
            query = ", ".join((scene.get("keywords") or [])[:2]).strip() or prompt
            clip_path, clip_note = stock_lib.fetch_clip(
                query, variant=0,
                progress=(lambda msg, i=index: progress(
                    0.10 + 0.25 * i / max(1, len(scenes)), msg)) if progress else None)
            if clip_path and progress:
                progress(0.10 + 0.25 * index / max(1, len(scenes)),
                         f"দৃশ্য {index + 1}: ভিডিও ক্লিপ পাওয়া গেছে")

        if clip_path:
            scene_visuals.append({"path": clip_path, "kind": "video",
                                  "note": clip_note or "ভিডিও ক্লিপ",
                                  "prompt": prompt, "source": clip_path})
        else:
            image, note, image_path = image_lib.scene_visual(
                prompt, width, height, index=index,
                source=source_mode,
                own_dir=opts.get("own_images_dir") or "",
                allow_network=allow_network,
                token=opts.get("image_token") or "",
                style=style,
                progress=(lambda msg, i=index: progress(0.10 + 0.25 * i / max(1, len(scenes)), msg))
                if progress else None,
            )
            graded = grade_image(image, preset, width, height, seed=index, position="center",
                                 vertical_bias=rng.uniform(-0.25, 0.25))
            path = os.path.join(backgrounds, f"scene_{index:02d}.jpg")
            graded.convert("RGB").save(path, quality=92)
            scene_visuals.append({"path": path, "kind": "image", "note": note,
                                  "prompt": prompt, "source": image_path})

    generic = [index + 1 for index, scene in enumerate(scenes)
               if not scene.get("matched", True)]
    if generic and progress:
        progress(0.36, f"{len(generic)}টি দৃশ্যের শব্দ অভিধানে মেলেনি — ছবি সাধারণ হতে পারে")

    # ---- shots: title card, scenes, cta card
    for shot_index, (start, end) in enumerate(timeline):
        if _cancelled():
            raise RuntimeError("বাতিল করা হয়েছে")
        duration = max(0.8, end - start)
        is_title = shot_index == 0
        is_cta = shot_index == len(timeline) - 1 and len(timeline) > 1
        scene_index = 0 if is_title else min(shot_index - 1, len(scene_visuals) - 1)
        source = scene_visuals[max(0, scene_index)]
        shot = {
            "start": round(start, 3),
            "end": round(end + (duration - (end - start)), 3),
            "duration": round(duration, 3),
            "kind": "title" if is_title else ("cta" if is_cta else "scene"),
            "background": source["path"],
            "background_kind": source.get("kind", "image"),
            "note": source["note"],
            "motion": motion,
            "overlays": [],
            **_kenburns_params(shot_index, bool(opts.get("kenburns", True)), rng, motion),
        }

        main_layer = None
        title_color = preset["text"]
        title_outline_color = "#FFFFFF" if _is_dark(title_color) else "#000000"
        title_outline = max(8, int(title_size * 0.13))
        if is_title:
            main_layer = textrender.text_layer_png(
                os.path.join(cards_dir, "title.png"), (width, height),
                script.get("title", ""), font_size=title_size, bold=True,
                color=title_color, box_color=None, outline_width=title_outline,
                outline_color=title_outline_color, accent=preset["accent"],
                valign="center", padding=int(title_size * 0.45), max_width_ratio=0.86,
                line_spacing=1.24)
        elif is_cta:
            main_layer = textrender.text_layer_png(
                os.path.join(cards_dir, "cta.png"), (width, height),
                script.get("cta", ""), font_size=int(title_size * 0.72), bold=True,
                color=title_color, box_color=None, outline_width=title_outline,
                outline_color=title_outline_color, accent=preset["accent"],
                valign="center", padding=int(title_size * 0.4), max_width_ratio=0.84)
        if main_layer:
            shot["overlays"].append({
                "image": main_layer["path"], "x": main_layer["x"], "y": main_layer["y"],
                "kind": "main",
            })

        if opts.get("subtitles", True):
            if is_title:
                segment_words = _words_between(words, start, end) or words[:len(script.get("hook", "").split())]
                text = script.get("hook", "")
            elif is_cta:
                segment_words = _words_between(words, start, end)
                text = script.get("cta", "")
            else:
                segment_words = _words_between(words, start, end)
                text = scenes[scene_index].get("text", "")

            chunks = caption_chunks(segment_words, text,
                                    max_words=int(opts.get("caption_words") or DEFAULT_CAPTION_WORDS))
            if not chunks:
                chunks = [{"text": text, "tokens": [], "start": start, "end": end}]
            for chunk_index, chunk in enumerate(chunks):
                if _cancelled():
                    raise RuntimeError("বাতিল করা হয়েছে")
                chunk_start = chunk.get("start")
                chunk_end = chunk.get("end")
                if chunk_start is None or chunk_end is None:
                    span = (end - start) / max(1, len(chunks))
                    chunk_start = start + span * chunk_index
                    chunk_end = chunk_start + span
                chunk_start = max(start, float(chunk_start))
                chunk_end = max(chunk_start + 0.6, min(float(chunk_end), end + 0.4))

                try:
                    layers = textrender.caption_layers(
                        os.path.join(captions_dir, f"shot{shot_index:02d}_chunk{chunk_index:02d}"),
                        (width, height), chunk["text"], style=caption_style,
                        font_size=caption_size, accent=preset["accent"],
                        uppercase=bool(preset.get("uppercase")),
                        position=caption_pos,
                        margin_ratio=0.17 if width <= height else 0.12,
                    )
                except Exception:
                    continue

                tokens = chunk.get("tokens") or []
                per_word = len(layers) > 1 and len(tokens) == len(layers)
                if per_word:
                    span = (chunk_end - chunk_start) / max(1, len(layers))
                    for index, layer in enumerate(layers):
                        token = tokens[index]
                        w_start = token.get("start")
                        w_end = token.get("end")
                        if w_start is None or w_end is None:
                            w_start = chunk_start + span * index
                            w_end = w_start + span
                        if index == len(layers) - 1:
                            w_end = max(float(w_end), chunk_end)
                        w_start = max(chunk_start, float(w_start))
                        w_end = min(max(float(w_end), w_start + 0.2), chunk_end + 0.45)
                        shot["overlays"].append({
                            "image": layer["path"], "x": layer["x"], "y": layer["y"],
                            "kind": "caption", "word_index": index,
                            "start": round(w_start, 3), "end": round(w_end, 3),
                            "text": token["text"],
                        })
                else:
                    layer = layers[0]
                    shot["overlays"].append({
                        "image": layer["path"], "x": layer["x"], "y": layer["y"],
                        "kind": "caption", "word_index": None,
                        "start": round(chunk_start, 3), "end": round(chunk_end, 3),
                        "text": chunk["text"],
                    })

        if is_cta and words:
            tail = words[-1].get("end")
            if tail and float(tail) > shot["end"]:
                shot["end"] = float(tail)
                shot["duration"] = float(tail) - shot["start"]
        shots.append(shot)

    total_duration = max(shot["start"] + shot["duration"] for shot in shots)
    target = float(opts.get("duration") or 0)
    voice_end = float((audio or {}).get("duration") or 0)
    if target and voice_end and target > voice_end + 2.0:
        # honour the requested length by holding the closing card a bit longer
        shots[-1]["duration"] += (target - voice_end)
        shots[-1]["end"] += (target - voice_end)
        total_duration = max(shot["start"] + shot["duration"] for shot in shots)

    plan = {
        "width": width,
        "height": height,
        "fps": int(opts.get("fps") or 24),
        "duration": round(total_duration, 3),
        "voice_duration": round(voice_end, 3),
        "style": style,
        "preset": preset,
        "shots": shots,
        "visuals": scene_visuals,
        "work_dir": work_dir,
        "watermark": None,
        "progress_bar": None,
    }

    # ---- watermark
    watermark_text = (opts.get("watermark") or "").strip()
    if watermark_text:
        bar_h = max(60, int(height * 0.05))
        entry = textrender.text_layer_png(
            os.path.join(cards_dir, "watermark.png"), (width, bar_h),
            watermark_text, font_size=max(22, int(bar_h * 0.42)), bold=True,
            color="#FFFFFF", box_color="#00000066", accent=None,
            valign="center", padding=int(bar_h * 0.22), max_width_ratio=0.5, margin_ratio=0.0)
        plan["watermark"] = {
            "image": entry["path"],
            "x": max(0, width - entry["width"] - int(width * 0.03)),
            "y": max(0, height - entry["height"] - int(height * 0.035)),
            "height": entry["height"],
            "width": entry["width"],
        }

    # ---- progress bar
    if opts.get("progress_bar", True):
        steps = 48
        bar_height = max(6, int(height * 0.006))
        frames = []
        for step in range(steps):
            ratio = (step + 1) / steps
            frames.append(textrender.progress_layer_png(
                os.path.join(bars_dir, f"bar_{step:02d}.png"),
                (width, bar_height), ratio,
                color=preset["accent"], track_color="#00000055", height=bar_height))
        plan["progress_bar"] = {"frames": frames, "height": bar_height,
                                "start": 0.0, "end": plan["duration"]}
    return plan
