"""Tools: one-click setup, environment tests and folders."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from ui import widgets


class ToolsPage(QWidget):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(widgets.label("টুলস", "h1"))
        outer.addWidget(widgets.label(
            "প্রথমবার সেটআপ, পরিবেশ পরীক্ষা আর ফোল্ডার খোলার সব কাজ এক জায়গায়।", "muted"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        setup_card = widgets.Card(title="প্রথমবার সেটআপ", icon_name="tools",
                                  subtitle="একবার চালালেই হবে")
        grid = QGridLayout()
        grid.setSpacing(10)
        items = [
            ("বাংলা ফন্ট নামান", "caption-frank", "download", self.on_fonts,
             "ভিডিওর বাংলা লেখা নিখুঁত করতে"),
            ("ব্রাউজার ইনস্টল", "chromium", "globe", self.on_browser_install,
             "YouTube/Facebook অটোমেশনের জন্য (১৫০ MB)"),
            ("ব্রাউজার যাচাই", "verify", "check", self.on_browser_verify,
             "আপলোডের আগে একবার পরীক্ষা করুন"),
            ("মিউজিক প্যাক তৈরি", "music-pack", "music", self.on_music,
             "৫টি ফ্রি ট্র্যাক তৈরি হবে"),
        ]
        for index, (title, _key, icon_name, handler, hint) in enumerate(items):
            tile = widgets.OptionTile(title, hint, icon_name=icon_name, compact=True)
            tile.clicked.connect(handler)
            grid.addWidget(tile, index // 2, index % 2)
        setup_card.add_layout(grid)
        left.addWidget(setup_card)

        test_card = widgets.Card(title="পরীক্ষা", icon_name="sparkles")
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(widgets.button("ভয়েস টেস্ট", "ghost", "mic", on_click=self.on_tts_test))
        row.addWidget(widgets.button("ছবি সোর্স টেস্ট", "ghost", "image",
                                     on_click=self.on_image_test))
        row.addWidget(widgets.button("ভিডিও ইঞ্জিন টেস্ট", "ghost", "film",
                                     on_click=self.on_engine_test))
        row.addWidget(widgets.button("বাংলা লেখা টেস্ট", "ghost", "content",
                                     on_click=self.on_text_test))
        row.addStretch(1)
        test_card.add_layout(row)
        left.addWidget(test_card)

        folder_card = widgets.Card(title="ফোল্ডার", icon_name="folder_open")
        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)
        for text, target in (("আউটপুট ভিডিও", "outputs"), ("প্রোফাইল", "profiles"),
                             ("ডেটা ও ক্যাশ", "data"), ("লগ", "logs"), ("ফন্ট", "fonts")):
            folder_row.addWidget(widgets.button(text, "ghost", "folder_open",
                                                on_click=lambda t=target: self.open_folder(t)))
        folder_row.addStretch(1)
        folder_card.add_layout(folder_row)
        left.addWidget(folder_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        info_card = widgets.Card(title="সিস্টেম তথ্য", icon_name="info")
        self.info_label = widgets.label("", "muted", wrap=True)
        info_card.add(self.info_label)
        info_card.add(widgets.button("আবার দেখুন", "ghost", "refresh", on_click=self.refresh_info))
        right.addWidget(info_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        self.refresh_info()

    # -------------------------------------------------------------- helpers
    def refresh_info(self):
        import platform
        lines = [f"Python: {platform.python_version()} ({sys.executable})"]
        for module_name, label in (("PySide6", "PySide6"), ("moviepy", "moviepy"),
                                   ("PIL", "Pillow"), ("edge_tts", "edge-tts"),
                                   ("playwright", "playwright"), ("numpy", "numpy")):
            try:
                module = __import__(module_name)
                lines.append(f"{label}: {getattr(module, '__version__', '?')}")
            except Exception:
                lines.append(f"{label}: নেই")
        try:
            import imageio_ffmpeg
            lines.append("ffmpeg: " + imageio_ffmpeg.get_ffmpeg_exe())
        except Exception:
            lines.append("ffmpeg: নেই")
        from tools import playwright_install
        builds = playwright_install.installed_builds()
        lines.append("Chromium: " + (", ".join(builds) if builds else "ইনস্টল করা নেই"))
        from core import textrender
        lines.append("ফন্ট: " + ", ".join(textrender.font_summary()["families"][:3]))
        lines.append(f"CPU: {os.cpu_count()} কোর")
        self.info_label.setText("\n".join(lines))

    def open_folder(self, target):
        from paths import (data_dir, fonts_dir, logs_dir, output_dir, outputs_dir, profiles_dir,
                           user_fonts_dir, user_music_dir)
        mapping = {"outputs": outputs_dir(), "output": output_dir(), "profiles": profiles_dir(),
                   "data": data_dir(), "logs": logs_dir(), "fonts": user_fonts_dir(),
                   "assets": fonts_dir(), "music": user_music_dir()}
        _open_path(mapping.get(target, data_dir()))

    # --------------------------------------------------------------- actions
    def on_fonts(self):
        studio = self.studio

        def work(progress, log, cancel):
            from tools import fetch_fonts
            progress(0.2, "ফন্ট নামানো হচ্ছে…")
            result = fetch_fonts.install(force=False, log=log)
            from core import textrender
            textrender._families = []
            progress(1.0, "ফন্ট ধাপ শেষ")
            return {"kind": "fonts", "result": result}

        studio.submit("বাংলা ফন্ট", work)

    def on_browser_install(self):
        studio = self.studio

        def work(progress, log, cancel):
            from tools import playwright_install
            progress(0.1, "ব্রাউজার যাচাই…")
            result = playwright_install.install(log=log, progress=lambda m: progress(0.4, m))
            progress(1.0, "ব্রাউজার ধাপ শেষ")
            return {"kind": "browser", "result": result}

        studio.submit("ব্রাউজার ইনস্টল", work)

    def on_browser_verify(self):
        studio = self.studio

        def work(progress, log, cancel):
            from tools import playwright_install
            progress(0.3, "ব্রাউজার চালু করে দেখা হচ্ছে…")
            result = playwright_install.verify(log=log)
            progress(1.0, "যাচাই শেষ")
            return {"kind": "browser_verify", "result": result}

        studio.submit("ব্রাউজার যাচাই", work)

    def on_music(self):
        studio = self.studio

        def work(progress, log, cancel):
            from core import music
            progress(0.2, "মিউজিক তৈরি হচ্ছে…")
            music.ensure_builtin(force=True, progress=lambda m: log(m, "dim"))
            progress(1.0, "মিউজিক প্রস্তুত")
            return {"kind": "music_ready"}

        studio.submit("মিউজিক প্যাক", work)

    def on_tts_test(self):
        studio = self.studio
        voice = studio.get("voice") or {}

        def work(progress, log, cancel):
            from core import tts
            progress(0.3, "ভয়েস তৈরি হচ্ছে…")
            result = tts.preview("আজকের দিনটি সুন্দর — বাংলা ভয়েস ঠিক আছে।",
                                 lang=voice.get("lang", "bn"), gender=voice.get("gender", "female"),
                                 accent=voice.get("accent", "bd"),
                                 voice_id=voice.get("voice") or None, engine="auto")
            log(f"ইঞ্জিন: {result.get('engine')} · {result.get('duration', 0):.1f} সেকেন্ড", "ok")
            progress(1.0, "ভয়েস তৈরি")
            return {"kind": "voice_preview", "audio": result}

        studio.submit("ভয়েস টেস্ট", work)

    def on_image_test(self):
        studio = self.studio

        def work(progress, log, cancel):
            from core import images
            progress(0.1, "AI ছবি পরীক্ষা…")
            path, note = images.fetch_pollinations("green paddy field sunrise, vertical", 720, 1280)
            log(f"AI (Pollinations): {note}" + (f" → {os.path.basename(path)}" if path else ""),
                "ok" if path else "warn")
            progress(0.4, "স্টক ছবি পরীক্ষা…")
            path, note = images.fetch_wikimedia("paddy field village", 720, 1280)
            log(f"স্টক (Wikimedia): {note}" + (f" → {os.path.basename(path)}" if path else ""),
                "ok" if path else "warn")
            progress(0.7, "র‍্যান্ডম ছবি পরীক্ষা…")
            path, note = images.fetch_picsum("test", 720, 1280, index=1)
            log(f"র‍্যান্ডম (Picsum): {note}" + (f" → {os.path.basename(path)}" if path else ""),
                "ok" if path else "warn")
            progress(1.0, "ছবি পরীক্ষা শেষ")
            return {"kind": "image_test"}

        studio.submit("ছবি সোর্স টেস্ট", work)

    def on_engine_test(self):
        studio = self.studio

        def work(progress, log, cancel):
            from core import music, textrender
            from paths import cache_dir
            progress(0.2, "মিউজিক লাইব্রেরি যাচাই…")
            tracks = music.library()
            log(f"মিউজিক ট্র্যাক: {len(tracks)}", "ok" if tracks else "warn")
            progress(0.5, "টেক্সট রেন্ডার যাচাই…")
            textrender.caption_png(os.path.join(cache_dir(), "_engine_test.png"),
                                   (640, 360), "বাংলা লেখা পরীক্ষা", font_size=34)
            log("টেক্সট রেন্ডার ঠিক আছে", "ok")
            progress(1.0, "ভিডিও ইঞ্জিন ঠিক আছে")
            return {"kind": "engine_test"}

        studio.submit("ভিডিও ইঞ্জিন টেস্ট", work)

    def on_text_test(self):
        studio = self.studio

        def work(progress, log, cancel):
            from core import textrender
            info = textrender.font_summary()
            log("ব্যবহৃত ফন্ট: " + ", ".join(info["families"]), "ok")
            if info["bundled"]:
                log("বান্ডল করা ফন্ট: " + ", ".join(info["bundled"]), "dim")
            else:
                log("বান্ডল করা বাংলা ফন্ট নেই — সিস্টেম ফন্ট ব্যবহার হচ্ছে", "warn")
            progress(0.5, "যুক্তাক্ষর যাচাই…")
            from PySide6.QtGui import QFontMetricsF
            font = textrender.make_font(80, bold=True)
            metrics = QFontMetricsF(font)
            shaped = metrics.horizontalAdvance("ক্ষ") < (
                metrics.horizontalAdvance("ক") + metrics.horizontalAdvance("ষ") - 2)
            log("যুক্তাক্ষর রেন্ডারিং: " + ("ঠিক আছে" if shaped else "সমস্যা আছে"), "ok" if shaped else "error")
            progress(1.0, "লেখা পরীক্ষা শেষ")
            return {"kind": "text_test"}

        studio.submit("বাংলা লেখা টেস্ট", work)


def _open_path(path):
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
