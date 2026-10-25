"""Step 5 — scene visuals, render and in-app preview."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget)

from core import projects as projects_lib
from core import render as render_lib
from core import script as script_lib
from ui import theme, widgets
from ui.components import player, wizard

THUMB_W, THUMB_H = 76, 135


def _round_pixmap(path, width=THUMB_W, height=THUMB_H, radius=10):
    label = QLabel()
    label.setFixedSize(width, height)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        f"background-color: {theme.CARD_ALT}; border: 1px solid {theme.BORDER_SOFT};"
        f" border-radius: {radius}px; color: {theme.MUTED_DARK};")
    if path and os.path.exists(path):
        pix = QPixmap(path).scaled(width - 2, height - 2, Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
        rounded = QPixmap(width, height)
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        shape = QPainterPath()
        shape.addRoundedRect(0, 0, width, height, radius, radius)
        painter.setClipPath(shape)
        painter.drawPixmap((width - pix.width()) // 2, (height - pix.height()) // 2, pix)
        painter.end()
        label.setPixmap(rounded)
    else:
        label.setText("ছবি\nনেই")
    return label


class PreviewPage(QWidget):
    step_index = 4

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.scene_rows = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "প্রিভিউ ও রেন্ডার",
            "প্রতিটি দৃশ্যের ছবি দেখে নিন — পছন্দ না হলে এক ক্লিকে বদলান, তারপর ভিডিও বানান।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(16)

        render_card = widgets.Card(title="রেন্ডার", icon_name="film")
        self.summary = widgets.label("", "muted", wrap=True)
        render_card.add(self.summary)
        self.progress = widgets.progress_bar(0, height=10)
        render_card.add(self.progress)
        self.status = widgets.label("প্রস্তুত", "dim")
        render_card.add(self.status)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.render_btn = widgets.button("ভিডিও তৈরি করুন", "primary", "play", on_click=self.on_render)
        row.addWidget(self.render_btn)
        self.cancel_btn = widgets.button("বাতিল", "danger", "stop", on_click=self.on_cancel)
        self.cancel_btn.setEnabled(False)
        row.addWidget(self.cancel_btn)
        row.addWidget(widgets.button("আউটপুট ফোল্ডার", "ghost", "folder_open",
                                     on_click=self.open_folder))
        row.addStretch(1)
        render_card.add_layout(row)
        left.addWidget(render_card)

        scene_card = widgets.Card(title="দৃশ্য ও ছবি", icon_name="image",
                                  subtitle="কীওয়ার্ড বদলে দিলে ছবিও বদলাবে")
        scene_card.add_row(
            widgets.button("সব দৃশ্যের ছবি আনুন", "primary", "image", on_click=self.on_load_all),
            widgets.button("সব ছবি নতুন করে", "ghost", "refresh", on_click=self.on_reroll_all),
            widgets.button("AI দিয়ে দৃশ্য মিলান", "ghost", "sparkles",
                           on_click=self.on_ai_prompts),
            None,
        )
        self.scene_box = QVBoxLayout()
        self.scene_box.setSpacing(10)
        scene_card.add_layout(self.scene_box)
        left.addWidget(scene_card)

        board_card = widgets.Card(title="স্টোরিবোর্ড (তৈরি হওয়া ভিডিওর)", icon_name="layers")
        self.board_row = QHBoxLayout()
        self.board_row.setSpacing(10)
        board_card.add_layout(self.board_row)
        left.addWidget(board_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        player_card = widgets.Card(title="প্রিভিউ", icon_name="eye")
        self.phone = widgets.PhonePreview(width=280)
        self.video_player = player.VideoPlayer()
        self.phone.set_widget(self.video_player)
        player_card.add(self.phone)
        player_card.add(widgets.button("ফাইল প্লেয়ারে চালান", "ghost", "external",
                                       on_click=self.open_external))
        right.addWidget(player_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("audio"),
                                         on_next=lambda: self.studio.navigate.emit("accounts"),
                                         next_text="একাউন্ট ধাপে যান"))

        self.studio.script_changed.connect(lambda _s: self.refresh_all())
        self.studio.settings_changed.connect(lambda _c: self.refresh_summary())
        self.set_board([])
        self.refresh_all()

    # -------------------------------------------------------------- helpers
    def refresh_all(self):
        self.refresh_summary()
        if not getattr(self, "_suppress_refresh", False):
            self.refresh_scenes()
        self._load_existing()

    def _apply_phone_aspect(self):
        aspect = (self.studio.get("video") or {}).get("aspect", "mobile")
        if aspect == "landscape":
            self.phone.set_aspect(16, 9)
        elif aspect == "square":
            self.phone.set_aspect(1, 1)
        else:
            self.phone.set_aspect(9, 16)

    def refresh_summary(self):
        self._apply_phone_aspect()
        opts = self.studio.render_options()
        script = self.studio.script or {}
        scenes = len(script.get("scenes") or [])
        from core import textrender
        from core import voices as voice_lib
        voice = opts.get("voice") or voice_lib.find(opts.get("lang", "bn"),
                                                    opts.get("gender", "female"),
                                                    opts.get("accent", "bd"))
        self.summary.setText(
            f"দৃশ্য: {scenes} · অনুপাত: {opts['aspect']} · স্টাইল: "
            f"{render_lib.style_label(opts['style'])}\n"
            f"কণ্ঠ: {voice_lib.label(voice)} · সাবটাইটেল: "
            f"{textrender.caption_style_label(opts.get('caption_style', 'bold'))} · "
            f"দৈর্ঘ্য লক্ষ্য: {opts['duration']} সেকেন্ড · "
            f"মিউজিক: {'চালু' if opts['music'] else 'বন্ধ'}")

    # ------------------------------------------------------------ scene list
    def refresh_scenes(self):
        while self.scene_box.count():
            item = self.scene_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.scene_rows = {}
        scenes = (self.studio.script or {}).get("scenes") or []
        if not scenes:
            self.scene_box.addWidget(widgets.empty_state(
                "কোনো দৃশ্য নেই", "ধাপ ১-এ স্ক্রিপ্ট তৈরি করুন", "content"))
            return
        for index, scene in enumerate(scenes):
            self.scene_box.addWidget(self._scene_row(index, scene))

    def _scene_row(self, index, scene):
        holder = widgets.Card()
        row = QHBoxLayout()
        row.setSpacing(12)

        thumb = _round_pixmap()
        row.addWidget(thumb, 0, Qt.AlignTop)

        middle = QVBoxLayout()
        middle.setSpacing(6)
        middle.addWidget(widgets.label(f"দৃশ্য {index + 1}", "dim"))
        text = widgets.label(scene.get("text", ""), "muted", wrap=True)
        middle.addWidget(text)
        edit = QLineEdit()
        edit.setPlaceholderText("ইমেজ কীওয়ার্ড (ইংরেজিতে ভালো কাজ করে)")
        edit.setText(", ".join(scene.get("keywords") or []))
        edit.editingFinished.connect(lambda i=index, e=edit: self._keywords_changed(i, e.text()))
        middle.addWidget(widgets.field_row("ছবির কীওয়ার্ড", edit,
                                           "যেমন: river, boat, sunrise", width=150))
        if not scene.get("matched", True):
            warning = widgets.label(
                "⚠ এই দৃশ্যের শব্দ অভিধানে মেলেনি, তাই ছবি সাধারণ আসবে — কীওয়ার্ড লিখুন "
                "অথবা ‘AI দিয়ে দৃশ্য মিলান’ চাপুন।", "muted", wrap=True)
            warning.setStyleSheet(f"color: {theme.WARN};")
            middle.addWidget(warning)
        note = widgets.label("", "muted", wrap=True)
        middle.addWidget(note)
        row.addLayout(middle, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(widgets.button("নতুন ছবি", "ghost", "refresh",
                                         on_click=lambda i=index: self.on_reroll(i)))
        buttons.addWidget(widgets.button("এখানেই ব্যবহার", "ghost", "check",
                                         on_click=lambda i=index: self.on_pick(i)))
        buttons.addStretch(1)
        row.addLayout(buttons)

        holder.add_layout(row)
        self.scene_rows[index] = {"thumb": thumb, "note": note, "edit": edit,
                                  "row": holder, "layout": row, "variant": 0}
        return holder

    def _keywords_changed(self, index, text):
        keywords = [part.strip() for part in str(text).split(",") if part.strip()]
        script = dict(self.studio.script or {})
        scenes = [dict(scene) for scene in (script.get("scenes") or [])]
        if index >= len(scenes):
            return
        style = (self.studio.get("video") or {}).get("style", "cinematic")
        style_hint = script_lib.STYLE_VISUALS.get(style, script_lib.STYLE_VISUALS["cinematic"])
        scenes[index]["keywords"] = keywords
        scenes[index]["image_prompt"] = f"{', '.join(keywords)}, {style_hint}" if keywords else ""
        script["scenes"] = scenes
        # do not rebuild the rows while the user is editing one of them
        self._suppress_refresh = True
        try:
            self.studio.update_script(**script)
        finally:
            self._suppress_refresh = False
        self.studio.log(f"দৃশ্য {index + 1} এর কীওয়ার্ড আপডেট হয়েছে", "dim")

    # -------------------------------------------------------------- actions
    def _reroll(self, index):
        opts = self.studio.render_options()
        variant = self.scene_rows.get(index, {}).get("variant", 0) + 1
        script = self.studio.script or {}

        def work(progress, log, cancel):
            from core import pipeline
            progress(0.2, f"দৃশ্য {index + 1} এর নতুন ছবি আনা হচ্ছে…")
            result = pipeline.build_scene_visual(script, opts, index=index, variant=variant)
            progress(1.0, "ছবি প্রস্তুত")
            return result

        self.studio.submit(f"ছবি (দৃশ্য {index + 1})", work)

    def on_reroll(self, index):
        self._reroll(index)

    def on_reroll_all(self):
        for index in self.scene_rows:
            self._reroll(index)

    def on_pick(self, index):
        """Accept the current thumbnail as the visual for this scene."""
        entry = self.scene_rows.get(index) or {}
        path = getattr(entry.get("thumb"), "_source_path", "")
        if path:
            self.studio.log(f"দৃশ্য {index + 1}: নির্বাচিত ছবি ব্যবহার করা হবে", "ok")
        else:
            self.studio.log("আগে ছবি আনুন", "warn")

    def on_load_all(self):
        script = self.studio.script or {}
        if not script.get("scenes"):
            self.studio.log("আগে স্ক্রিপ্ট তৈরি করুন", "warn")
            return
        opts = self.studio.render_options()

        def work(progress, log, cancel):
            from core import pipeline
            return pipeline.build_storyboard(script, opts, progress=progress, cancel=cancel)

        self.studio.submit("সব দৃশ্যের ছবি", work)

    def on_ai_prompts(self):
        """Ask the AI to write one image prompt per scene from the script text."""
        studio = self.studio
        script = studio.script or {}
        if not (script.get("scenes") or []):
            studio.log("আগে স্ক্রিপ্ট তৈরি করুন", "warn")
            return
        ai = studio.get("ai") or {}
        provider = ai.get("provider", "pollinations")
        keys = ai.get("keys") or {}
        model = ai.get("model") or None
        ollama_url = ai.get("ollama_url") or None
        style = (studio.get("video") or {}).get("style", "cinematic")

        def work(progress, log, cancel):
            from core import script_ai
            progress(0.15, f"AI ({provider}) দিয়ে দৃশ্যের প্রম্পট লেখা হচ্ছে…")
            prompts = script_ai.generate_image_prompts(
                script.get("scenes") or [], provider=provider, keys=keys, model=model,
                ollama_url=ollama_url, style=style)
            updated = script_lib.apply_image_prompts(script, prompts)
            for line in prompts:
                log("• " + line, "dim")
            progress(1.0, "সব দৃশ্যের প্রম্পট তৈরি")
            return {"kind": "ai_prompts", "script": updated, "prompts": prompts}

        studio.submit("AI দৃশ্য মিলান", work)

    def set_scene_visual(self, result):
        index = result.get("index")
        image = result.get("image")
        entry = self.scene_rows.get(index)
        if entry is None or not image:
            return
        variant = int(result.get("variant") or 0)
        entry["variant"] = variant
        new_thumb = _round_pixmap(image)
        new_thumb._source_path = image
        entry["layout"].replaceWidget(entry["thumb"], new_thumb)
        entry["thumb"].deleteLater()
        entry["thumb"] = new_thumb
        entry["note"].setText(
            f"উৎস: {result.get('note', '')} · প্রম্পট: {result.get('prompt', '')[:110]}")

    def set_storyboard(self, items):
        for item in items or []:
            self.set_scene_visual(item)

    # --------------------------------------------------------------- render
    def on_render(self):
        studio = self.studio
        try:
            script = studio.require_script()
        except Exception as exc:
            studio.log(str(exc), "warn")
            return
        opts = studio.render_options()
        self.render_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)

        def work(progress, log, cancel):
            from core import pipeline
            result = pipeline.build_video(script, opts, progress=progress, log=log, cancel=cancel)
            result["kind"] = "render"
            return result

        studio.submit("ভিডিও রেন্ডার", work)

    def on_cancel(self):
        self.studio.queue.cancel_current()
        self.studio.log("বাতিলের অনুরোধ পাঠানো হয়েছে", "warn")

    def show_result(self, result):
        self.render_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(1000)
        video = result.get("video")
        if video and os.path.exists(video):
            self.video_player.load(video)
            self._apply_phone_aspect()
            self.status.setText("তৈরি: " + os.path.basename(video))
            if self.studio.project:
                project = projects_lib.update(
                    self.studio.project["id"], video_path=video,
                    thumbnail=result.get("thumbnail", ""),
                    duration=result.get("duration", 0),
                    title=(self.studio.script or {}).get("title", ""))
                self.studio.project = project
                self.studio.project_changed.emit(project)
        else:
            self.status.setText("ভিডিও পাওয়া যায়নি")

    def set_board(self, images):
        while self.board_row.count():
            item = self.board_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for path in images[:5]:
            self.board_row.addWidget(widgets.thumbnail_label(path, 108, 192))
        if not images:
            self.board_row.addWidget(widgets.empty_state("স্টোরিবোর্ড নেই", "", "layers"))
        self.board_row.addStretch(1)

    def set_progress(self, ratio, message):
        self.progress.setValue(int(max(0.0, min(1.0, ratio)) * 1000))
        if message:
            self.status.setText(message)

    def _load_existing(self):
        last = self.studio.last_render or {}
        video = last.get("video")
        if video and os.path.exists(video):
            self.video_player.load(video)
            self._apply_phone_aspect()
            self.status.setText("সর্বশেষ তৈরি: " + os.path.basename(video))
            self.set_board(last.get("storyboard") or [])

    def open_folder(self):
        from paths import outputs_dir
        _open_path(outputs_dir())

    def open_external(self):
        video = (self.studio.last_render or {}).get("video")
        if video and os.path.exists(video):
            _open_path(video)
        else:
            self.studio.log("আগে ভিডিও তৈরি করুন", "warn")


def _open_path(path):
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606 - opening the user's own output folder
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
