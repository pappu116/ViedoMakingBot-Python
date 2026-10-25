"""Render planning tests (timing, captions, plan structure)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import render as render_lib


def make_script(scenes=3):
    return {
        "title": "পরীক্ষার ভিডিও",
        "hook": "শুরুতে একটা কথা।",
        "scenes": [{"text": f"দৃশ্য নম্বর {i + 1} এখানে বলা হচ্ছে।", "image_prompt": f"scene {i}"}
                   for i in range(scenes)],
        "cta": "লাইক ও সাবস্ক্রাইব করুন।",
        "body": " ".join(f"দৃশ্য নম্বর {i + 1} এখানে বলা হচ্ছে।" for i in range(scenes)),
        "lang": "bn",
        "topic": "test",
        "tags": ["test"],
    }


WORDS = [
    {"text": "শুরুতে", "start": 0.0, "end": 0.5},
    {"text": "একটা", "start": 0.5, "end": 0.9},
    {"text": "কথা।", "start": 0.9, "end": 1.4},
    {"text": "দৃশ্য", "start": 1.4, "end": 1.8},
    {"text": "নম্বর", "start": 1.8, "end": 2.2},
    {"text": "১", "start": 2.2, "end": 2.5},
    {"text": "এখানে", "start": 2.5, "end": 3.0},
    {"text": "বলা", "start": 3.0, "end": 3.4},
    {"text": "হচ্ছে।", "start": 3.4, "end": 4.0},
    {"text": "দৃশ্য", "start": 4.0, "end": 4.4},
    {"text": "নম্বর", "start": 4.4, "end": 4.8},
    {"text": "২", "start": 4.8, "end": 5.1},
    {"text": "এখানে", "start": 5.1, "end": 5.6},
    {"text": "বলা", "start": 5.6, "end": 6.0},
    {"text": "হচ্ছে।", "start": 6.0, "end": 6.6},
    {"text": "দৃশ্য", "start": 6.6, "end": 7.0},
    {"text": "নম্বর", "start": 7.0, "end": 7.4},
    {"text": "৩", "start": 7.4, "end": 7.7},
    {"text": "এখানে", "start": 7.7, "end": 8.2},
    {"text": "বলা", "start": 8.2, "end": 8.6},
    {"text": "হচ্ছে।", "start": 8.6, "end": 9.2},
    {"text": "লাইক", "start": 9.2, "end": 9.6},
    {"text": "ও", "start": 9.6, "end": 9.7},
    {"text": "সাবস্ক্রাইব", "start": 9.7, "end": 10.3},
    {"text": "করুন।", "start": 10.3, "end": 10.8},
]


def test_timeline_covers_whole_audio():
    script = make_script()
    audio = {"duration": 10.8, "words": WORDS}
    ranges = render_lib.build_timeline(script, audio, render_lib.DEFAULT_OPTS)
    assert len(ranges) == 5  # title + 3 scenes + cta
    assert ranges[0][0] == 0.0
    assert ranges[-1][1] >= 10.0
    for (start, end) in ranges:
        assert end >= start


def test_timeline_without_words_is_proportional():
    script = make_script()
    ranges = render_lib.build_timeline(script, {"duration": 20.0, "words": []},
                                       {"duration": 20})
    assert len(ranges) == 5
    assert ranges[-1][1] >= 18.0


def test_timeline_falls_back_for_sentence_boundaries():
    script = make_script()
    audio = {"duration": 12.0, "words": [{"text": "সেন্টেন্স", "start": 0, "end": 12.0,
                                          "sentence": True}]}
    ranges = render_lib.build_timeline(script, audio, render_lib.DEFAULT_OPTS)
    assert len(ranges) == 5
    assert ranges[-1][1] >= 10.0


def test_caption_chunking_uses_timings():
    chunks = render_lib.caption_chunks(WORDS[:9], "", max_words=3)
    assert len(chunks) == 3
    assert chunks[0]["text"].startswith("শুরুতে")
    assert chunks[0]["start"] == 0.0
    assert chunks[-1]["end"] == 4.0


def test_caption_chunking_without_timings():
    chunks = render_lib.caption_chunks([], "এক দুই তিন চার পাঁচ ছয় সাত", max_words=3)
    assert len(chunks) >= 2
    assert chunks[0]["start"] is None


def test_caption_chunks_never_cross_a_sentence_break():
    """A caption ending mid-sentence looks broken on screen."""
    words = [
        {"text": "শুরু", "start": 0.0, "end": 0.3},
        {"text": "করার", "start": 0.3, "end": 0.6},
        {"text": "আগে", "start": 0.6, "end": 0.9},
        {"text": "একটা", "start": 0.9, "end": 1.2},
        {"text": "কথা", "start": 1.2, "end": 1.5},
        {"text": "শুনুন।", "start": 1.5, "end": 2.0},
        {"text": "এবার", "start": 2.0, "end": 2.3},
        {"text": "শুরু", "start": 2.3, "end": 2.6},
        {"text": "করি।", "start": 2.6, "end": 3.0},
    ]
    chunks = render_lib.caption_chunks(words, "", max_words=4, max_chars=26)
    texts = [chunk["text"] for chunk in chunks]
    # the sentence-final word must be the last word of its chunk
    for chunk in chunks:
        assert not chunk["text"].rstrip().endswith("।।")
    joined = " ".join(texts)
    assert joined == "শুরু করার আগে একটা কথা শুনুন। এবার শুরু করি।"
    # no chunk may start with the tail of a previous sentence
    assert texts[0].startswith("শুরু করার")


def test_caption_chunks_respect_word_limit():
    words = [{"text": f"শব্দ{i}", "start": i * 0.2, "end": (i + 1) * 0.2} for i in range(20)]
    chunks = render_lib.caption_chunks(words, "", max_words=4, max_chars=100)
    for chunk in chunks:
        assert len(chunk["tokens"]) <= 4


def test_long_caption_never_touches_the_frame_edge(tmp_path):
    """Regression: a too-long line must wrap, never run off the picture."""
    import numpy as np
    from PIL import Image

    from core import textrender

    long_text = ("শুরু করার আগে একটা কথা শুনুন এবং শেষ পর্যন্ত দেখুন "
                 "কারণ এখানেই আসল বিষয়টা বলা হয়েছে")
    layers = textrender.caption_layers(
        os.path.join(tmp_path, "long"), (1080, 1920), long_text, style="bold", font_size=76)
    layer = layers[0]
    assert layer["x"] >= 0
    assert layer["x"] + layer["width"] <= 1080, "ক্যাপশন ফ্রেমের বাইরে চলে গেছে"
    alpha = np.array(Image.open(layer["path"]).convert("RGBA"))[:, :, 3]
    columns = np.where(alpha.max(axis=0) > 10)[0]
    assert columns[0] > 2 and columns[-1] < layer["width"] - 3, "লেখা ছবির প্রান্ত ছুঁয়ে ফেলেছে"


def test_build_plan_offline(tmp_path):
    script = make_script()
    opts = {"aspect": "square", "style": "cinematic", "images": False, "image_source": "none",
            "duration": 12, "subtitles": True, "progress_bar": True, "watermark": "@test"}
    plan = render_lib.build_plan(script, {"duration": 10.8, "words": WORDS},
                                 opts, work_dir=str(tmp_path / "work"))
    assert plan["width"] == 1080 and plan["height"] == 1080
    assert len(plan["shots"]) == 5
    assert os.path.exists(plan["shots"][0]["background"])
    assert plan["progress_bar"]["frames"]
    assert plan["watermark"]["image"]
    captions = [o for shot in plan["shots"] for o in shot["overlays"] if o["kind"] == "caption"]
    assert captions, "কোনো ক্যাপশন তৈরি হয়নি"
    assert all(os.path.exists(o["image"]) for o in captions)


def test_resolve_size_variants():
    assert render_lib.resolve_size("mobile") == (1080, 1920)
    assert render_lib.resolve_size("landscape") == (1920, 1080)
    assert render_lib.resolve_size("square") == (1080, 1080)
    assert render_lib.resolve_size("unknown") == (1080, 1920)
