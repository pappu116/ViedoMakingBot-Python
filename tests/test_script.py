"""Script building and template tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import script as script_lib


def test_templates_exist():
    templates = script_lib.load_templates("all")
    assert templates, "কোনো টেমপ্লেট পাওয়া যায়নি"
    assert any(t.get("niche") == "motivational" for t in templates)


def test_from_template_builds_scenes():
    items = script_lib.from_template("motivational", 2)
    assert len(items) == 2
    for item in items:
        assert item["title"]
        assert item["body"]
        assert len(item["scenes"]) >= 1
        for scene in item["scenes"]:
            assert scene["text"].strip()
            assert scene["image_prompt"].strip()


def test_own_text_bangla_detection():
    script = script_lib.from_own_text(
        "প্রথম বাক্য এখানে। দ্বিতীয় বাক্যটি আরও একটু লম্বা হবে যাতে দৃশ্য ভাগ হয়।",
        title="পরীক্ষা")
    assert script["lang"] == "bn"
    assert script["title"] == "পরীক্ষা"
    assert len(script["scenes"]) >= 1
    assert script["cta"]


def test_own_text_english_detection():
    script = script_lib.from_own_text("First sentence here. Second one is longer for splitting.")
    assert script["lang"] == "en"
    assert script["scenes"]


def test_sentence_split_handles_danda():
    sentences = script_lib.split_sentences("এক। দুই! তিন? Four.")
    assert len(sentences) == 4


def test_group_scenes_respects_limits():
    text = " ".join(f"এটি বাক্য নম্বর {i}।" for i in range(12))
    scenes = script_lib.group_scenes(script_lib.split_sentences(text), max_chars=120, max_sentences=2)
    assert 4 <= len(scenes) <= 12


def test_srt_stripping():
    raw = "1\n00:00:01,000 --> 00:00:03,000\nপ্রথম লাইন\n\n2\n00:00:03,000 --> 00:00:05,000\nদ্বিতীয় লাইন\n"
    assert script_lib.strip_srt(raw) == "প্রথম লাইন দ্বিতীয় লাইন"


def test_image_prompt_is_english_and_descriptive():
    prompt = script_lib.make_image_prompt("বাংলা লেখা", "bangladesh", "cinematic", 0, "bn")
    assert "cinematic" in prompt
    assert len(prompt) > 20
