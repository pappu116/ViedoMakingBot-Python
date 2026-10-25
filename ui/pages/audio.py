"""Step 4 — music, ducking and subtitles (with a real caption style preview)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from core import music as music_lib
from core import textrender
from ui import theme, widgets
from ui.components import wizard


class AudioPage(QWidget):
    step_index = 3

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self._loading = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "মিউজিক ও সাবটাইটেল",
            "ব্যাকগ্রাউন্ড মিউজিক, ডাকিং আর ক্যাপশনের স্টাইল ঠিক করুন।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        toggle_card = widgets.Card(title="অডিও টগল", icon_name="music")
        video = self.studio.get("video") or {}
        toggle_card.add(widgets.switch_row(
            "ভয়েসওভার", "স্ক্রিপ্ট পড়ে শোনাবে", checked=bool(video.get("voiceover", True)),
            on_change=lambda v: self._toggle("voiceover", v)))
        toggle_card.add(widgets.switch_row(
            "ব্যাকগ্রাউন্ড মিউজিক", "রয়্যালটি-ফ্রি মিউজিক", checked=bool(video.get("music", True)),
            on_change=lambda v: self._toggle("music", v)))
        toggle_card.add(widgets.switch_row(
            "ডাকিং", "কথা বলার সময় মিউজিক নরম হবে", checked=bool(video.get("ducking", True)),
            on_change=lambda v: self._toggle("ducking", v)))
        toggle_card.add(widgets.switch_row(
            "সাবটাইটেল", "ভয়েসের সাথে সিঙ্ক করা ক্যাপশন",
            checked=bool(video.get("subtitles", True)),
            on_change=lambda v: self._toggle("subtitles", v)))
        self.volume = widgets.SliderRow(
            "মিউজিক ভলিউম", 5, 60, int(float(video.get("music_volume", 0.18)) * 100), "%",
            on_change=self._on_volume, hint="২০% আশপাশে সবচেয়ে ভালো শোনায়")
        toggle_card.add(self.volume)
        left.addWidget(toggle_card)

        library_card = widgets.Card(title="মিউজিক লাইব্রেরি", icon_name="layers",
                                    subtitle="সব ট্র্যাক সম্পূর্ণ ফ্রি ও কপিরাইট-মুক্ত")
        self.music_list = QListWidget()
        self.music_list.setMinimumHeight(150)
        self.music_list.currentRowChanged.connect(self._on_track)
        library_card.add(self.music_list)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(widgets.button("লাইব্রেরি রিফ্রেশ", "ghost", "refresh",
                                     on_click=self.refresh_music))
        row.addWidget(widgets.button("নতুন ট্র্যাক তৈরি করুন", "ghost", "sparkles",
                                     on_click=self.generate_music))
        row.addStretch(1)
        library_card.add_layout(row)
        left.addWidget(library_card)
        left.addStretch(1)

        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        caption_card = widgets.Card(title="ক্যাপশন স্টাইল", icon_name="subtitles",
                                    subtitle="যেটা বাছবেন, ভিডিওতে ঠিক সেটাই বসবে")
        self.style_tiles = {}
        for key, preset in textrender.CAPTION_STYLES.items():
            hint = ("ভরাট আউটলাইন, খুব স্পষ্ট" if key == "bold" else
                    "বলার সময় শব্দটা জ্বলে ওঠে" if key == "karaoke" else
                    "সাদা বর্ণ, হলুদ হাইলাইট" if key == "yellow" else
                    "কালো বক্সের ভেতরে লেখা" if key == "box" else
                    "হালকা আউটলাইন")
            tile = widgets.OptionTile(preset["label_bn"], hint, icon_name="subtitles",
                                      compact=True)
            tile.clicked.connect(lambda k=key: self.set_caption_style(k))
            caption_card.add(tile)
            self.style_tiles[key] = tile

        self.caption_preview = widgets.label("", "muted")
        self.caption_preview.setAlignment(Qt.AlignCenter)
        self.caption_preview.setMinimumHeight(230)
        self.caption_preview.setStyleSheet(
            f"background-color: #0A0F1C; border: 1px solid {theme.BORDER_SOFT}; border-radius: 12px;")
        caption_card.add(widgets.label("প্রিভিউ", "dim"))
        caption_card.add(self.caption_preview)
        right.addWidget(caption_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("voice"),
                                         on_next=lambda: self.studio.navigate.emit("preview")))

        self.refresh_music()
        self.refresh_caption()
        self._loading = False
        self.studio.settings_changed.connect(lambda _cfg: self.refresh_caption())

    # -------------------------------------------------------------- helpers
    def _toggle(self, key, value):
        self.studio.set_setting("video", key, bool(value))
        self.studio.log(f"{key} → {'চালু' if value else 'বন্ধ'}", "dim")

    def _on_volume(self, value):
        if self._loading:
            return
        self.studio.set_setting("video", "music_volume", round(value / 100.0, 3))

    def _on_track(self, row):
        if row < 0:
            return
        item = self.music_list.item(row)
        if not item:
            return
        path = item.data(Qt.UserRole)
        self.studio.set_setting("paths", "music_dir", os.path.dirname(path))
        self.studio.log("মিউজিক ট্র্যাক: " + os.path.basename(path), "dim")

    def refresh_music(self):
        self.music_list.clear()
        try:
            tracks = music_lib.tracks()
        except Exception as exc:
            self.studio.log(f"মিউজিক লোড হয়নি: {exc}", "error")
            tracks = []
        for track in tracks:
            name = ("🎵 " if track["builtin"] else "📁 ") + track["name"]
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, track["path"])
            self.music_list.addItem(item)
        if not tracks:
            self.studio.log("কোনো মিউজিক নেই — 'নতুন ট্র্যাক তৈরি করুন' চাপুন", "warn")

    def generate_music(self):
        studio = self.studio

        def work(progress, log, cancel):
            progress(0.1, "নতুন মিউজিক তৈরি হচ্ছে…")
            music_lib.ensure_builtin(force=True, progress=lambda msg: log(msg, "dim"))
            progress(1.0, "মিউজিক লাইব্রেরি তৈরি")
            return {"kind": "music_ready"}

        studio.submit("মিউজিক তৈরি", work)

    def refresh_caption(self):
        style = (self.studio.get("video") or {}).get("caption_style", "bold")
        if style not in textrender.CAPTION_STYLES:
            style = "bold"
        for key, tile in self.style_tiles.items():
            tile.set_selected(key == style)

        sample = "এভাবেই সাবটাইটেল দেখাবে"
        if (self.studio.get("voice") or {}).get("lang") == "en":
            sample = "This is how your captions look"
        try:
            from PIL import Image
            from core import images as image_lib

            canvas_w, canvas_h = 420, 300
            background = image_lib.procedural_background(canvas_w, canvas_h, seed=11)
            layers = textrender.caption_layers(
                _preview_path(), (canvas_w, canvas_h), sample, style=style,
                font_size=30, margin_ratio=0.08)
            layer = layers[0]
            canvas = background.copy()
            patch = Image.open(layer["path"]).convert("RGBA")
            canvas.paste(patch, (layer["x"], layer["y"]), patch)
            canvas.save(_preview_png_path())

            from PySide6.QtGui import QPixmap
            pix = QPixmap(_preview_png_path())
            self.caption_preview.setPixmap(pix)
            self.caption_preview.setText("")
        except Exception as exc:
            self.caption_preview.setText(f"প্রিভিউ তৈরি হয়নি: {exc}")

    def set_caption_style(self, key):
        self.studio.set_setting("video", "caption_style", key)
        for name, tile in self.style_tiles.items():
            tile.set_selected(name == key)
        self.studio.log("ক্যাপশন স্টাইল: " + textrender.caption_style_label(key), "dim")
        self.refresh_caption()


def _preview_path():
    return os.path.join(_preview_dir(), "caption_preview")


def _preview_png_path():
    return os.path.join(_preview_dir(), "caption_preview_canvas.png")


def _preview_dir():
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "cache")
    os.makedirs(base, exist_ok=True)
    return base
