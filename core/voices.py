"""Voice catalog: Bangla/English, male/female, BD/IN/US/UK accents."""

VOICES = [
    # Bangla
    {"id": "bn-BD-NabanitaNeural", "lang": "bn", "gender": "female", "accent": "bd",
     "bn": "বাংলা মহিলা (বাংলাদেশ)", "en": "Bangla Female (Bangladesh)"},
    {"id": "bn-BD-PradeepNeural", "lang": "bn", "gender": "male", "accent": "bd",
     "bn": "বাংলা পুরুষ (বাংলাদেশ)", "en": "Bangla Male (Bangladesh)"},
    {"id": "bn-IN-TanishaaNeural", "lang": "bn", "gender": "female", "accent": "in",
     "bn": "বাংলা মহিলা (ভারত)", "en": "Bangla Female (India)"},
    {"id": "bn-IN-BashkarNeural", "lang": "bn", "gender": "male", "accent": "in",
     "bn": "বাংলা পুরুষ (ভারত)", "en": "Bangla Male (India)"},
    # English
    {"id": "en-US-AriaNeural", "lang": "en", "gender": "female", "accent": "us",
     "bn": "ইংরেজি মহিলা (US)", "en": "English Female (US)"},
    {"id": "en-US-GuyNeural", "lang": "en", "gender": "male", "accent": "us",
     "bn": "ইংরেজি পুরুষ (US)", "en": "English Male (US)"},
    {"id": "en-US-JennyNeural", "lang": "en", "gender": "female", "accent": "us",
     "bn": "ইংরেজি মহিলা (US, নরম)", "en": "English Female (US, soft)"},
    {"id": "en-GB-SoniaNeural", "lang": "en", "gender": "female", "accent": "uk",
     "bn": "ইংরেজি মহিলা (UK)", "en": "English Female (UK)"},
    {"id": "en-GB-RyanNeural", "lang": "en", "gender": "male", "accent": "uk",
     "bn": "ইংরেজি পুরুষ (UK)", "en": "English Male (UK)"},
    {"id": "en-IN-NeerjaNeural", "lang": "en", "gender": "female", "accent": "in",
     "bn": "ইংরেজি মহিলা (ভারত)", "en": "English Female (India)"},
    {"id": "en-IN-PrabhatNeural", "lang": "en", "gender": "male", "accent": "in",
     "bn": "ইংরেজি পুরুষ (ভারত)", "en": "English Male (India)"},
    {"id": "en-AU-NatashaNeural", "lang": "en", "gender": "female", "accent": "au",
     "bn": "ইংরেজি মহিলা (অস্ট্রেলিয়া)", "en": "English Female (Australia)"},
]

LANG_LABELS = {"bn": {"bn": "বাংলা", "en": "Bangla"}, "en": {"bn": "ইংরেজি", "en": "English"}}
GENDER_LABELS = {"female": {"bn": "মহিলা", "en": "Female"}, "male": {"bn": "পুরুষ", "en": "Male"}}
ACCENT_LABELS = {
    "bd": {"bn": "বাংলাদেশ", "en": "Bangladesh"},
    "in": {"bn": "ভারত", "en": "India"},
    "us": {"bn": "আমেরিকা (US)", "en": "United States"},
    "uk": {"bn": "যুক্তরাজ্য (UK)", "en": "United Kingdom"},
    "au": {"bn": "অস্ট্রেলিয়া", "en": "Australia"},
}

DEFAULT_VOICE = {"bn": "bn-BD-NabanitaNeural", "en": "en-US-AriaNeural"}


def label(voice_id, ui_lang="bn"):
    for voice in VOICES:
        if voice["id"] == voice_id:
            return voice.get(ui_lang) or voice["en"]
    return voice_id or ""


def accents_for(lang):
    seen = []
    for voice in VOICES:
        if voice["lang"] == lang and voice["accent"] not in seen:
            seen.append(voice["accent"])
    return seen


def genders_for(lang):
    return [g for g in ("female", "male") if any(v["lang"] == lang and v["gender"] == g for v in VOICES)]


def list_for(lang=None, gender=None, accent=None):
    out = []
    for voice in VOICES:
        if lang and voice["lang"] != lang:
            continue
        if gender and voice["gender"] != gender:
            continue
        if accent and voice["accent"] != accent:
            continue
        out.append(voice)
    return out


def find(lang="bn", gender="female", accent="bd"):
    """Best matching edge-tts voice id for the requested combination."""
    for exact in (True, False):
        for voice in VOICES:
            if voice["lang"] != lang:
                continue
            if voice["gender"] != gender:
                continue
            if exact and voice["accent"] != accent:
                continue
            return voice["id"]
    return DEFAULT_VOICE.get(lang, DEFAULT_VOICE["en"])


def is_valid(voice_id):
    return any(v["id"] == voice_id for v in VOICES)


def accent_label(accent, ui_lang="bn"):
    return ACCENT_LABELS.get(accent, {}).get(ui_lang, accent)


def lang_label(lang, ui_lang="bn"):
    return LANG_LABELS.get(lang, {}).get(ui_lang, lang)


def gender_label(gender, ui_lang="bn"):
    return GENDER_LABELS.get(gender, {}).get(ui_lang, gender)
