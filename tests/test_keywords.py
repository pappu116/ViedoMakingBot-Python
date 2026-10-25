"""Visual keyword extraction (Bangla -> English) tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import keywords, script as script_lib


def test_bangla_words_map_to_visuals():
    words = keywords.extract_keywords("বাংলাদেশের নদী আমাদের প্রাণ।")
    assert "river" in words
    assert any("bangladesh" in word for word in words)


def test_bangla_suffixes_are_stripped():
    assert "river" in keywords.extract_keywords("নদীটি অনেক সুন্দর")
    assert "mountain" in keywords.extract_keywords("পাহাড়ে বরফ পড়ে")


def test_multiple_concepts_are_kept():
    words = keywords.extract_keywords("সবুজ ধানখেত আর নীল আকাশ")
    assert "rice field" in words
    assert "blue sky" in words


def test_english_stopwords_are_dropped():
    words = keywords.extract_keywords("5 amazing facts about the ocean you never knew")
    assert "ocean" in words
    assert "facts" not in words
    assert "never" not in words


def test_unknown_text_falls_back_to_a_style_hint():
    prompt = script_lib.make_image_prompt("আজকে আকাশ পরিষ্কার।", "", "cinematic")
    assert "sky" in prompt
    assert "cinematic" in prompt


def test_prompt_includes_style():
    prompt = script_lib.make_image_prompt("নৌকা চলে স্রোতের টানে।", "", "dramatic")
    assert "boat" in prompt
    assert "dramatic" in prompt.lower()


def test_scenes_get_keywords_and_prompts():
    script = script_lib.from_own_text(
        "নদী আর নৌকা আমাদের জীবন। ধানখেত সবুজ আর সুন্দর।", title="নদী")
    assert script["scenes"]
    for scene in script["scenes"]:
        assert scene.get("keywords"), "কীওয়ার্ড নেই"
        assert scene.get("image_prompt")


def test_bangla_template_prompts_use_the_body_text():
    """Bangla templates carry Bangla bodies — keywords must come from the text."""
    scripts = script_lib.from_template("bangla", 3)
    assert scripts
    for script in scripts:
        assert script["scenes"]
        for scene in script["scenes"]:
            assert scene.get("keywords"), scene
            assert scene.get("image_prompt", "").strip()
        joined = " ".join(s["image_prompt"] for s in script["scenes"]).lower()
        # visual words, never raw Bangla, go into the image prompt
        assert not any("\u0980" <= ch <= "\u09ff" for ch in joined)


def test_english_template_prompts_use_curated_visuals():
    script = script_lib.from_template("motivational", 1)[0]
    joined = " ".join(scene["image_prompt"] for scene in script["scenes"]).lower()
    assert any(word in joined for word in ("climb", "summit", "run", "road", "sunrise",
                                           "gym", "horizon", "silhouette"))


def test_search_query_is_short():
    query = keywords.search_query("বাংলাদেশের সবুজ ধানখেত আর নীল আকাশ দেখতে অসাধারণ")
    assert query
    assert len(query.split()) <= 4


def test_empty_input_is_safe():
    assert keywords.extract_keywords("") == []
    assert keywords.visual_keywords("", "", "cinematic")
