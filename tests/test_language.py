"""Language flow and scene-image matching tests.

The two bugs these cover: a Bangla script being voiced in English, and images that
had nothing to do with the script.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import keywords, script as script_lib


def test_bangla_text_wins_over_english_setting():
    script = script_lib.from_own_text("বাংলাদেশের কৃষকরা পরিশ্রম করেন।", title="টেস্ট",
                                      lang="en")
    assert script["lang"] == "bn", "বাংলা লেখা ইংরেজি ভাষায় চলে যাওয়া যাবে না"


def test_english_text_stays_english():
    script = script_lib.from_own_text("This is a short English script.", title="Test",
                                      lang="bn")
    assert script["lang"] == "en"


def test_mixed_text_with_bangla_counts_as_bangla():
    script = script_lib.from_own_text("AI নিয়ে আজকের আলোচনা।", title="টেস্ট")
    assert script["lang"] == "bn"


def test_normalize_lang_without_text_uses_the_setting():
    assert script_lib.normalize_lang("en") == "en"
    assert script_lib.normalize_lang("bn") == "bn"
    assert script_lib.normalize_lang("auto") == "bn"


def test_dictionary_is_large_enough():
    assert len(keywords.BANGLA_TERMS) >= 350, len(keywords.BANGLA_TERMS)


def test_common_words_are_mapped():
    for word, expected in (("কৃষক", "farmer"), ("ফলন", "harvest"), ("মৌসুম", "seasonal"),
                           ("রাজনীতি", "government"), ("নামাজ", "prayer")):
        assert keywords.extract_keywords(f"আজ {word} নিয়ে কথা"), word
        assert any(expected in item for item in keywords.extract_keywords(f"আজ {word} নিয়ে কথা"))


def test_bangla_suffixes_resolve():
    for phrase in ("নদীর ধারে", "নদীতে ভাসে", "নদীটি সুন্দর"):
        assert "river" in keywords.extract_keywords(phrase), phrase


def test_matched_flag_marks_generic_fallbacks():
    matched = script_lib.build_script(title="নদী", body="নদীর ধারে নৌকা চলে।",
                                      lang="bn", topic="নদী")
    assert all(scene["matched"] for scene in matched["scenes"])

    generic = script_lib.build_script(title="অজানা", body="জিব্রিশ ঝাপসা টোকা।",
                                      lang="bn")
    assert not any(scene["matched"] for scene in generic["scenes"])


def test_unknown_text_falls_back_to_a_style_look():
    words, matched = keywords.matched_keywords("জিব্রিশ ঝাপসা টোকা", "", "cinematic")
    assert matched is False
    assert words


def test_apply_image_prompts_replaces_prompts_and_keeps_timing():
    script = script_lib.from_own_text("নদী আর নৌকা। ধানখেত সবুজ।", title="টেস্ট", lang="bn")
    before = [scene["text"] for scene in script["scenes"]]
    prompts = [f"custom prompt {index}" for index in range(len(script["scenes"]))]
    updated = script_lib.apply_image_prompts(script, prompts)
    assert [scene["image_prompt"] for scene in updated["scenes"]] == prompts
    assert [scene["text"] for scene in updated["scenes"]] == before
    assert all(scene["matched"] for scene in updated["scenes"])
    assert updated["prompts_source"] == "ai"


def test_script_language_beats_voice_setting(tmp_path, monkeypatch):
    from core import settings as settings_lib

    monkeypatch.setattr(settings_lib, "settings_path", lambda: str(tmp_path / "settings.json"))
    from ui.state import Studio

    studio = Studio()
    studio.settings["voice"].update({"lang": "en", "accent": "us",
                                     "voice": "en-US-AriaNeural"})
    studio.set_script(script_lib.from_own_text("বাংলা স্ক্রিপ্ট।", title="টেস্ট"))

    opts = studio.render_options()
    assert opts["lang"] == "bn", "স্ক্রিপ্টের ভাষাই প্রাধান্য পাবে"
    assert opts["voice"] == "", "ইংরেজি ভয়েস আইডি বাংলায় ব্যবহার করা যাবে না"
    assert opts["accent"] in ("bd", "in")


def test_english_script_keeps_english_voice(tmp_path, monkeypatch):
    from core import settings as settings_lib

    monkeypatch.setattr(settings_lib, "settings_path", lambda: str(tmp_path / "settings.json"))
    from ui.state import Studio

    studio = Studio()
    studio.settings["voice"].update({"lang": "en", "accent": "us",
                                     "voice": "en-US-GuyNeural"})
    studio.set_script(script_lib.from_own_text("An English script here.", title="Test"))

    opts = studio.render_options()
    assert opts["lang"] == "en"
    assert opts["voice"] == "en-US-GuyNeural"


def test_weak_scene_skips_stock_video(tmp_path):
    """A scene with no matched keywords must not pull in random footage."""
    from core import render as render_lib

    script = script_lib.build_script(title="অজানা", body="জিব্রিশ ঝাপসা টোকা।", lang="bn")
    plan = render_lib.build_plan(
        script, {"duration": 4.0, "words": []},
        {"aspect": "mobile", "style": "cinematic", "images": True, "stock_video": True,
         "allow_network": False, "image_source": "auto", "subtitles": False,
         "progress_bar": False, "duration": 4},
        work_dir=str(tmp_path / "work"))
    kinds = {shot.get("background_kind") for shot in plan["shots"]}
    assert "video" not in kinds
