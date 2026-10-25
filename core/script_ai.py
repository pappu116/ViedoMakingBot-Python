"""AI script generation with free/keyless providers and a hard JSON contract.

Providers: pollinations (no key), gemini, groq, openrouter (free keys), ollama (local).
Any failure falls back to a template script so the pipeline never stalls.
"""
import json
import re
import sys
import os

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import script as script_lib

TIMEOUT = 90

PROVIDERS = [
    {"id": "pollinations", "name": "Pollinations (key লাগে না)", "needs_key": False,
     "hint": "ইন্টারনেট থাকলেই কাজ করে"},
    {"id": "gemini", "name": "Google Gemini (ফ্রি key)", "needs_key": True,
     "hint": "aistudio.google.com থেকে ফ্রি key"},
    {"id": "groq", "name": "Groq (ফ্রি key)", "needs_key": True,
     "hint": "console.groq.com — খুব দ্রুত"},
    {"id": "openrouter", "name": "OpenRouter (ফ্রি key)", "needs_key": True,
     "hint": "openrouter.ai — ফ্রি মডেল"},
    {"id": "ollama", "name": "Ollama (লোকাল)", "needs_key": False,
     "hint": "লোকাল মডেল, ইন্টারনেট লাগে না"},
]

DEFAULT_MODELS = {
    "pollinations": "openai",
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    "ollama": "llama3.1",
}

SYSTEM_PROMPT = (
    "You are a short-video scriptwriter for YouTube Shorts, Facebook Reels and TikTok. "
    "Return ONLY valid minified JSON, no markdown, no explanation."
)

JSON_TEMPLATE = """{
  "title": "click-worthy title under 70 chars",
  "hook": "one attention grabbing opening line",
  "scenes": [{"text": "1-2 spoken sentences", "image_prompt": "english visual description for image generation"}],
  "cta": "closing call to action line",
  "description": "2-3 line video description",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}"""


def provider_info(provider_id):
    for item in PROVIDERS:
        if item["id"] == provider_id:
            return item
    return PROVIDERS[0]


def build_prompt(topic, lang="bn", tone="educational", duration_sec=45, scene_count=None):
    language = "Bengali (বাংলা)" if script_lib.lang_code(lang) == "bn" else "English"
    words = max(6, int((duration_sec or 45) / 2.4))
    scenes = scene_count or max(4, min(12, int((duration_sec or 45) / 8) + 2))
    return (
        f"Write a short vertical video script about: {topic}\n"
        f"Language of all spoken text (title, hook, scenes, cta, description): {language}.\n"
        f"Tone: {tone}. Target length: about {words} spoken words. Number of scenes: {scenes}.\n"
        "Rules: the first 3 seconds must hook the viewer; each scene is one idea; "
        "image_prompt must always be in English and describe a concrete visual (no text in image).\n"
        f"Return exactly this JSON shape:\n{JSON_TEMPLATE}"
    )


def _extract_json(text):
    if not text:
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.S)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        snippet = raw[start:end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            try:
                return json.loads(re.sub(r",\s*([}\]])", r"\1", snippet))
            except Exception:
                return None
    return None


# ------------------------------------------------------------------ providers
def _http_json(url, payload, headers=None, method="post"):
    if method == "get":
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    else:
        resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _call_pollinations(prompt, model=None):
    url = "https://text.pollinations.ai/openai"
    payload = {
        "model": model or DEFAULT_MODELS["pollinations"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        data = _http_json(url, payload)
        return data["choices"][0]["message"]["content"]
    except Exception:
        resp = requests.get(
            "https://text.pollinations.ai/" + requests.utils.quote(prompt),
            params={"model": model or DEFAULT_MODELS["pollinations"], "json": "true"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text


def _call_gemini(prompt, key, model=None):
    if not key:
        raise ValueError("Gemini API key দরকার")
    model = model or DEFAULT_MODELS["gemini"]
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           f":generateContent?key={key}")
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }
    data = _http_json(url, payload)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_openai_compatible(prompt, key, endpoint, model, extra_headers=None):
    if not key:
        raise ValueError("API key দরকার")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
    }
    try:
        data = _http_json(endpoint, payload, headers=headers)
    except Exception:
        payload.pop("response_format", None)
        data = _http_json(endpoint, payload, headers=headers)
    return data["choices"][0]["message"]["content"]


def _call_ollama(prompt, model=None, base_url="http://localhost:11434"):
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model or DEFAULT_MODELS["ollama"],
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    data = _http_json(url, payload)
    return data["message"]["content"]


def raw_completion(prompt, provider="pollinations", key="", model=None, ollama_url=None):
    provider = provider or "pollinations"
    model = model or DEFAULT_MODELS.get(provider)
    if provider == "pollinations":
        return _call_pollinations(prompt, model)
    if provider == "gemini":
        return _call_gemini(prompt, key, model)
    if provider == "groq":
        return _call_openai_compatible(prompt, key, "https://api.groq.com/openai/v1/chat/completions", model)
    if provider == "openrouter":
        return _call_openai_compatible(
            prompt, key, "https://openrouter.ai/api/v1/chat/completions", model,
            extra_headers={"HTTP-Referer": "https://localhost", "X-Title": "YTFB Studio"},
        )
    if provider == "ollama":
        return _call_ollama(prompt, model, ollama_url or "http://localhost:11434")
    raise ValueError("অজানা AI প্রোভাইডার: " + str(provider))


def _extract_list(text):
    """Parse a JSON array from an AI reply."""
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.S)
    if fence:
        raw = fence.group(1).strip()
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end > start:
        snippet = raw[start:end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            try:
                return json.loads(re.sub(r",\s*([\]}])", r"\1", snippet))
            except Exception:
                pass
    data = _extract_json(raw)
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
    return None


def generate_image_prompts(scenes, provider="pollinations", keys=None, key="", model=None,
                           ollama_url=None, style="cinematic"):
    """Ask the AI for one English image prompt per scene (raises on failure)."""
    scenes = scenes or []
    if not scenes:
        raise ValueError("কোনো দৃশ্য নেই")
    numbered = "\n".join(
        f"{index + 1}. {str(scene.get('text', '')).strip()}"
        for index, scene in enumerate(scenes))
    prompt = (
        "For each numbered scene below, write ONE English prompt for an image generator "
        "that visually shows what that scene says. Rules: describe a concrete visual "
        "subject and setting; no text, letters or logos in the image; no camera jargon; "
        f"at most 18 words each. Return ONLY a JSON array of {len(scenes)} strings in the "
        "same order.\n\n" + numbered)
    keys = keys or {}
    if not key:
        key = keys.get(provider, "")
    raw = raw_completion(prompt, provider=provider, key=key, model=model, ollama_url=ollama_url)
    items = _extract_list(raw)
    if not isinstance(items, list) or not items:
        raise ValueError("AI ঠিকভাবে উত্তর দেয়নি")
    prompts = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("prompt") or item.get("image_prompt") or item.get("text") or ""
        text = str(item).strip().strip('"').strip()
        prompts.append(text)
    prompts = [p for p in prompts if p]
    if len(prompts) < len(scenes):
        # pad with the existing prompts rather than losing the alignment
        for index in range(len(prompts), len(scenes)):
            prompts.append(str(scenes[index].get("image_prompt") or "").strip())
    return prompts[:len(scenes)]


# --------------------------------------------------------------------- facade
def generate_script(topic, provider="pollinations", keys=None, key="", model=None,
                    lang="bn", tone="educational", duration_sec=45, style="cinematic",
                    ollama_url=None):
    """Return a full script dict. Never raises: falls back to templates."""
    keys = keys or {}
    if not key:
        key = keys.get(provider, "")
    prompt = build_prompt(topic, lang=lang, tone=tone, duration_sec=duration_sec)
    warnings = []
    try:
        raw = raw_completion(prompt, provider=provider, key=key, model=model, ollama_url=ollama_url)
        data = _extract_json(raw)
        if not data:
            raise ValueError("AI উত্তর পড়া যায়নি")
        scenes = []
        for item in data.get("scenes") or []:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                prompt_text = str(item.get("image_prompt", "")).strip()
            else:
                text, prompt_text = str(item).strip(), ""
            if not text:
                continue
            scenes.append({
                "text": text,
                "image_prompt": prompt_text or script_lib.make_image_prompt(
                    text, topic, style, len(scenes), lang),
            })
        if not scenes:
            raise ValueError("AI কোনো দৃশ্য দেয়নি")
        built = script_lib.build_script(
            title=str(data.get("title", "")).strip() or topic[:70],
            body=" ".join(s["text"] for s in scenes),
            tags=data.get("tags") or [],
            niche="custom",
            topic=topic,
            lang=lang,
            hook=str(data.get("hook", "")).strip() or None,
            cta=str(data.get("cta", "")).strip() or None,
            style=style,
            image_prompts=[s["image_prompt"] for s in scenes],
            source="ai:" + provider,
        )
        if data.get("description"):
            built["description"] = str(data["description"]).strip()
        return built
    except Exception as exc:
        warnings.append(f"{provider} ব্যর্থ: {exc}")
    fallback = script_lib.from_own_text(
        _topic_seed(topic, lang), title=topic[:70] or None, lang=lang, style=style)
    fallback["source"] = "template"
    fallback["warnings"] = warnings
    return fallback


def _topic_seed(topic, lang):
    """Build a usable body from templates when the AI route failed."""
    try:
        items = script_lib.from_template("all", 1)
        base = items[0]["body"]
    except Exception:
        base = (f"{topic} নিয়ে আজকের গুরুত্বপূর্ণ কথাগুলো শুনুন এবং শেষ পর্যন্ত দেখুন।"
                if script_lib.lang_code(lang) == "bn" else
                f"Here is why {topic} matters and what you should know about it.")
    if topic and script_lib.lang_code(lang) == "bn":
        return f"{topic} — {base}"
    return base
