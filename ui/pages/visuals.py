"""Step 2 — aspect, style, duration and the visual toggles."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from core import render as render_lib
from core import script as script_lib
from ui import widgets
from ui.components import wizard

ASPECTS = [
    ("mobile", "Mobile (9:16)", "শর্টস, রিলস, টিকটক", "জনপ্রিয়"),
    ("landscape", "YouTube (16:9)", "সাধারণ লম্বা ভিডিও", ""),
    ("square", "Square (1:1)", "ফিড পোস্ট", ""),
]

DURATIONS = [
    ("৩০ সেকেন্ড", 30), ("৪৫ সেকেন্ড", 45), ("৬০ সেকেন্ড", 60),
    ("৯০ সেকেন্ড", 90), ("২ মিনিট", 120), ("৩ মিনিট", 180),
]

CORE_STYLES = ["cinematic", "dramatic", "educational", "vibrant"]


class VisualsPage(QWidget):
    step_index = 1

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.aspect_tiles = {}
        self.style_tiles = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "ভিডিও সেটিংস ও স্টাইল",
            "ফ্রেম, স্টাইল আর দৈর্ঘ্য ঠিক করুন — পরিবর্তন সাথে সাথেই সেভ হয়।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        # ------------------------------------------------------------ aspect
        aspect_card = widgets.Card(title="ভিডিওর অনুপাত", icon_name="film",
                                   right_widget=widgets.label("জনপ্রিয়", "chipPop"))
        grid = QGridLayout()
        grid.setSpacing(10)
        for index, (key, title, subtitle, badge) in enumerate(ASPECTS):
            tile = widgets.OptionTile(title, subtitle, icon_name="video", badge=badge)
            tile.clicked.connect(lambda k=key: self.set_aspect(k))
            grid.addWidget(tile, 0, index)
            self.aspect_tiles[key] = tile
        aspect_card.add_layout(grid)
        left.addWidget(aspect_card)

        # ------------------------------------------------------------- style
        style_card = widgets.Card(title="ভিডিওর স্টাইল", icon_name="wand",
                                  right_widget=widgets.label("জনপ্রিয়", "chipPop"))
        style_grid = QGridLayout()
        style_grid.setSpacing(10)
        for index, key in enumerate(render_lib.STYLE_PRESETS.keys()):
            preset = render_lib.STYLE_PRESETS[key]
            tile = widgets.StyleTile(key, preset["label_bn"], preset["swatch"])
            tile.clicked.connect(lambda k=key: self.set_style(k))
            style_grid.addWidget(tile, index // 4, index % 4)
            self.style_tiles[key] = tile
        style_card.add_layout(style_grid)
        left.addWidget(style_card)

        # ---------------------------------------------------------- duration
        detail_card = widgets.Card(title="দৈর্ঘ্য, গতি ও মুভমেন্ট", icon_name="clock")
        self.duration_combo = QComboBox()
        for text, seconds in DURATIONS:
            self.duration_combo.addItem(text, seconds)
        self.fps_combo = QComboBox()
        for text, value in (("24 fps (সাধারণ)", 24), ("30 fps (স্মুথ)", 30)):
            self.fps_combo.addItem(text, value)
        self.motion_combo = QComboBox()
        for key in render_lib.motion_names():
            self.motion_combo.addItem(render_lib.motion_label(key), key)
        detail_card.add(widgets.field_row("ভিডিওর দৈর্ঘ্য", self.duration_combo,
                                          "ভয়েসের দৈর্ঘ্য বেশি হলে সেটাই ধরা হবে"))
        detail_card.add(widgets.field_row("ফ্রেম রেট", self.fps_combo, ""))
        detail_card.add(widgets.field_row(
            "মুভমেন্ট", self.motion_combo,
            "Zoom-In / Zoom-Out / Ken Burns / Pan — ছবি ও ক্লিপ দুটোতেই কাজ করে"))
        self.duration_combo.currentIndexChanged.connect(self._save)
        self.fps_combo.currentIndexChanged.connect(self._save)
        self.motion_combo.currentIndexChanged.connect(self._save)
        left.addWidget(detail_card)
        left.addStretch(1)

        # ------------------------------------------------------------ column
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)

        preview_card = widgets.Card(title="প্রিভিউ", icon_name="eye",
                                    right_widget=widgets.label("9:16", "chip"))
        self.phone = widgets.PhonePreview(width=240)
        preview_card.add(self.phone)
        preview_card.add(widgets.button("প্রথম দৃশ্যের প্রিভিউ দেখুন", "ghost", "image",
                                        on_click=self.on_preview))
        right.addWidget(preview_card)

        toggle_card = widgets.Card(title="ভিডিও টগল", icon_name="layers")
        toggle_card.add(widgets.switch_row(
            "আসল ভিডিও ফুটেজ (B-roll)", "Wikimedia থেকে ফ্রি ক্লিপ — অনেক বেশি রিয়ালিস্টিক",
            checked=True, on_change=lambda v: self._toggle("stock_video", v)))
        toggle_card.add(widgets.switch_row(
            "AI ছবি ব্যবহার করুন", "প্রতিটি দৃশ্যের জন্য ইন্টারনেট থেকে ছবি (ফ্রি)",
            checked=True, on_change=lambda v: self._toggle("images", v)))
        toggle_card.add(widgets.switch_row(
            "মুভমেন্ট চালু", "বন্ধ করলে সব দৃশ্য স্থির থাকবে (ধরন নিচে বাছুন)",
            checked=True, on_change=lambda v: self._toggle("kenburns", v)))
        toggle_card.add(widgets.switch_row(
            "প্রগ্রেস বার", "ভিডিওর নিচে অগ্রগতি বার",
            checked=True, on_change=lambda v: self._toggle("progress_bar", v)))
        self.watermark_edit = QLineEdit()
        self.watermark_edit.setPlaceholderText("@yourchannel")
        self.watermark_edit.editingFinished.connect(self._save)
        toggle_card.add(widgets.field_row("ওয়াটারমার্ক", self.watermark_edit,
                                          "খালি রাখলে কিছু দেখাবে না"))
        toggle_card.add(widgets.switch_row(
            "সাবটাইটেল", "ভয়েসের সাথে সিঙ্ক করা ক্যাপশন",
            checked=True, on_change=lambda v: self._toggle("subtitles", v)))
        right.addWidget(toggle_card)
        right.addStretch(1)

        columns.addLayout(right, 2)
        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("script"),
                                         on_next=lambda: self.studio.navigate.emit("voice")))

        self._loading = True
        self._sync()
        self._loading = False
        self.studio.settings_changed.connect(lambda _cfg: self._sync())

    # -------------------------------------------------------------- helpers
    def _sync(self):
        if getattr(self, "_saving", False):
            return
        video = self.studio.get("video") or {}
        for key, tile in self.aspect_tiles.items():
            tile.set_selected(key == video.get("aspect", "mobile"))
        for key, tile in self.style_tiles.items():
            tile.set_selected(key == video.get("style", "cinematic"))
        target = int(video.get("duration") or 45)
        for index in range(self.duration_combo.count()):
            if self.duration_combo.itemData(index) == target:
                self.duration_combo.setCurrentIndex(index)
                break
        for index in range(self.fps_combo.count()):
            if self.fps_combo.itemData(index) == int(video.get("fps") or 24):
                self.fps_combo.setCurrentIndex(index)
                break
        for index in range(self.motion_combo.count()):
            if self.motion_combo.itemData(index) == (video.get("motion") or "auto"):
                self.motion_combo.setCurrentIndex(index)
                break
        self.watermark_edit.setText(video.get("watermark") or "")
        aspect = video.get("aspect", "mobile")
        if aspect == "landscape":
            self.phone.set_aspect(16, 9)
        elif aspect == "square":
            self.phone.set_aspect(1, 1)
        else:
            self.phone.set_aspect(9, 16)

    def _save(self):
        if self._loading or getattr(self, "_saving", False):
            return
        self._saving = True
        try:
            cfg = self.studio.settings
            video = cfg.setdefault("video", {})
            video["duration"] = self.duration_combo.currentData()
            video["fps"] = self.fps_combo.currentData()
            video["motion"] = self.motion_combo.currentData() or "auto"
            video["watermark"] = self.watermark_edit.text().strip()
            self.studio.save_settings()
        finally:
            self._saving = False

    def _toggle(self, key, value):
        self.studio.set_setting("video", key, bool(value))
        self.studio.log(f"{key} → {'চালু' if value else 'বন্ধ'}", "dim")
        if key == "images" and value:
            self.studio.log("ছবি চালু — ইন্টারনেট না থাকলে ব্যাকগ্রাউন্ড ব্যবহার হবে", "dim")

    def set_aspect(self, key):
        self.studio.set_setting("video", "aspect", key)
        for name, tile in self.aspect_tiles.items():
            tile.set_selected(name == key)
        self._sync()
        self.studio.log("অনুপাত: " + key, "dim")

    def set_style(self, key):
        self.studio.set_setting("video", "style", key)
        for name, tile in self.style_tiles.items():
            tile.set_selected(name == key)
        self.studio.log("স্টাইল: " + render_lib.style_label(key), "dim")
        if self.studio.script:
            # a style change must also rewrite the image prompts, otherwise an
            # "anime" video would still be filled with cinematic photos
            updated = script_lib.apply_style(self.studio.script, key)
            self.studio.set_script(updated)
            self.studio.log("ছবির প্রম্পট নতুন স্টাইল অনুযায়ী আপডেট হয়েছে", "dim")

    def on_preview(self):
        studio = self.studio
        if not studio.script:
            studio.log("আগে ধাপ ১-এ স্ক্রিপ্ট তৈরি করুন", "warn")
            return
        opts = studio.render_options()

        def work(progress, log, cancel):
            from core import pipeline
            progress(0.2, "প্রিভিউ ফ্রেম তৈরি হচ্ছে…")
            image = pipeline.render_preview_frame(studio.script, opts, index=0)
            progress(1.0, "প্রিভিউ প্রস্তুত")
            return {"kind": "preview", "image": image}

        studio.submit("প্রিভিউ", work)
