"""Voice catalog and TTS timing tests (no network required)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import tts, voices as voice_lib


def test_voice_catalog_has_bangla_and_english():
    bangla = voice_lib.list_for("bn")
    english = voice_lib.list_for("en")
    assert len(bangla) >= 4
    assert len(english) >= 6
    assert {v["gender"] for v in bangla} == {"male", "female"}


def test_find_voice_matches_language_and_gender():
    assert voice_lib.find("bn", "female", "bd") == "bn-BD-NabanitaNeural"
    assert voice_lib.find("bn", "male", "bd") == "bn-BD-PradeepNeural"
    assert voice_lib.find("en", "female", "us").startswith("en-US")
    # unknown accent falls back to the same language
    assert voice_lib.find("bn", "male", "zz") == "bn-BD-PradeepNeural"


def test_voice_labels_are_bengali():
    label = voice_lib.label("bn-BD-NabanitaNeural", "bn")
    assert "বাংলা" in label
    assert voice_lib.lang_label("bn") == "বাংলা"
    assert voice_lib.gender_label("male") == "পুরুষ"


def test_word_timings_cover_duration():
    words = tts._words_from_text("এক দুই তিন চার পাঁচ", 10.0)
    assert len(words) == 5
    assert words[0]["start"] == 0.0
    assert abs(words[-1]["end"] - 10.0) < 0.001
    for first, second in zip(words, words[1:]):
        assert second["start"] >= first["start"]


def test_empty_text_gives_no_timings():
    assert tts._words_from_text("", 5.0) == []


def test_finalize_writes_timings_file(tmp_path):
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"0" * 2048)
    payload = tts._finalize(str(audio), "test", 3.5,
                            [{"text": "এক", "start": 0.0, "end": 3.5}], "এক", "bn-BD-NabanitaNeural")
    assert payload["duration"] == 3.5
    assert os.path.exists(payload["timings_path"])
    loaded = tts.load_timings(payload["timings_path"])
    assert loaded["words"][0]["text"] == "এক"
    assert loaded["engine"] == "test"


def test_offline_engine_produces_audio_for_supported_language(tmp_path):
    """pyttsx3 is the guaranteed offline path for languages Windows has voices for."""
    if not tts.offline_supports("en"):
        return
    result = tts.synthesize("This is an offline voice test.", out_path=str(tmp_path / "en.wav"),
                            lang="en", engine="pyttsx3")
    assert result["engine"].startswith("pyttsx3")
    assert os.path.exists(result["audio"])
    assert os.path.getsize(result["audio"]) > 1000
    assert result["duration"] > 0.2
    assert result["words"], "টাইমিং অনুমান করা হয়নি"


def test_bangla_offline_either_works_or_reports_clearly(tmp_path):
    """With no Bangla voice pack installed the engine must fail loudly, not silently."""
    try:
        result = tts.synthesize("পরীক্ষার ভয়েস।", out_path=str(tmp_path / "bn.wav"),
                                lang="bn", engine="pyttsx3")
        assert os.path.getsize(result["audio"]) > 1000
        assert result["duration"] > 0.2
    except RuntimeError as exc:
        assert "ভয়েস তৈরি করা যায়নি" in str(exc)
        if not tts.offline_supports("bn"):
            assert "অফলাইন ভয়েস ইনস্টল করা নেই" in str(exc)


def test_auto_engine_never_returns_empty_audio(tmp_path):
    """The auto chain must land on a real engine (network is available here)."""
    result = tts.synthesize("পরীক্ষার বাক্য।", out_path=str(tmp_path / "auto.mp3"), lang="bn")
    assert os.path.getsize(result["audio"]) > 2048
    assert result["duration"] > 0.5


def test_preview_signature_keeps_ui_keywords():
    """The voice page and tools page pass these exact keywords — keep them in sync."""
    import inspect
    parameters = inspect.signature(tts.preview).parameters
    for name in ("text", "lang", "gender", "accent", "voice_id", "rate", "pitch", "engine"):
        assert name in parameters, f"preview() হারানো কীওয়ার্ড: {name}"


def test_preview_accepts_every_ui_keyword():
    """Regression: the UI passes engine=... which preview() must forward."""
    result = tts.preview(text="আজকের কথাটি শুনুন।", lang="bn", gender="female", accent="bd",
                         voice_id="", rate=0, pitch=0, engine="auto")
    assert os.path.getsize(result["audio"]) > 2048
    assert result["engine"]


def test_preview_accepts_offline_engine():
    if not tts.offline_supports("en"):
        return
    result = tts.preview(text="Offline preview check", lang="en", gender="female", accent="us",
                         voice_id=None, rate=0, pitch=0, engine="pyttsx3")
    assert result["engine"].startswith("pyttsx3")
    assert os.path.getsize(result["audio"]) > 1000
