"""Script building: template engine, scene splitting, image prompts, CTA.

Templates live in content/templates/*.json so new niches only need a JSON file.
"""
import glob
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import template_dir

NICHES = ["motivational", "facts", "stories", "tech", "health", "bangla"]

STYLE_VISUALS = {
    "cinematic": "cinematic film still, dramatic lighting, shallow depth of field, 35mm",
    "dramatic": "dramatic moody scene, high contrast, deep shadows, emotional",
    "educational": "clean modern illustration, bright clear lighting, infographic style",
    "tutorial": "clean tutorial photo, bright even lighting, clear subject, high clarity, "
                "step by step how-to look",
    "vibrant": "vibrant colorful scene, saturated colors, energetic, bright",
    "anime": "anime style illustration, cel shaded, clean lineart, detailed anime background, "
             "no photorealism, no photograph",
    "cartoon2d": "flat 2d cartoon illustration, bold clean outlines, simple shapes, "
                 "no photorealism, no photograph",
    "whiteboard": "whiteboard doodle drawing, black marker on white, simple sketch, "
                  "no photorealism",
    "sketch": "pencil sketch drawing, hand drawn, textured paper, no photorealism",
    "puppet": "cute 3d puppet character, felt texture, stop motion look, no photorealism",
    "realistic": "photorealistic photograph, natural light, highly detailed",
    "slide": "minimal presentation background, soft gradient, clean vector shapes",
}

VISUAL_KEYWORDS = {
    "motivational": [
        "lone climber reaching a mountain summit at sunrise",
        "person running on a foggy city street at dawn",
        "silhouette standing before a huge bright horizon",
        "determined athlete training in an empty gym",
        "open road stretching into golden sunset",
    ],
    "facts": [
        "glowing planet earth seen from space",
        "abstract science visualization with particles",
        "ancient library with floating books",
        "microscope view of colorful cells",
        "futuristic data visualization of the world",
    ],
    "stories": [
        "lone traveler walking through a quiet village path",
        "child reading a book under warm lamp light",
        "old workshop with tools and handmade craft",
        "teacher writing on a blackboard in a small classroom",
        "person planting a sapling at golden hour",
    ],
    "tech": [
        "futuristic circuit board glowing blue",
        "server room with neon lights",
        "humanoid robot in a modern laboratory",
        "smartphone interface holograms floating in air",
        "city skyline with digital network overlay",
    ],
    "health": [
        "fresh fruits and vegetables on a wooden table",
        "person meditating in a bright peaceful room",
        "morning jog in a green park",
        "glass of water with lemon on a clean desk",
        "healthy meal bowl photographed from above",
    ],
    "bangla": [
        "green rice fields of rural bengal at sunrise",
        "colorful rickshaw art on a dhaka street",
        "boat on a wide river at sunset in bangladesh",
        "traditional bengali village house with palm trees",
        "tea garden hills of sylhet in the morning mist",
    ],
    "custom": [
        "cinematic establishing shot with dramatic light",
        "close up detail shot with soft bokeh",
        "wide landscape view at golden hour",
        "person in motion with motion blur background",
        "abstract background with depth and texture",
    ],
}

BN_CTA = "ভিডিওটি ভালো লাগলে লাইক, শেয়ার আর সাবস্ক্রাইব করতে ভুলবেন না।"
EN_CTA = "If you enjoyed this, like, share and subscribe for more."

BN_HOOKS = [
    "শুরু করার আগে একটা কথা শুনুন।",
    "এই বিষয়টা আপনার ধারণা বদলে দিতে পারে।",
    "শেষ পর্যন্ত দেখুন, কারণ এটা গুরুত্বপূর্ণ।",
]

EN_HOOKS = [
    "Here is something most people get wrong.",
    "Watch this before you scroll past.",
    "This one idea can change your results.",
]


def _is_bangla(text):
    return bool(re.search(r"[\u0980-\u09FF]", text or ""))


def lang_code(lang):
    return "bn" if str(lang).lower() in ("bn", "bangla", "bengali", "বাংলা") else "en"


def normalize_lang(lang, text=""):
    """The written text decides the language.

    A Bangla script must never be voiced with an English voice just because a
    dropdown was left on English — that produced broken, English-sounding audio.
    """
    text = (text or "").strip()
    if text:
        return "bn" if _is_bangla(text) else "en"
    if str(lang).lower() in ("auto", "", "none"):
        return "bn"
    return lang_code(lang)


# ---------------------------------------------------------------- templates
def load_templates(niche="all"):
    files = glob.glob(os.path.join(template_dir(), "*.json"))
    templates = []
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        if not isinstance(data, dict) or "body_patterns" not in data:
            continue
        if niche not in ("all", None) and data.get("niche") != niche:
            continue
        templates.append(data)
    return templates


def available_niches():
    names = sorted({t.get("niche") for t in load_templates("all") if t.get("niche")})
    return names or ["custom"]


def _fill(text, slots):
    out = str(text)
    for key, values in (slots or {}).items():
        placeholder = "{" + key + "}"
        while placeholder in out and values:
            out = out.replace(placeholder, str(random.choice(values)), 1)
    return re.sub(r"\{[a-z_]+\}", "", out).strip()


def from_template(niche="all", count=1):
    templates = load_templates(niche)
    if not templates:
        templates = load_templates("all")
    if not templates:
        raise ValueError("কোনো টেমপ্লেট পাওয়া যায়নি: " + str(niche))
    results = []
    for _ in range(count):
        tpl = random.choice(templates)
        slots = tpl.get("slots", {})
        title = _fill(random.choice(tpl["title_patterns"]), slots)
        body = _fill(random.choice(tpl["body_patterns"]), slots)
        topic = _fill("{topic}", slots) if "{topic}" in json.dumps(slots) else title
        script = build_script(
            title=title,
            body=body,
            tags=tpl.get("tags", []),
            niche=tpl.get("niche", "custom"),
            topic=topic or title,
            source="template",
        )
        # English templates are generic filler, so pair them with the curated visuals
        # for their niche. Bangla templates already yield good keywords from the text.
        pool = VISUAL_KEYWORDS.get(tpl.get("niche")) or VISUAL_KEYWORDS["custom"]
        style = script.get("style", "cinematic")
        style_hint = STYLE_VISUALS.get(style, STYLE_VISUALS["cinematic"])
        topic_en = topic if topic and not _is_bangla(topic) else ""
        body_is_bangla = _is_bangla(script.get("body", ""))
        for index, scene in enumerate(script.get("scenes") or []):
            if body_is_bangla and scene.get("keywords"):
                continue
            visual = pool[index % len(pool)]
            pieces = [p for p in (topic_en, visual) if p]
            scene["keywords"] = pieces
            scene["image_prompt"] = f"{', '.join(pieces)}, {style_hint}"
        results.append(script)
    return results


# ---------------------------------------------------------------- text utils
def split_sentences(text):
    text = re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[।!?\.])\s+", text)
    out = []
    for part in parts:
        piece = part.strip()
        if piece:
            out.append(piece)
    return out


def group_scenes(sentences, max_chars=170, max_sentences=2):
    scenes, current = [], ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip()
        count = len(split_sentences(current))
        if current and (len(candidate) > max_chars or count >= max_sentences):
            scenes.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        scenes.append(current)
    return scenes or [" "]


def make_image_prompt(text, topic="", style="cinematic", index=0, lang="en"):
    """English image prompt derived from what the scene actually says.

    The style hint comes first because image models weight the start of the prompt
    more heavily — this is what makes 'anime' actually look like anime.
    """
    from core import keywords as keyword_lib

    style_hint = STYLE_VISUALS.get(style, STYLE_VISUALS["cinematic"])
    words = keyword_lib.visual_keywords(text, topic, style, limit=4)
    if not words:
        keys = VISUAL_KEYWORDS.get("custom") or ["cinematic scene"]
        words = [keys[index % len(keys)]]
    return f"{style_hint}, {', '.join(words)}"


def apply_style(script, style):
    """Re-write every scene prompt for a newly chosen video style."""
    style_hint = STYLE_VISUALS.get(style, STYLE_VISUALS["cinematic"])
    scenes = []
    for index, scene in enumerate(script.get("scenes") or []):
        scene = dict(scene)
        words = scene.get("keywords") or []
        if not words:
            from core import keywords as keyword_lib
            words, matched = keyword_lib.matched_keywords(
                scene.get("text", ""), script.get("topic", ""), style, limit=4)
            scene["keywords"] = words
            scene["matched"] = matched
        scene["image_prompt"] = f"{style_hint}, {', '.join(words)}" if words else style_hint
        scenes.append(scene)
    updated = dict(script)
    updated["style"] = style
    updated["scenes"] = scenes
    return updated


def apply_image_prompts(script, prompts):
    """Replace every scene prompt with an AI-written one (keeps timing/keywords)."""
    scenes = []
    for index, scene in enumerate(script.get("scenes") or []):
        scene = dict(scene)
        prompt = ""
        if prompts and index < len(prompts):
            prompt = str(prompts[index] or "").strip()
        if prompt:
            scene["image_prompt"] = prompt
            scene["matched"] = True
            scene["keywords"] = [part.strip() for part in prompt.split(",") if part.strip()][:4]
        scenes.append(scene)
    updated = dict(script)
    updated["scenes"] = scenes
    updated["prompts_source"] = "ai"
    return updated


def build_cta(lang="en"):
    return BN_CTA if lang_code(lang) == "bn" else EN_CTA


def build_hook(lang="en", topic=""):
    pool = BN_HOOKS if lang_code(lang) == "bn" else EN_HOOKS
    return random.choice(pool)


def _description(title, body, tags):
    head = (body or "").strip()
    short = head[:200] + ("..." if len(head) > 200 else "")
    tagline = " ".join("#" + str(t).replace(" ", "") for t in (tags or [])[:8])
    return (short + "\n\n" + tagline).strip()


# ---------------------------------------------------------------- builders
def build_script(title, body, tags=None, niche="custom", topic=None, lang="auto",
                 hook=None, cta=None, style="cinematic", image_prompts=None, source="own"):
    from core import keywords as keyword_lib

    body = (body or "").strip()
    lang = normalize_lang(lang, body or title)
    title = (title or "").strip() or (body.split(".")[0][:60] if body else "নতুন ভিডিও")
    topic = topic or (title if not _is_bangla(title) else "")
    sentences = split_sentences(body)
    scene_texts = group_scenes(sentences)
    scenes = []
    for i, text in enumerate(scene_texts):
        keywords, matched = keyword_lib.matched_keywords(text, topic, style, limit=4)
        prompt = None
        if image_prompts and i < len(image_prompts) and image_prompts[i]:
            prompt = image_prompts[i]
        scenes.append({
            "text": text,
            "keywords": keywords,
            "matched": matched,
            "image_prompt": prompt or make_image_prompt(text, topic, style, i, lang),
        })
    return {
        "title": title,
        "hook": hook or build_hook(lang, topic),
        "body": body,
        "cta": cta or build_cta(lang),
        "scenes": scenes,
        "description": _description(title, body, tags),
        "tags": [str(t).strip() for t in (tags or []) if str(t).strip()],
        "niche": niche,
        "topic": topic,
        "lang": lang,
        "style": style,
        "source": source,
    }


def from_own_text(text, title=None, lang="auto", tags=None, style="cinematic"):
    text = (text or "").strip()
    if not text:
        raise ValueError("স্ক্রিপ্ট খালি")
    if not title:
        first_line = text.splitlines()[0].strip()
        title = first_line[:70] if first_line else "আমার ভিডিও"
    return build_script(title=title, body=text, tags=tags, niche="custom",
                        lang=lang, style=style, source="own")


def strip_srt(text):
    """Turn .srt/.vtt subtitle text into plain script text."""
    lines = []
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw or raw.isdigit() or "-->" in raw or raw.upper().startswith("WEBVTT"):
            continue
        lines.append(raw)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def load_script_file(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        raw = fh.read()
    if path.lower().endswith((".srt", ".vtt")):
        return strip_srt(raw)
    return raw.strip()
