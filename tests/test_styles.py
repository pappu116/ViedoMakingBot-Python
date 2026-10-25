"""Video style consistency: presets, prompt hints and visual-source rules."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import render as render_lib
from core import script as script_lib


def test_every_style_has_a_prompt_hint():
    """A style without an image-prompt hint would silently produce unrelated visuals."""
    missing = [name for name in render_lib.STYLE_PRESETS
               if name not in script_lib.STYLE_VISUALS]
    assert not missing, f"prompt hint নেই: {missing}"


def test_every_style_has_a_label_and_swatch():
    for name, preset in render_lib.STYLE_PRESETS.items():
        assert preset.get("label_bn"), name
        assert preset.get("label_en"), name
        assert str(preset.get("swatch", "")).startswith("#"), name
        assert preset.get("accent"), name


def test_illustrated_styles_are_flagged():
    for name in ("anime", "cartoon2d", "whiteboard", "sketch", "puppet", "slide"):
        assert render_lib.style_is_illustrated(name), name
    for name in ("cinematic", "dramatic", "educational", "vibrant", "realistic"):
        assert not render_lib.style_is_illustrated(name), name


def test_illustrated_plan_never_uses_real_footage(tmp_path):
    script = {
        "title": "টেস্ট", "hook": "শুরু", "body": "একটি বাক্য।",
        "scenes": [{"text": "নদী আর নৌকা।", "image_prompt": "river boat, anime style"}],
        "cta": "সাবস্ক্রাইব", "lang": "bn", "topic": "river",
    }
    plan = render_lib.build_plan(
        script, {"duration": 4.0, "words": []},
        {"aspect": "mobile", "style": "anime", "images": True, "stock_video": True,
         "allow_network": False, "image_source": "auto", "subtitles": False,
         "progress_bar": False, "duration": 4},
        work_dir=str(tmp_path / "work"))
    kinds = {shot.get("background_kind") for shot in plan["shots"]}
    assert "video" not in kinds, "অ্যানিমেশন স্টাইলে আসল ভিডিও ঢোকা যাবে না"
    for shot in plan["shots"]:
        assert os.path.exists(shot["background"])


def test_photographic_style_allows_stock(tmp_path):
    script = {
        "title": "টেস্ট", "hook": "শুরু", "body": "একটি বাক্য।",
        "scenes": [{"text": "নদী আর নৌকা।", "image_prompt": "river boat"}],
        "cta": "সাবস্ক্রাইব", "lang": "bn", "topic": "river",
    }
    plan = render_lib.build_plan(
        script, {"duration": 4.0, "words": []},
        {"aspect": "mobile", "style": "cinematic", "images": True, "stock_video": True,
         "allow_network": False, "image_source": "auto", "subtitles": False,
         "progress_bar": False, "duration": 4},
        work_dir=str(tmp_path / "work"))
    assert plan["shots"]
    for shot in plan["shots"]:
        assert os.path.exists(shot["background"])


def test_grading_actually_changes_the_frame(tmp_path):
    """Each style must produce a visibly different look from the same source."""
    from PIL import Image, ImageStat

    source = Image.new("RGB", (200, 200), (120, 120, 120))
    means = {}
    for name, preset in render_lib.STYLE_PRESETS.items():
        graded = render_lib.grade_image(source, preset, 200, 200, seed=1)
        means[name] = ImageStat.Stat(graded).mean
    unique = {tuple(round(value) for value in mean) for mean in means.values()}
    assert len(unique) >= len(render_lib.STYLE_PRESETS) - 1, "স্টাইলগুলো একই রকম দেখাচ্ছে"


def test_caption_style_is_independent_of_video_style():
    """Caption look is chosen separately, so every video style works with every caption."""
    from core import textrender
    for caption_style in textrender.CAPTION_STYLES:
        assert caption_style in textrender.CAPTION_STYLES
    assert render_lib.DEFAULT_OPTS["caption_style"] in textrender.CAPTION_STYLES


def test_apply_style_rewrites_every_prompt():
    """Picking a new style must change the image prompts, not just a settings field."""
    script = script_lib.from_own_text("নদী আর নৌকা আমাদের প্রাণ।", title="টেস্ট",
                                      lang="bn", style="cinematic")
    assert "cinematic" in script["scenes"][0]["image_prompt"]

    updated = script_lib.apply_style(script, "anime")
    assert updated["style"] == "anime"
    assert updated["scenes"]
    for scene in updated["scenes"]:
        assert "anime" in scene["image_prompt"].lower()
        assert "cinematic" not in scene["image_prompt"].lower()
        assert scene.get("keywords"), "কীওয়ার্ড হারিয়ে যাওয়া যাবে না"
        # the original script must stay untouched
        assert scene is not script["scenes"][updated["scenes"].index(scene)]


def test_apply_style_is_safe_for_unknown_styles():
    script = script_lib.from_own_text("একটি বাক্য।", title="টেস্ট", lang="bn")
    updated = script_lib.apply_style(script, "does-not-exist")
    assert updated["style"] == "does-not-exist"
    assert updated["scenes"][0]["image_prompt"].strip()


def test_every_illustrated_style_has_a_fallback_palette():
    from core import images as image_lib
    for style in render_lib.ILLUSTRATED_STYLES:
        assert image_lib.style_palette(style) is not None, style


def test_illustrated_prompt_forbids_photorealism():
    for style in ("anime", "cartoon2d"):
        prompt = script_lib.STYLE_VISUALS[style].lower()
        assert "no photorealism" in prompt, style


def test_style_hint_comes_first_in_the_prompt():
    """Image models weight the beginning of a prompt more, so the style must lead."""
    prompt = script_lib.make_image_prompt("নদী আর নৌকা।", "", "anime")
    assert prompt.lower().startswith("anime")


def test_tutorial_style_is_available():
    assert "tutorial" in render_lib.STYLE_PRESETS
    assert "tutorial" in script_lib.STYLE_VISUALS
    assert render_lib.STYLE_PRESETS["tutorial"]["label_bn"]
    # a tutorial is filmed, not illustrated, so real footage is allowed
    assert not render_lib.style_is_illustrated("tutorial")


def test_whiteboard_and_sketch_are_illustrated():
    for style in ("whiteboard", "sketch"):
        assert style in render_lib.STYLE_PRESETS
        assert style in script_lib.STYLE_VISUALS
        assert render_lib.style_is_illustrated(style)


def test_every_motion_preset_returns_valid_params():
    import random
    rng = random.Random(7)
    for motion in render_lib.motion_names():
        params = render_lib._kenburns_params(0, True, rng, motion)
        assert set(params) == {"zoom_from", "zoom_to", "pan_from", "pan_to"}, motion
        assert params["zoom_from"] >= 1.0, motion
        assert params["zoom_to"] >= 1.0, motion


def test_zoom_in_and_zoom_out_have_opposite_direction():
    import random
    zoom_in = render_lib._kenburns_params(0, True, random.Random(3), "zoom_in")
    zoom_out = render_lib._kenburns_params(0, True, random.Random(3), "zoom_out")
    assert zoom_in["zoom_to"] > zoom_in["zoom_from"]
    assert zoom_out["zoom_from"] > zoom_out["zoom_to"]


def test_static_motion_has_no_movement():
    import random
    params = render_lib._kenburns_params(2, True, random.Random(3), "none")
    assert params["zoom_from"] == params["zoom_to"] == 1.0
    assert params["pan_from"] == params["pan_to"] == (0.0, 0.0)


def test_pan_motion_moves_sideways():
    import random
    params = render_lib._kenburns_params(0, True, random.Random(3), "pan")
    assert params["pan_from"][0] != params["pan_to"][0]
    assert params["zoom_from"] == params["zoom_to"]


def test_plan_records_the_chosen_motion(tmp_path):
    script = {
        "title": "টেস্ট", "hook": "শুরু", "body": "একটি বাক্য।",
        "scenes": [{"text": "নদী।", "image_prompt": "river"}],
        "cta": "সাবস্ক্রাইব", "lang": "bn", "topic": "river",
    }
    for motion in ("zoom_in", "zoom_out", "none"):
        plan = render_lib.build_plan(
            script, {"duration": 3.0, "words": []},
            {"aspect": "mobile", "style": "cinematic", "images": False,
             "image_source": "none", "subtitles": False, "progress_bar": False,
             "duration": 3, "motion": motion},
            work_dir=str(tmp_path / f"work_{motion}"))
        assert plan["shots"]
        for shot in plan["shots"]:
            assert shot["motion"] == motion
