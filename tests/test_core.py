"""Path, settings, project store and pipeline unit tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths
from core import projects as projects_lib
from core import settings as settings_lib
from core import video as video_lib


def test_paths_are_inside_app():
    root = paths.app_dir()
    for value in (paths.output_dir(), paths.data_dir(), paths.profiles_dir(),
                  paths.logs_dir(), paths.cache_dir(), paths.fonts_dir()):
        assert value.startswith(root)


def test_ensure_dirs_creates_folders():
    paths.ensure_dirs()
    for folder in (paths.outputs_dir(), paths.images_cache_dir(), paths.tts_cache_dir(),
                   paths.thumb_dir(), paths.data_dir()):
        assert os.path.isdir(folder)


def test_settings_defaults_and_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_lib, "settings_path", lambda: str(tmp_path / "settings.json"))
    cfg = settings_lib.load()
    assert cfg["video"]["aspect"] == "mobile"
    assert cfg["voice"]["lang"] == "bn"
    cfg["video"]["duration"] = 99
    settings_lib.save(cfg)
    reloaded = settings_lib.load()
    assert reloaded["video"]["duration"] == 99
    assert reloaded["upload"]["visibility"] == "public"


def test_settings_deep_merge_keeps_missing_keys():
    merged = settings_lib._deep_merge(settings_lib.DEFAULTS, {"video": {"duration": 30}})
    assert merged["video"]["duration"] == 30
    assert merged["video"]["subtitles"] is True


def test_projects_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(projects_lib, "projects_path", lambda: str(tmp_path / "projects.json"))
    item = projects_lib.create(title="টেস্ট", idea="test", script={"title": "টেস্ট"})
    assert item["id"]
    listed = projects_lib.list_all()
    assert len(listed) == 1
    updated = projects_lib.update(item["id"], duration=42)
    assert updated["duration"] == 42
    assert projects_lib.get(item["id"])["duration"] == 42
    stats = projects_lib.stats()
    assert stats["projects"] == 1
    projects_lib.delete(item["id"])
    assert projects_lib.list_all() == []


def test_duck_envelope_lowers_under_voice():
    import numpy as np
    fps = 1000
    voice = np.zeros((fps, 2), dtype=np.float32)
    voice[200:600] = 0.4  # speaking segment
    envelope = video_lib._duck_envelope(voice, fps=fps, window=0.02, threshold=0.05)
    assert envelope[0] < 0.2          # before speech, little ducking
    assert envelope[400] > 0.6        # during speech, ducking engaged


def test_audio_track_without_voice_uses_music(tmp_path, monkeypatch):
    from core import music as music_lib
    monkeypatch.setattr(music_lib, "library", lambda user_dir=None: [])
    plan = {"duration": 1.0, "music_seed": "x"}
    track = video_lib.build_audio_track(plan, None, {"music": True, "music_volume": 0.2})
    assert track is None  # no library, no voice -> nothing to mix


def test_frame_composer_draws_progress_bar(tmp_path):
    from PIL import Image
    background = tmp_path / "bg.jpg"
    Image.new("RGB", (90, 160), (20, 30, 60)).save(background)
    plan = {
        "width": 90,
        "height": 160,
        "fps": 10,
        "duration": 1.0,
        "shots": [{
            "start": 0.0, "duration": 1.0, "background": str(background),
            "zoom_from": 1.0, "zoom_to": 1.05, "pan_from": (0, 0), "pan_to": (0, 0),
            "overlays": [],
        }],
        "progress_bar": {"frames": [], "height": 4, "color": "#7C3AED", "start": 0, "end": 1.0},
        "watermark": None,
    }
    composer = video_lib.FrameComposer(plan)
    frame = composer.frame(0.9)
    assert frame.shape == (160, 90, 3)
    assert frame.dtype.name == "uint8"
    # the last rows are the coloured progress track
    assert tuple(frame[157, 5]) != (0, 0, 0)


def test_frame_composer_applies_overlay(tmp_path):
    from PIL import Image
    background = tmp_path / "bg.jpg"
    Image.new("RGB", (60, 60), (0, 0, 0)).save(background)
    overlay = tmp_path / "ov.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(overlay)
    plan = {
        "width": 60, "height": 60, "fps": 10, "duration": 1.0,
        "shots": [{
            "start": 0.0, "duration": 1.0, "background": str(background),
            "zoom_from": 1.0, "zoom_to": 1.0, "pan_from": (0, 0), "pan_to": (0, 0),
            "overlays": [{"image": str(overlay), "x": 10, "y": 30, "kind": "caption",
                          "start": 0.0, "end": 1.0}],
        }],
        "progress_bar": None, "watermark": None,
    }
    composer = video_lib.FrameComposer(plan)
    frame = composer.frame(0.5)
    assert tuple(frame[35, 15]) == (255, 0, 0)
    assert tuple(frame[5, 5]) == (0, 0, 0)
