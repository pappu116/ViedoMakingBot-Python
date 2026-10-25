"""Content library: browse bundled templates and generate a starting script."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from core import script as script_lib
from ui import widgets


class ContentPage(QWidget):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.templates = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(4)
        header.addWidget(widgets.label("কন্টেন্ট লাইব্রেরি", "h1"))
        header.addWidget(widgets.label(
            "বিল্ট-ইন টেমপ্লেটগুলো দেখুন — এক ক্লিকে সেটা দিয়ে স্ক্রিপ্ট বানান। "
            "নতুন টেমপ্লেট যোগ করতে চাইলে content/templates ফোল্ডারে JSON ফাইল রাখুন।", "muted"))
        outer.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        left_card = widgets.Card(title="টেমপ্লেট", icon_name="content")
        self.niche_combo = QListWidget()
        self.niche_combo.setMinimumHeight(420)
        self.niche_combo.currentRowChanged.connect(self._on_select)
        left_card.add(self.niche_combo)
        left_card.add(widgets.button("রিফ্রেশ", "ghost", "refresh", on_click=self.refresh))
        columns.addWidget(left_card, 2)

        right_card = widgets.Card(title="নমুনা", icon_name="eye")
        self.sample_box = QVBoxLayout()
        self.sample_box.setSpacing(10)
        right_card.add_layout(self.sample_box)
        right_card.add(widgets.button("এই টেমপ্লেট দিয়ে স্ক্রিপ্ট বানান", "primary", "wand",
                                      on_click=self.on_use))
        columns.addWidget(right_card, 3)

        outer.addLayout(columns, 1)
        self.refresh()

    def refresh(self):
        self.niche_combo.clear()
        self.templates = []
        try:
            files = script_lib.load_templates("all")
        except Exception as exc:
            self.studio.log(f"টেমপ্লেট লোড হয়নি: {exc}", "error")
            files = []
        for index, template in enumerate(files):
            niche = template.get("niche", "custom")
            count = len(template.get("body_patterns") or [])
            item = QListWidgetItem(f"{niche}  ·  {count} ধরনের স্ক্রিপ্ট")
            self.niche_combo.addItem(item)
            self.templates.append(template)
        if not self.templates:
            self.studio.log("কোনো টেমপ্লেট পাওয়া যায়নি", "warn")

    def _current(self):
        row = self.niche_combo.currentRow()
        if row < 0 or row >= len(self.templates):
            return None
        return self.templates[row]

    def _on_select(self, _row):
        template = self._current()
        while self.sample_box.count():
            item = self.sample_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not template:
            return
        self.sample_box.addWidget(widgets.label(template.get("niche", ""), "h2"))
        try:
            sample = script_lib.from_template(template.get("niche"), 1)[0]
        except Exception:
            sample = None
        if sample:
            self.sample_box.addWidget(widgets.label(sample["title"], "accent", wrap=True))
            body = widgets.label(sample["body"], "muted", wrap=True)
            body.setMinimumWidth(380)
            self.sample_box.addWidget(body)
            self.sample_box.addWidget(widgets.label(
                f"দৃশ্য: {len(sample.get('scenes') or [])} · ট্যাগ: {', '.join(sample.get('tags') or [])}",
                "muted", wrap=True))
        self.sample_box.addStretch(1)

    def on_use(self):
        template = self._current()
        if not template:
            self.studio.log("আগে একটি টেমপ্লেট বেছে নিন", "warn")
            return
        try:
            script = script_lib.from_template(template.get("niche"), 1)[0]
        except Exception as exc:
            self.studio.log(str(exc), "error")
            return
        style = (self.studio.get("video") or {}).get("style", "cinematic")
        script["style"] = style
        self.studio.set_script(script)
        self.studio.log("টেমপ্লেট থেকে স্ক্রিপ্ট তৈরি: " + script.get("title", ""), "ok")
        self.studio.navigate.emit("script")
