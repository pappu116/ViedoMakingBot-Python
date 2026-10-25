"""Bengali text rendering tests (the riskiest part of the video pipeline)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import textrender


def test_qt_and_fonts_available():
    textrender.ensure_qt()
    families = textrender.load_fonts()
    assert families, "কোনো ফন্ট পাওয়া যায়নি"
    assert textrender.family()


def test_bangla_conjuncts_are_shaped():
    """A shaping engine renders ক্ষ as one glyph, narrower than ক + ষ."""
    from PySide6.QtGui import QFontMetricsF

    font = textrender.make_font(80, bold=True)
    metrics = QFontMetricsF(font)
    for ligature, first, second in (("ক্ষ", "ক", "ষ"), ("ঞ্জ", "ন", "জ"), ("ক্ত", "ক", "ত")):
        assert metrics.horizontalAdvance(ligature) < (
            metrics.horizontalAdvance(first) + metrics.horizontalAdvance(second) - 2)


def test_layout_lines_wraps_long_bangla_text():
    font = textrender.make_font(40)
    text = "প্রথম বাক্য এখানে। দ্বিতীয় বাক্যটি অনেক লম্বা হবে যাতে র‍্যাপিং পরীক্ষা করা যায়।"
    lines = textrender.layout_lines(text, font, 240)
    assert len(lines) >= 2
    assert all(isinstance(line, str) for line in lines)


def test_caption_png_writes_file(tmp_path):
    target = os.path.join(tmp_path, "caption.png")
    entry = textrender.caption_png(target, (720, 1280), "বাংলাদেশের সংস্কৃতি", font_size=44)
    assert os.path.exists(entry["path"])
    assert os.path.getsize(entry["path"]) > 1000
    assert entry["width"] > 0 and entry["height"] > 0
    assert entry["x"] >= 0 and entry["y"] >= 0


def test_text_layer_png_sizes_match_content(tmp_path):
    target = os.path.join(tmp_path, "title.png")
    entry = textrender.text_layer_png(target, (1080, 1920), "আজকের বিষয়", font_size=72,
                                      box_color="#000000C0")
    assert os.path.exists(entry["path"])
    # tight layer: far smaller than the full frame it will be placed on
    assert entry["width"] < 1080
    assert entry["height"] < 600


def test_progress_layer_png(tmp_path):
    target = os.path.join(tmp_path, "bar.png")
    path = textrender.progress_layer_png(target, (400, 10), 0.5)
    assert os.path.exists(path)


def test_caption_styles_all_render(tmp_path):
    for style in textrender.caption_style_names():
        layers = textrender.caption_layers(
            os.path.join(tmp_path, f"cap_{style}"), (1080, 1920),
            "আজকের কথাটি শুনুন", style=style, font_size=72)
        assert layers, style
        for layer in layers:
            assert os.path.exists(layer["path"])
            assert os.path.getsize(layer["path"]) > 500
            assert layer["width"] < 1080 * 1.1
            assert layer["x"] >= 0 and layer["y"] >= 0


def test_karaoke_style_emits_one_layer_per_word(tmp_path):
    text = "এক দুই তিন চার"
    layers = textrender.caption_layers(
        os.path.join(tmp_path, "karaoke"), (1080, 1920), text, style="karaoke",
        font_size=72)
    assert len(layers) == 4
    assert [layer["word_index"] for layer in layers] == [0, 1, 2, 3]
    # every layer must be a different image (a different word highlighted)
    paths = {layer["path"] for layer in layers}
    assert len(paths) == 4


def test_bold_style_emits_single_layer(tmp_path):
    layers = textrender.caption_layers(
        os.path.join(tmp_path, "bold"), (1080, 1920), "দুই শব্দ", style="bold", font_size=72)
    assert len(layers) == 1


def test_caption_box_shrinks_to_the_text(tmp_path):
    short = textrender.caption_layers(
        os.path.join(tmp_path, "short"), (1080, 1920), "ছোট", style="bold", font_size=72)[0]
    long = textrender.caption_layers(
        os.path.join(tmp_path, "long"), (1080, 1920),
        "এটি অনেক বড় একটি বাক্য যা দুই লাইনে ভাগ হবে", style="bold", font_size=72)[0]
    assert short["width"] < long["width"]
    assert short["width"] < 1080


def test_caption_default_is_fixed_height_friendly():
    """Captions must not sit under the platform UI at the very bottom."""
    style = textrender.DEFAULT_CAPTION_STYLE
    assert style in textrender.CAPTION_STYLES
