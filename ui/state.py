"""Shared UI state: current script, settings, jobs and cross-page signals."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal

from core import jobs as jobs_lib
from core import projects as projects_lib
from core import settings as settings_lib
from core import tts as tts_lib
from core import voices as voice_lib


class Studio(QObject):
    """One object every page talks to."""

    script_changed = Signal(dict)
    settings_changed = Signal(dict)
    project_changed = Signal(dict)
    render_done = Signal(dict)
    navigate = Signal(str)
    status = Signal(str)
    logged = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = settings_lib.load()
        self.script = {}
        self.project = None
        self.last_render = {}
        self.preview_audio = None
        self.preview_player = None
        self.queue = jobs_lib.JobQueue(self)
        self.queue.logged.connect(self.logged)
        self.queue.progressed.connect(self._on_progress)
        self.queue.finished.connect(self._on_finished)
        self.queue.failed.connect(self._on_failed)
        self.queue.started.connect(lambda name: self.status.emit(f"চলছে: {name}"))
        self._progress_ratio = 0.0

    # ------------------------------------------------------------- plumbing
    def log(self, message, level="info"):
        self.logged.emit(str(message), str(level))

    def _on_progress(self, ratio, message):
        self._progress_ratio = ratio
        if message:
            self.status.emit(message)

    def _on_finished(self, name, result):
        self.status.emit("প্রস্তুত")
        if result.get("kind") == "render":
            self.last_render = result
            self.render_done.emit(result)

    def _on_failed(self, name, message):
        self.status.emit("ত্রুটি: " + message)
        self.log(f"[{name}] {message}", "error")

    def progress_ratio(self):
        return self._progress_ratio

    def submit(self, name, fn, meta=None):
        if self.queue.busy() or self.queue.pending():
            self.log("একটি কাজ চলছে — কিউতে যোগ করা হলো: " + name, "warn")
        return self.queue.submit(name, fn, meta)

    # --------------------------------------------------------------- state
    def set_script(self, script, from_project=None):
        self.script = dict(script or {})
        self.script_changed.emit(self.script)
        if from_project:
            self.project = from_project
            self.project_changed.emit(from_project)

    def update_script(self, **fields):
        merged = dict(self.script or {})
        merged.update(fields)
        self.script = merged
        self.script_changed.emit(self.script)
        return merged

    def require_script(self):
        if not (self.script or {}).get("scenes"):
            raise RuntimeError("আগে ধাপ ১-এ স্ক্রিপ্ট তৈরি করুন")
        return self.script

    def save_settings(self):
        settings_lib.save(self.settings)
        self.settings_changed.emit(self.settings)

    def set_setting(self, section, key, value):
        self.settings.setdefault(section, {})
        self.settings[section][key] = value
        self.save_settings()

    def get(self, section, key=None, default=None):
        data = self.settings.get(section, {})
        if key is None:
            return data
        return data.get(key, default)

    # ------------------------------------------------------ render options
    def effective_language(self):
        """The script's own language always wins over the voice setting."""
        script_lang = ((self.script or {}).get("lang") or "").strip()
        if script_lang:
            return script_lang
        return ((self.get("voice") or {}).get("lang") or "bn")

    def render_options(self, extra=None):
        video = self.get("video") or {}
        voice = self.get("voice") or {}
        voice_lang = voice.get("lang", "bn")
        lang = self.effective_language()
        accent = voice.get("accent", "bd")
        voice_id = voice.get("voice") or ""
        if lang != voice_lang:
            # never reuse a voice from another language — it would read the script
            # with the wrong phonetics
            voice_id = ""
            valid = voice_lib.accents_for(lang)
            if valid and accent not in valid:
                accent = valid[0]
        opts = {
            "aspect": video.get("aspect", "mobile"),
            "style": video.get("style", "cinematic"),
            "caption_style": video.get("caption_style", "bold"),
            "duration": int(video.get("duration") or 45),
            "fps": int(video.get("fps") or 24),
            "music": bool(video.get("music", True)),
            "music_volume": float(video.get("music_volume", 0.18)),
            "subtitles": bool(video.get("subtitles", True)),
            "voiceover": bool(video.get("voiceover", True)),
            "ducking": bool(video.get("ducking", True)),
            "kenburns": bool(video.get("kenburns", True)),
            "motion": video.get("motion", "auto"),
            "progress_bar": bool(video.get("progress_bar", True)),
            "watermark": video.get("watermark") or "",
            "images": bool(video.get("images", True)),
            "stock_video": bool(video.get("stock_video", True)),
            "image_source": video.get("image_source", "auto"),
            "image_token": (self.get("ai") or {}).get("pollen_token") or "",
            "own_images_dir": video.get("own_images_dir") or "",
            "music_dir": (self.get("paths") or {}).get("music_dir") or "",
            "lang": lang,
            "gender": voice.get("gender", "female"),
            "accent": accent,
            "voice": voice_id,
            "rate": int(voice.get("rate") or 0),
            "pitch": int(voice.get("pitch") or 0),
            "voice_engine": voice.get("engine", "auto"),
        }
        if extra:
            opts.update(extra)
        return opts

    # ------------------------------------------------------------- helpers
    def voices_for_language(self, lang):
        return tts_lib.available_edge_voices(lang)

    def project_stats(self):
        return projects_lib.stats()
