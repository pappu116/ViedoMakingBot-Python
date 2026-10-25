"""Text to speech with word-level timings.

Engine order: edge-tts (free, no key, best quality + real word timings)
-> gTTS (free online) -> pyttsx3 (fully offline).
"""
import asyncio
import concurrent.futures
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import voices as voice_lib
from paths import ensure_dirs, tts_cache_dir

LANG_MAP = {"bn": "bn", "bangla": "bn", "bengali": "bn", "en": "en", "english": "en"}
TLD_MAP = {"bd": "com.bd", "bangladesh": "com.bd", "in": "co.in", "india": "co.in",
           "us": "com", "uk": "co.uk", "au": "com.au"}


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def _words_from_text(text, duration):
    """Fallback word timings when the engine gives none (weighted by word length)."""
    tokens = [t for t in re.split(r"\s+", (text or "").strip()) if t]
    if not tokens:
        return []
    weights = [max(1.0, len(t) ** 0.6) for t in tokens]
    total = sum(weights)
    words, cursor = [], 0.0
    for token, weight in zip(tokens, weights):
        span = duration * weight / total
        words.append({"text": token, "start": round(cursor, 3), "end": round(cursor + span, 3)})
        cursor += span
    return words


def probe_duration(path):
    """Fast, dependency-light duration lookup (wave header first, then ffmpeg)."""
    if not path or not os.path.exists(path):
        return 0.0
    if path.lower().endswith(".wav"):
        try:
            import wave
            with wave.open(path, "rb") as handle:
                rate = handle.getframerate() or 1
                return handle.getnframes() / float(rate)
        except Exception:
            pass
    try:
        from moviepy import AudioFileClip
        clip = AudioFileClip(path)
        duration = float(clip.duration or 0)
        clip.close()
        return duration
    except Exception:
        return 0.0


def _usable_audio(path, minimum=1024):
    """Engines can silently write empty files (missing voice pack), so check."""
    try:
        return os.path.exists(path) and os.path.getsize(path) >= minimum
    except OSError:
        return False


def offline_supports(lang="bn"):
    """Whether an installed Windows voice can actually speak this language."""
    keys = {
        "bn": ("bengali", "bangla", "bn-", "bn_", "heera", "hemant"),
        "en": ("english", "en-", "en_", "zira", "david", "hazel", "mark"),
    }.get(lang, ("english",))
    for _voice_id, name in list_offline_voices():
        lowered = str(name or "").lower()
        if any(key in lowered for key in keys):
            return True
    return False


# ------------------------------------------------------------------- engines
async def _edge_stream(text, out_path, voice_id, rate=0, pitch=0, volume=0):
    import edge_tts
    kwargs = {
        "rate": f"{int(rate):+d}%",
        "pitch": f"{int(pitch):+d}Hz",
        "volume": f"{int(volume):+d}%",
    }
    try:
        communicate = edge_tts.Communicate(text, voice_id, boundary="WordBoundary", **kwargs)
    except TypeError:
        communicate = edge_tts.Communicate(text, voice_id, **kwargs)
    words = []
    with open(out_path, "wb") as fh:
        async for chunk in communicate.stream():
            kind = chunk.get("type")
            if kind == "audio":
                fh.write(chunk["data"])
            elif kind in ("WordBoundary", "SentenceBoundary"):
                start = chunk.get("offset", 0) / 1e7
                span = chunk.get("duration", 0) / 1e7
                entry = {
                    "text": chunk.get("text", ""),
                    "start": round(start, 3),
                    "end": round(start + span, 3),
                }
                if kind == "SentenceBoundary":
                    entry["sentence"] = True
                words.append(entry)
    return words


async def _edge_voice_list():
    import edge_tts
    return await edge_tts.list_voices()


def available_edge_voices(lang=None):
    try:
        data = _run_async(_edge_voice_list())
    except Exception:
        return []
    out = []
    for item in data:
        short = item.get("ShortName", "")
        if lang and not short.startswith(lang):
            continue
        out.append({"id": short, "gender": item.get("Gender", ""), "locale": item.get("Locale", "")})
    return out


def _gtts_save(text, out_path, lang_code, accent):
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang_code, tld=TLD_MAP.get(accent, "com"), slow=False)
    tts.save(out_path)
    return out_path


def _pyttsx3_save(text, out_path, gender, rate):
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", 150 + int(rate) * 2)
    engine.setProperty("volume", 1.0)
    wanted = ["female", "zira", "hazel", "susan"] if gender == "female" else ["male", "david", "mark", "raheem"]
    try:
        for voice in engine.getProperty("voices"):
            name = (getattr(voice, "name", "") or "").lower()
            if any(key in name for key in wanted):
                engine.setProperty("voice", voice.id)
                break
    except Exception:
        pass
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()
    return out_path


def list_offline_voices():
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = [(v.id, getattr(v, "name", v.id)) for v in engine.getProperty("voices")]
        engine.stop()
        return voices
    except Exception:
        return []


# -------------------------------------------------------------------- facade
def synthesize(text, out_path=None, lang="bn", gender="female", accent="bd",
               voice_id=None, rate=0, pitch=0, engine="auto"):
    """Create speech audio and return {audio, engine, duration, words, timings_path, text}."""
    ensure_dirs()
    text = (text or "").strip() or " "
    lang_code = LANG_MAP.get(str(lang).lower(), "bn" if re.search(r"[\u0980-\u09FF]", text) else "en")
    voice_id = voice_id or voice_lib.find(lang_code, gender, accent)

    if not out_path:
        import hashlib
        digest = hashlib.md5(f"{text}|{voice_id}|{rate}|{pitch}".encode("utf-8")).hexdigest()[:16]
        out_path = os.path.join(tts_cache_dir(), digest + ".mp3")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    order = ["edge", "gtts", "pyttsx3"] if engine in ("auto", None, "") else [engine]
    errors = []
    for name in order:
        try:
            if name == "edge":
                target = os.path.splitext(out_path)[0] + ".mp3"
                words = _run_async(_edge_stream(text, target, voice_id, rate, pitch))
                if not _usable_audio(target, 2048):
                    raise RuntimeError("edge-tts খালি ফাইল দিয়েছে")
                duration = words[-1]["end"] if words else probe_duration(target)
                return _finalize(target, "edge-tts", duration, words, text, voice_id)
            if name == "gtts":
                target = os.path.splitext(out_path)[0] + ".gtts.mp3"
                _gtts_save(text, target, lang_code, accent)
                if not _usable_audio(target, 2048):
                    raise RuntimeError("gTTS খালি ফাইল দিয়েছে")
                duration = probe_duration(target)
                return _finalize(target, "gTTS", duration,
                                 _words_from_text(text, duration), text, voice_id)
            if name == "pyttsx3":
                target = os.path.splitext(out_path)[0] + ".offline.wav"
                _pyttsx3_save(text, target, gender, rate)
                duration = probe_duration(target)
                if not _usable_audio(target) or duration < 0.2:
                    hint = ("" if offline_supports(lang_code) else
                            " — এই ভাষার অফলাইন ভয়েস ইনস্টল করা নেই")
                    raise RuntimeError("pyttsx3 কিছু তৈরি করেনি" + hint)
                return _finalize(target, "pyttsx3 (অফলাইন)", duration,
                                 _words_from_text(text, duration), text, voice_id)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError(
        "ভয়েস তৈরি করা যায়নি — ইন্টারনেট সংযোগ দেখুন। বিস্তারিত: " + " | ".join(errors))


def _finalize(audio_path, engine_name, duration, words, text, voice_id):
    timings_path = os.path.splitext(audio_path)[0] + ".timings.json"
    payload = {
        "engine": engine_name,
        "voice": voice_id,
        "duration": round(float(duration or 0), 3),
        "words": words,
        "text": text,
    }
    try:
        with open(timings_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError:
        timings_path = None
    payload["audio"] = audio_path
    payload["timings_path"] = timings_path
    return payload


def load_timings(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"engine": "?", "duration": 0.0, "words": []}


def preview(text, lang="bn", gender="female", accent="bd", voice_id=None, rate=0, pitch=0,
            engine="auto"):
    """Short voice preview used by the wizard's listen button."""
    sample = (text or "").strip()
    if not sample:
        sample = "আমি বাংলায় কথা বলছি।" if lang == "bn" else "This is a voice preview."
    sample = " ".join(sample.split()[:40])
    return synthesize(sample, lang=lang, gender=gender, accent=accent,
                      voice_id=voice_id or None, rate=int(rate or 0), pitch=int(pitch or 0),
                      engine=engine or "auto")
