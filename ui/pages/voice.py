"""Step 3 — voice selection with a live listen button."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QHBoxLayout, QPushButton, QVBoxLayout,
                               QWidget)

from core import voices as voice_lib
from ui import theme, widgets
from ui.components import player, wizard

ENGINES = [
    ("auto", "স্বয়ংক্রিয় (edge → gTTS → অফলাইন)"),
    ("edge", "edge-tts (সেরা মান, ইন্টারনেট)"),
    ("gtts", "gTTS (ইন্টারনেট)"),
    ("pyttsx3", "অফলাইন (Windows কণ্ঠ)"),
]


class VoicePage(QWidget):
    step_index = 2

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self._loading = True
        self._saving = False
        self.voice_lang = "bn"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "ভয়েস নির্বাচন করুন",
            "ভাষা, লিঙ্গ আর অ্যাকসেন্ট বেছে নিন — এখানেই শুনে নিতে পারবেন।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        card = widgets.Card(title="ভয়েস", icon_name="mic")
        self.lang_group = QButtonGroup(self)
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        self.lang_buttons = {}
        for index, (code, title) in enumerate((("bn", "বাংলা"), ("en", "ইংরেজি"))):
            pill = QPushButton(title)
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            pill.setMinimumHeight(38)
            pill.clicked.connect(lambda _=False, c=code: self.set_lang(c))
            lang_row.addWidget(pill)
            self.lang_group.addButton(pill, index)
            self.lang_buttons[code] = pill
        lang_row.addStretch(1)
        card.add_layout(lang_row)

        self.gender_combo = QComboBox()
        self.accent_combo = QComboBox()
        pair = QHBoxLayout()
        pair.setSpacing(12)
        pair.addWidget(widgets.field_row("লিঙ্গ", self.gender_combo, "", width=90))
        pair.addWidget(widgets.field_row("অ্যাকসেন্ট", self.accent_combo, "", width=90))
        card.add_layout(pair)
        self.gender_combo.currentIndexChanged.connect(self._on_gender)
        self.accent_combo.currentIndexChanged.connect(self._on_accent)

        self.voice_combo = QComboBox()
        card.add(widgets.field_row("কণ্ঠ", self.voice_combo, "আসল কণ্ঠের নাম"))
        self.voice_combo.currentIndexChanged.connect(self._on_voice)

        self.rate_slider = widgets.SliderRow("বলার গতি", -40, 40, 0, "%", on_change=self._on_sliders)
        self.pitch_slider = widgets.SliderRow("পিচ", -30, 30, 0, " Hz", on_change=self._on_sliders)
        card.add(self.rate_slider)
        card.add(self.pitch_slider)

        self.engine_combo = QComboBox()
        for value, text in ENGINES:
            self.engine_combo.addItem(text, value)
        self.engine_combo.currentIndexChanged.connect(self._on_engine)
        card.add(widgets.field_row("ভয়েস ইঞ্জিন", self.engine_combo,
                                   "ইন্টারনেট না থাকলে অফলাইন কণ্ঠ ব্যবহার হবে"))

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(widgets.button("🔊 কণ্ঠ শুনুন", "primary", "play", on_click=self.on_listen))
        row.addWidget(widgets.button("অফলাইন কণ্ঠের তালিকা", "ghost", "download",
                                     on_click=self.on_list_offline))
        row.addStretch(1)
        card.add_layout(row)
        left.addWidget(card)

        self.audio_preview = player.AudioPreview()
        preview_card = widgets.Card(title="প্রিভিউ", icon_name="music")
        preview_card.add(self.audio_preview)
        left.addWidget(preview_card)
        left.addStretch(1)

        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        summary = widgets.Card(title="নির্বাচিত কণ্ঠ", icon_name="user")
        self.voice_label = widgets.label("—", "h2", wrap=True)
        self.voice_detail = widgets.label("", "muted", wrap=True)
        summary.add(self.voice_label)
        summary.add(self.voice_detail)
        right.addWidget(summary)

        tips = widgets.Card(title="টিপস", icon_name="info")
        tips.add(widgets.label(
            "• বাংলা ভয়েসের জন্য edge-tts সবচেয়ে ভালো শোনায় (ফ্রি, key লাগে না)।\n"
            "• ইন্টারনেট না থাকলে pyttsx3 অফলাইন কণ্ঠ ব্যবহার হবে।\n"
            "• gTTS-এ বাংলার জন্য বাংলাদেশ/ভারত অ্যাকসেন্ট বেছে নিতে পারেন।\n"
            "• গতি +১০% দিলে শর্টসে আরও প্রাণবন্ত লাগে।", "muted", wrap=True))
        right.addWidget(tips)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("visuals"),
                                         on_next=lambda: self.studio.navigate.emit("audio")))

        self._sync()
        self._loading = False
        self.studio.settings_changed.connect(lambda _cfg: self._sync())
        self.studio.script_changed.connect(self._follow_script_language)

    def _follow_script_language(self, script):
        """Keep the voice language in sync with whatever the script is written in."""
        lang = (script or {}).get("lang")
        if not lang or lang == self.voice_lang:
            return
        self.set_lang(lang)
        self.studio.log(
            "স্ক্রিপ্ট " + ("বাংলা" if lang == "bn" else "ইংরেজি") +
            " — ভয়েসও সেই ভাষায় সেট করা হলো", "ok")

    # -------------------------------------------------------------- helpers
    def _lang(self):
        return self.voice_lang

    def _sync(self):
        if getattr(self, "_saving", False):
            return
        self._loading = True
        voice = self.studio.get("voice") or {}
        self.voice_lang = voice.get("lang", "bn")
        for code, pill in self.lang_buttons.items():
            active = code == self.voice_lang
            pill.setStyleSheet(
                f"QPushButton {{ border-radius: 10px; padding: 8px 20px;"
                f" background-color: {theme.ACCENT_SOFT if active else 'transparent'};"
                f" border: 1px solid {theme.ACCENT_HOVER if active else theme.BORDER_SOFT};"
                f" color: {'#FFFFFF' if active else theme.MUTED};"
                f" font-weight: {'700' if active else '500'}; }}")
        self._fill_genders(voice.get("gender", "female"))
        self._fill_accents(voice.get("accent", "bd"))
        self._fill_voices(voice.get("voice") or "")
        for index in range(self.engine_combo.count()):
            if self.engine_combo.itemData(index) == voice.get("engine", "auto"):
                self.engine_combo.setCurrentIndex(index)
                break
        self.rate_slider.set_value(int(voice.get("rate") or 0))
        self.pitch_slider.set_value(int(voice.get("pitch") or 0))
        self._loading = False
        self._update_summary()

    def _fill_genders(self, selected):
        self.gender_combo.blockSignals(True)
        self.gender_combo.clear()
        for gender in voice_lib.genders_for(self.voice_lang):
            self.gender_combo.addItem(voice_lib.gender_label(gender), gender)
        index = max(0, self.gender_combo.findData(selected))
        self.gender_combo.setCurrentIndex(index)
        self.gender_combo.blockSignals(False)

    def _fill_accents(self, selected):
        self.accent_combo.blockSignals(True)
        self.accent_combo.clear()
        accents = voice_lib.accents_for(self.voice_lang)
        for accent in accents:
            self.accent_combo.addItem(voice_lib.accent_label(accent), accent)
        index = max(0, self.accent_combo.findData(selected))
        if index == -1:
            index = 0
        self.accent_combo.setCurrentIndex(index)
        self.accent_combo.blockSignals(False)

    def _fill_voices(self, selected):
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        self.voice_combo.addItem("স্বয়ংক্রিয় (শ্রেষ্ঠ মিল)", "")
        matches = voice_lib.list_for(
            self.voice_lang, self.gender_combo.currentData(), self.accent_combo.currentData())
        if not matches:
            matches = voice_lib.list_for(self.voice_lang)
        for voice in matches:
            self.voice_combo.addItem(voice["bn"], voice["id"])
        index = self.voice_combo.findData(selected)
        self.voice_combo.setCurrentIndex(max(0, index))
        self.voice_combo.blockSignals(False)

    def _update_summary(self):
        voice_id = self.voice_combo.currentData() or ""
        gender = self.gender_combo.currentData() or "female"
        accent = self.accent_combo.currentData() or "bd"
        resolved = voice_id or voice_lib.find(self.voice_lang, gender, accent)
        self.voice_label.setText(voice_lib.label(resolved) or resolved)
        engine = self.engine_combo.currentData()
        note = ""
        if engine == "pyttsx3":
            from core import tts as tts_lib
            if not tts_lib.offline_supports(self.voice_lang):
                note = ("\n⚠️ এই ভাষার অফলাইন ভয়েস Windows-এ নেই — অটো মোড ব্যবহার করুন "
                        "অথবা ইন্টারনেট চালু রাখুন।")
        self.voice_detail.setText(
            f"ভাষা: {voice_lib.lang_label(self.voice_lang)} · "
            f"লিঙ্গ: {voice_lib.gender_label(gender)} · "
            f"অ্যাকসেন্ট: {voice_lib.accent_label(accent)}\n"
            f"কণ্ঠ আইডি: {resolved}\n"
            f"গতি: {self.rate_slider.value():+d}% · পিচ: {self.pitch_slider.value():+d} Hz{note}")

    def _save(self):
        if self._loading or self._saving:
            return
        # Write every voice field in ONE go. Saving them one by one emitted
        # settings_changed each time, which rebuilt the combos mid-save and reset
        # the gender/accent the user had just picked.
        self._saving = True
        try:
            cfg = self.studio.settings
            voice = cfg.setdefault("voice", {})
            voice.update({
                "lang": self.voice_lang,
                "gender": self.gender_combo.currentData() or "female",
                "accent": self.accent_combo.currentData() or "bd",
                "voice": self.voice_combo.currentData() or "",
                "rate": int(self.rate_slider.value()),
                "pitch": int(self.pitch_slider.value()),
                "engine": self.engine_combo.currentData() or "auto",
            })
            self.studio.save_settings()
        finally:
            self._saving = False
        self._update_summary()

    # --------------------------------------------------------------- events
    def set_lang(self, code):
        self.voice_lang = code
        self._loading = True
        for name, pill in self.lang_buttons.items():
            active = name == code
            pill.setStyleSheet(
                f"QPushButton {{ border-radius: 10px; padding: 8px 20px;"
                f" background-color: {theme.ACCENT_SOFT if active else 'transparent'};"
                f" border: 1px solid {theme.ACCENT_HOVER if active else theme.BORDER_SOFT};"
                f" color: {'#FFFFFF' if active else theme.MUTED};"
                f" font-weight: {'700' if active else '500'}; }}")
        self._fill_genders("female")
        self._fill_accents("bd" if code == "bn" else "us")
        self._fill_voices("")
        self._loading = False
        self._save()

    def _on_gender(self):
        self._loading = True
        self._fill_accents(self.accent_combo.currentData())
        self._fill_voices("")
        self._loading = False
        self._save()

    def _on_accent(self):
        self._loading = True
        self._fill_voices("")
        self._loading = False
        self._save()

    def _on_voice(self):
        self._save()

    def _on_sliders(self, _value=None):
        self._save()

    def _on_engine(self):
        self._save()

    def on_listen(self):
        studio = self.studio
        text = ""
        if studio.script:
            text = (studio.script.get("hook") or "").strip()
            if not text:
                scenes = studio.script.get("scenes") or []
                text = scenes[0].get("text", "") if scenes else ""
        if not text:
            text = "আমি বাংলায় কথা বলছি।" if self.voice_lang == "bn" else "This is a voice preview."

        params = {
            "text": text[:160],
            "lang": self.voice_lang,
            "gender": self.gender_combo.currentData() or "female",
            "accent": self.accent_combo.currentData() or "bd",
            "voice_id": self.voice_combo.currentData() or None,
            "rate": self.rate_slider.value(),
            "pitch": self.pitch_slider.value(),
            "engine": self.engine_combo.currentData(),
        }

        def work(progress, log, cancel):
            from core import tts
            progress(0.3, "কণ্ঠ তৈরি হচ্ছে…")
            result = tts.preview(**params)
            progress(1.0, "তৈরি — এখনই শুনতে পারবেন")
            return {"kind": "voice_preview", "audio": result}

        studio.submit("কণ্ঠ প্রিভিউ", work)

    def play_preview(self, audio):
        path = (audio or {}).get("audio")
        if path:
            self.audio_preview.play(path)
            self.studio.log(f"কণ্ঠ: {(audio or {}).get('engine')} · "
                            f"{(audio or {}).get('duration', 0):.1f} সেকেন্ড", "ok")

    def on_list_offline(self):
        def work(progress, log, cancel):
            from core import tts
            items = tts.list_offline_voices()
            for voice_id, name in items:
                log(f"• {name}", "dim")
            if not items:
                log("কোনো অফলাইন কণ্ঠ পাওয়া যায়নি", "warn")
            return {"kind": "offline_voices", "items": items}

        self.studio.submit("অফলাইন কণ্ঠ", work)
