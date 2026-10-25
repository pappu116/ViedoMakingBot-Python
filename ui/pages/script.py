"""Step 1 — idea and script (AI, own script, templates)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QPushButton,
                               QTextEdit, QVBoxLayout, QWidget)

from core import script as script_lib
from core import script_ai
from ui import theme, widgets
from ui.components import wizard

TONES = {
    "শিক্ষামূলক": "educational",
    "অনুপ্রেরণামূলক": "motivational",
    "গল্পের মতো": "storytelling",
    "মজার": "funny",
    "খবরধর্মী": "news",
    "রহস্যময়": "mysterious",
}
TONES_REVERSE = {v: k for k, v in TONES.items()}

EXAMPLES = {
    "bn": [
        "বাংলাদেশের নদী ও নৌকা নিয়ে ৪৫ সেকেন্ডের শর্টস",
        "প্রতিদিন সকালে ওঠার ৫টি অভ্যাস",
        "সফল হওয়ার জন্য ধৈর্যের গুরুত্ব",
        "গ্রাম বাংলার প্রকৃতি কতটা সুন্দর",
    ],
    "en": [
        "5 morning habits that change your life",
        "Why consistency beats motivation",
        "Amazing facts about the ocean",
        "How to start freelancing in 2026",
    ],
}

MODES = ["AI দিয়ে লিখুন", "নিজের স্ক্রিপ্ট", "টেমপ্লেট"]


class ScriptPage(QWidget):
    step_index = 0

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.mode = MODES[0]
        self.mode_buttons = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "ভিডিও তৈরি করুন",
            "আপনার আইডিয়া দিন অথবা নিজের স্ক্রিপ্ট লিখুন — বাকিটা অ্যাপ করে দেবে।"))

        left = QVBoxLayout()
        left.setSpacing(16)

        # ---------------------------------------------------------- idea card
        idea_card = widgets.Card(title="আপনার ধারণা লিখুন", icon_name="wand",
                                 right_widget=self._link("উদাহরণ দেখুন", self._insert_example))
        row = QHBoxLayout()
        row.setSpacing(10)
        for index, name in enumerate(MODES):
            pill = QPushButton(name)
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            pill.setMinimumHeight(36)
            pill.clicked.connect(lambda _=False, m=name: self.set_mode(m))
            row.addWidget(pill)
            self.mode_buttons[name] = pill
        row.addStretch(1)
        idea_card.add_layout(row)

        self.topic_input = widgets.SearchField("বিষয় / ধারণা লিখুন…")
        idea_card.add(widgets.field_row("আপনার ভিডিও আইডিয়া", self.topic_input,
                                        "আপনার ভিডিও কী সম্পর্কে?"))

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["বাংলা (Bangla)", "ইংরেজি (English)"])
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(list(TONES.keys()))
        pair = QHBoxLayout()
        pair.setSpacing(12)
        pair.addWidget(widgets.field_row("ভাষা", self.lang_combo,
                                         "লেখা দেখে স্বয়ংক্রিয়ভাবে ঠিক হয়", width=120))
        pair.addWidget(widgets.field_row("সুর", self.tone_combo, "", width=100))
        idea_card.add_layout(pair)

        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText(
            "আপনার ভিডিও ধারণা বা পুরো স্ক্রিপ্ট এখানে লিখুন…\n"
            "যেমন: বাংলাদেশের ইতিহাস, প্রযুক্তি, স্বাস্থ্য টিপস ইত্যাদি")
        self.text_area.setMinimumHeight(190)
        self.text_area.textChanged.connect(self._update_counter)
        idea_card.add(self.text_area)
        self.counter = widgets.label("০ অক্ষর", "muted")
        idea_card.add(self.counter)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.generate_btn = widgets.button("AI দিয়ে স্ক্রিপ্ট লিখুন", "primary", "sparkles",
                                           on_click=self.on_generate)
        actions.addWidget(self.generate_btn)
        actions.addWidget(widgets.button("ফাইল থেকে আনুন", "ghost", "folder_open",
                                        on_click=self.on_import))
        actions.addWidget(widgets.button("নমুনা স্ক্রিপ্ট", "ghost", "content",
                                        on_click=self.on_template))
        actions.addStretch(1)
        idea_card.add_layout(actions)
        left.addWidget(idea_card)

        # ------------------------------------------------------- script card
        self.script_card = widgets.Card(title="আপনার স্ক্রিপ্ট", icon_name="content",
                                        subtitle="চাইলে হাতে বদলে নিতে পারেন")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("ভিডিওর টাইটেল")
        self.script_card.add(widgets.field_row("টাইটেল", self.title_edit, "শর্টসে এটাই দেখাবে"))
        self.body_edit = QTextEdit()
        self.body_edit.setMinimumHeight(150)
        self.body_edit.setPlaceholderText("ভয়েসওভারের লেখা এখানে আসবে…")
        self.script_card.add(widgets.label("ভয়েস ও সাবটাইটেল টেক্সট", "dim"))
        self.script_card.add(self.body_edit)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("bangla, motivation, shorts")
        self.script_card.add(widgets.field_row("ট্যাগ", self.tags_edit, "কমা দিয়ে আলাদা করুন"))

        self.scene_box = QVBoxLayout()
        self.scene_box.setSpacing(6)
        self.script_card.add_layout(self.scene_box)
        self.script_card.add_row(
            widgets.button("স্ক্রিপ্ট থেকে দৃশ্য তৈরি করুন", "ghost", "layers",
                           on_click=self.on_rebuild),
            widgets.button("এই স্ক্রিপ্ট দিয়ে এগিয়ে যান", "primary", "chevron_right",
                           on_click=lambda: self.studio.navigate.emit("visuals")),
        )
        left.addWidget(self.script_card)
        left.addStretch(1)

        outer.addLayout(left)
        self.set_mode(MODES[0])
        self.studio.script_changed.connect(self._sync_from_state)

    # ---------------------------------------------------------------- utils
    def _link(self, text, handler):
        label = widgets.label(text, "link")
        label.setCursor(Qt.PointingHandCursor)
        label.mousePressEvent = lambda _event: handler()
        return label

    def _update_counter(self):
        count = len(self.text_area.toPlainText())
        self.counter.setText(f"{count} অক্ষর · আনুমানিক {max(1, count // 18)} সেকেন্ড ভয়েস")

    def _insert_example(self):
        lang = "bn" if self.lang_combo.currentIndex() == 0 else "en"
        examples = EXAMPLES[lang]
        self.topic_input.setText(examples[len(self.topic_input.text()) % len(examples)])

    def lang_code(self):
        return "bn" if self.lang_combo.currentIndex() == 0 else "en"

    def set_mode(self, mode):
        self.mode = mode
        for name, pill in self.mode_buttons.items():
            active = name == mode
            pill.setStyleSheet(
                f"QPushButton {{ border-radius: 10px; padding: 8px 16px;"
                f" background-color: {theme.ACCENT_SOFT if active else 'transparent'};"
                f" border: 1px solid {theme.ACCENT_HOVER if active else theme.BORDER_SOFT};"
                f" color: {'#FFFFFF' if active else theme.MUTED};"
                f" font-weight: {'700' if active else '500'}; }}"
                f"QPushButton:hover {{ color: {theme.TEXT}; }}")
        label = {"AI দিয়ে লিখুন": "AI দিয়ে স্ক্রিপ্ট লিখুন",
                 "নিজের স্ক্রিপ্ট": "নিজের লেখা থেকে তৈরি করুন",
                 "টেমপ্লেট": "টেমপ্লেট থেকে তৈরি করুন"}.get(mode)
        self.generate_btn.setText(label)
        if mode == "নিজের স্ক্রিপ্ট":
            self.text_area.setPlaceholderText("আপনার নিজের পুরো স্ক্রিপ্ট এখানে লিখে দিন…")
        elif mode == "টেমপ্লেট":
            self.text_area.setPlaceholderText("টেমপ্লেট থেকে বানাতে উপরে শুধু বিষয় লিখুন…")
        else:
            self.text_area.setPlaceholderText(
                "চাইলে নিজের লেখা স্ক্রিপ্টও এখানে দিতে পারেন — খালি রাখলে AI লিখবে।")

    # --------------------------------------------------------------- actions
    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "স্ক্রিপ্ট ফাইল", "", "টেক্সট ফাইল (*.txt *.md *.srt *.vtt);;সব ফাইল (*.*)")
        if not path:
            return
        try:
            text = script_lib.load_script_file(path)
        except Exception as exc:
            self.studio.log(f"ফাইল পড়া যায়নি: {exc}", "error")
            return
        self.text_area.setPlainText(text)
        self.set_mode("নিজের স্ক্রিপ্ট")
        if not self.topic_input.text().strip():
            self.topic_input.setText(os.path.splitext(os.path.basename(path))[0])
        self.studio.log("স্ক্রিপ্ট ফাইল লোড হয়েছে: " + os.path.basename(path), "ok")

    def on_generate(self):
        topic = self.topic_input.text().strip()
        own_text = self.text_area.toPlainText().strip()
        lang = self.lang_code()
        # The written words decide the language: a Bangla script must never turn
        # into an English video just because the dropdown was left on English.
        detected = "bn" if script_lib._is_bangla(topic + " " + own_text) else "en"
        if detected != lang:
            lang = detected
            self.lang_combo.setCurrentIndex(0 if lang == "bn" else 1)
            self.studio.log(
                f"লেখা {'বাংলা' if lang == 'bn' else 'ইংরেজি'} — ভাষা স্বয়ংক্রিয়ভাবে "
                f"{'বাংলা' if lang == 'bn' else 'ইংরেজি'} ধরা হলো", "dim")
        tone = TONES.get(self.tone_combo.currentText(), "educational")
        style = (self.studio.get("video") or {}).get("style", "cinematic")
        duration = int((self.studio.get("video") or {}).get("duration") or 45)

        if self.mode == "নিজের স্ক্রিপ্ট":
            if not own_text:
                self.studio.log("নিজের স্ক্রিপ্ট লিখুন বা ফাইল থেকে আনুন", "warn")
                return
            self._plain(own_text, topic, lang, style)
            return

        if not topic and not own_text:
            self.studio.log("আগে বিষয় বা স্ক্রিপ্ট লিখুন", "warn")
            return

        if self.mode == "টেমপ্লেট" or not topic:
            self._template(topic or own_text[:60], lang, style)
            return

        ai = self.studio.get("ai") or {}
        provider = ai.get("provider", "pollinations")
        keys = ai.get("keys") or {}
        model = ai.get("model") or None
        ollama_url = ai.get("ollama_url") or None

        def work(progress, log, cancel):
            progress(0.15, f"স্ক্রিপ্ট লেখা হচ্ছে ({provider})…")
            if own_text:
                base = script_lib.from_own_text(own_text, title=topic or None, lang=lang, style=style)
            else:
                base = script_ai.generate_script(
                    topic, provider=provider, keys=keys, model=model, lang=lang, tone=tone,
                    duration_sec=duration, style=style, ollama_url=ollama_url)
            if cancel():
                return {"kind": "script", "script": base, "cancelled": True}
            progress(0.9, "দৃশ্য সাজানো হচ্ছে…")
            if own_text and topic:
                base["title"] = topic
            for warning in base.get("warnings") or []:
                log(warning, "warn")
            progress(1.0, "স্ক্রিপ্ট তৈরি")
            return {"kind": "script", "script": base}

        self.studio.submit("স্ক্রিপ্ট তৈরি", work)

    def on_template(self):
        topic = self.topic_input.text().strip()
        preview = self.text_area.toPlainText().strip()[:60]
        style = (self.studio.get("video") or {}).get("style", "cinematic")
        self._template(topic or preview, self.lang_code(), style)

    def _plain(self, text, topic, lang, style):
        try:
            # the pasted text decides the language, not the dropdown
            lang = script_lib.normalize_lang("auto", text)
            script = script_lib.from_own_text(text, title=topic or None, lang=lang, style=style)
        except Exception as exc:
            self.studio.log(str(exc), "error")
            return
        self._apply(script)

    def _template(self, topic, lang, style):
        try:
            items = script_lib.from_template("bangla" if lang == "bn" else "all", 1)
        except Exception:
            items = script_lib.from_template("all", 1)
        script = items[0]
        if topic and not script_lib._is_bangla(topic):
            script["title"] = topic
        script["style"] = style
        self._apply(script)

    def _apply(self, script):
        self.studio.set_script(script)
        if not self.studio.project:
            from core import projects as projects_lib
            self.studio.project = projects_lib.create(
                title=script.get("title", ""), idea=script.get("topic", ""),
                script=script, settings=self.studio.settings)
            self.studio.project_changed.emit(self.studio.project)
        elif self.studio.project:
            from core import projects as projects_lib
            self.studio.project = projects_lib.update(
                self.studio.project["id"], title=script.get("title", ""), script=script)
        self.studio.log("স্ক্রিপ্ট প্রস্তুত — দৃশ্য সংখ্যা: "
                        f"{len(script.get('scenes') or [])}", "ok")

    def on_rebuild(self):
        title = self.title_edit.text().strip()
        body = self.body_edit.toPlainText().strip()
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        if not body:
            self.studio.log("ভয়েস টেক্সট খালি", "warn")
            return
        style = (self.studio.get("video") or {}).get("style", "cinematic")
        script = script_lib.build_script(title=title or "আমার ভিডিও", body=body, tags=tags,
                                         niche="custom", lang=self.lang_code(), style=style,
                                         topic=self.topic_input.text().strip())
        self.studio.set_script(script)
        self.studio.log("স্ক্রিপ্ট থেকে নতুন দৃশ্য তৈরি হয়েছে", "ok")

    def _sync_from_state(self, script):
        if not script:
            return
        if not self.title_edit.hasFocus() and self.title_edit.text() != script.get("title", ""):
            self.title_edit.setText(script.get("title", ""))
        body = script.get("body") or ""
        if not self.body_edit.hasFocus() and self.body_edit.toPlainText().strip() != body.strip():
            self.body_edit.setPlainText(body)
        if not self.tags_edit.hasFocus():
            self.tags_edit.setText(", ".join(script.get("tags") or []))
        self._render_scenes(script)

    def _render_scenes(self, script):
        while self.scene_box.count():
            item = self.scene_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        scenes = script.get("scenes") or []
        self.scene_box.addWidget(widgets.label(f"দৃশ্য ({len(scenes)})", "dim"))
        for index, scene in enumerate(scenes[:14]):
            chip = widgets.label(f"{index + 1}. {scene.get('text', '')}", "chip", wrap=True)
            self.scene_box.addWidget(chip)
