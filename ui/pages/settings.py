"""Settings: AI keys, defaults, upload behaviour and folders."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLineEdit, QMessageBox, QSpinBox,
                               QVBoxLayout, QWidget)

from core import script_ai
from ui import widgets

VERSION = "1.0"


class SettingsPage(QWidget):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self._loading = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(widgets.label("সেটিংস", "h1"))
        outer.addWidget(widgets.label("Key, ডিফল্ট মান আর আপলোডের নিয়ম — সব এখানে।", "muted"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        # ---------------------------------------------------------------- AI
        ai_card = widgets.Card(title="AI স্ক্রিপ্ট", icon_name="sparkles")
        self.provider_combo = QComboBox()
        for provider in script_ai.PROVIDERS:
            self.provider_combo.addItem(provider["name"], provider["id"])
        ai_card.add(widgets.field_row("প্রোভাইডার", self.provider_combo,
                                      "Key ছাড়াও কাজ করে (Pollinations)"))
        self.keys = {}
        for provider_id, hint in (("gemini", "aistudio.google.com থেকে ফ্রি"),
                                  ("groq", "console.groq.com থেকে ফ্রি"),
                                  ("openrouter", "openrouter.ai থেকে ফ্রি")):
            field = QLineEdit()
            field.setEchoMode(QLineEdit.Password)
            field.setPlaceholderText("API key")
            ai_card.add(widgets.field_row(provider_id.title(), field, hint))
            self.keys[provider_id] = field
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("খালি রাখলে ডিফল্ট মডেল")
        ai_card.add(widgets.field_row("মডেল", self.model_edit, "ঐচ্ছিক"))
        self.ollama_edit = QLineEdit()
        self.ollama_edit.setPlaceholderText("http://localhost:11434")
        ai_card.add(widgets.field_row("Ollama ঠিকানা", self.ollama_edit, "লোকাল মডেলের জন্য"))
        self.pollen_edit = QLineEdit()
        self.pollen_edit.setPlaceholderText("ঐচ্ছিক — ফ্রি লিমিট বাড়ায়")
        ai_card.add(widgets.field_row("Pollinations টোকেন", self.pollen_edit,
                                      "ছবির ৪৫ সেকেন্ডের লিমিট উঠে যায়"))
        left.addWidget(ai_card)

        # ----------------------------------------------------------- upload
        upload_card = widgets.Card(title="আপলোড", icon_name="upload")
        self.visibility_combo = QComboBox()
        for value, text in (("public", "Public"), ("unlisted", "Unlisted"), ("private", "Private")):
            self.visibility_combo.addItem(text, value)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100)
        self.limit_spin.setValue(6)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(widgets.field_row("ডিফল্ট ভিজিবিলিটি", self.visibility_combo, "", width=130))
        row.addWidget(widgets.field_row("দিনে সর্বোচ্চ আপলোড", self.limit_spin,
                                        "০ = সীমা নেই", width=130))
        upload_card.add_layout(row)
        self.headless_switch = widgets.switch_row(
            "হেডলেস ব্রাউজার", "ব্যাকগ্রাউন্ডে আপলোড (ব্রাউজার দেখবেন না)",
            checked=False, on_change=lambda v: self._set("upload", "headless", bool(v)))
        upload_card.add(self.headless_switch)
        left.addWidget(upload_card)

        # -------------------------------------------------------------- UI
        ui_card = widgets.Card(title="ইন্টারফেস", icon_name="settings")
        self.notify_switch = widgets.switch_row(
            "কাজ শেষে জানান", "Windows নোটিফিকেশন দেখাবে", checked=True,
            on_change=lambda v: self._set("ui", "notify_on_done", bool(v)))
        self.open_switch = widgets.switch_row(
            "রেন্ডার শেষে আউটপুট ফোল্ডার খুলুন", "", checked=True,
            on_change=lambda v: self._set("ui", "open_output_after_render", bool(v)))
        ui_card.add(self.notify_switch)
        ui_card.add(self.open_switch)
        left.addWidget(ui_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)

        paths_card = widgets.Card(title="ফোল্ডার", icon_name="folder_open")
        self.output_picker = widgets.PathPicker(mode="dir", placeholder="খালি = ডিফল্ট output")
        self.music_picker = widgets.PathPicker(mode="dir", placeholder="নিজের মিউজিক ফোল্ডার (ঐচ্ছিক)")
        self.images_picker = widgets.PathPicker(mode="dir", placeholder="নিজের ছবির ফোল্ডার (ঐচ্ছিক)")
        paths_card.add(widgets.field_row("আউটপুট", self.output_picker, "", width=90))
        paths_card.add(widgets.field_row("মিউজিক", self.music_picker, "", width=90))
        paths_card.add(widgets.field_row("ছবি", self.images_picker, "", width=90))
        right.addWidget(paths_card)

        save_card = widgets.Card(title="সেভ ও রিসেট", icon_name="save")
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(widgets.button("সেভ করুন", "primary", "save", on_click=self.on_save))
        row.addWidget(widgets.button("ক্যাশ পরিষ্কার", "ghost", "trash", on_click=self.on_clear_cache))
        save_card.add_layout(row)
        right.addWidget(save_card)

        about_card = widgets.Card(title=f"সম্পর্কে — YTFB Studio {VERSION}", icon_name="info")
        about_card.add(widgets.label(
            "সম্পূর্ণ ফ্রি টুল: নিজের স্ক্রিপ্ট বা AI দিয়ে ভিডিও বানিয়ে YouTube ও Facebook-এ "
            "আপলোড করা যায়। কোনো paid API লাগে না — edge-tts, Pollinations, Wikimedia আর "
            "নিজের তৈরি মিউজিক ব্যবহার হয়।\n\n"
            "দায়িত্ব আপনার: প্ল্যাটফর্মের নিয়ম (ToS) মেনে চলুন, নিজের কনটেন্ট আপলোড করুন, "
            "ডিলে কম রাখবেন না এবং দিনে অনেক আপলোড করবেন না — এতে আপনার একাউন্ট সুরক্ষিত থাকবে।",
            "muted", wrap=True))
        right.addWidget(about_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        self._loading = False
        self._connect()
        self._sync()

    # -------------------------------------------------------------- helpers
    def _connect(self):
        self.provider_combo.currentIndexChanged.connect(self._save)
        self.model_edit.editingFinished.connect(self._save)
        self.ollama_edit.editingFinished.connect(self._save)
        self.pollen_edit.editingFinished.connect(self._save)
        for field in self.keys.values():
            field.editingFinished.connect(self._save)
        self.visibility_combo.currentIndexChanged.connect(self._save)
        self.limit_spin.valueChanged.connect(self._save)
        for picker in (self.output_picker, self.music_picker, self.images_picker):
            picker.edit.editingFinished.connect(self._save)

    def _set(self, section, key, value):
        self.studio.set_setting(section, key, value)

    def _sync(self):
        cfg = self.studio.settings
        ai = cfg.get("ai") or {}
        for index in range(self.provider_combo.count()):
            if self.provider_combo.itemData(index) == ai.get("provider", "pollinations"):
                self.provider_combo.setCurrentIndex(index)
                break
        for provider_id, field in self.keys.items():
            field.setText((ai.get("keys") or {}).get(provider_id, ""))
        self.model_edit.setText(ai.get("model") or "")
        self.ollama_edit.setText(ai.get("ollama_url") or "http://localhost:11434")
        self.pollen_edit.setText(ai.get("pollen_token") or "")

        upload = cfg.get("upload") or {}
        for index in range(self.visibility_combo.count()):
            if self.visibility_combo.itemData(index) == upload.get("visibility", "public"):
                self.visibility_combo.setCurrentIndex(index)
                break
        self.limit_spin.setValue(int(upload.get("daily_limit") or 6))
        self.headless_switch.toggle.setChecked(bool(upload.get("headless", False)))

        ui = cfg.get("ui") or {}
        self.notify_switch.toggle.setChecked(bool(ui.get("notify_on_done", True)))
        self.open_switch.toggle.setChecked(bool(ui.get("open_output_after_render", True)))

        paths = cfg.get("paths") or {}
        self.output_picker.setText(paths.get("output_dir") or "")
        self.music_picker.setText(paths.get("music_dir") or "")
        self.images_picker.setText(paths.get("images_dir") or "")

    def _save(self):
        if self._loading:
            return
        cfg = self.studio.settings
        cfg.setdefault("ai", {})
        cfg["ai"]["provider"] = self.provider_combo.currentData()
        cfg["ai"]["model"] = self.model_edit.text().strip()
        cfg["ai"]["ollama_url"] = self.ollama_edit.text().strip() or "http://localhost:11434"
        cfg["ai"]["pollen_token"] = self.pollen_edit.text().strip()
        keys = cfg["ai"].setdefault("keys", {})
        for provider_id, field in self.keys.items():
            keys[provider_id] = field.text().strip()

        cfg.setdefault("upload", {})
        cfg["upload"]["visibility"] = self.visibility_combo.currentData()
        cfg["upload"]["daily_limit"] = self.limit_spin.value()

        cfg.setdefault("paths", {})
        cfg["paths"]["output_dir"] = self.output_picker.text()
        cfg["paths"]["music_dir"] = self.music_picker.text()
        cfg["paths"]["images_dir"] = self.images_picker.text()

        cfg.setdefault("video", {})
        cfg["video"]["own_images_dir"] = self.images_picker.text()

        self.studio.save_settings()
        self.studio.log("সেটিংস সেভ হয়েছে", "ok")

    def on_save(self):
        self._save()

    def on_clear_cache(self):
        box = QMessageBox(self)
        box.setWindowTitle("ক্যাশ পরিষ্কার করবেন?")
        box.setText("ডাউনলোড করা ছবি, ভয়েস ক্যাশ আর থাম্বনেইল মুছে যাবে। "
                    "আসল ভিডিও ফাইলগুলো থাকবে।")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        if box.exec() != QMessageBox.Yes:
            return
        from paths import cache_dir, thumb_dir
        for folder in (cache_dir(), thumb_dir()):
            if os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)
        self.studio.log("ক্যাশ পরিষ্কার করা হয়েছে", "ok")
