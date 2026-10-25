"""Step 7 — publish queue: platform, profiles, visibility and dry-run."""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QListWidget, QListWidgetItem,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from core.upload import limits as limits_lib
from ui import widgets
from ui.components import wizard

VISIBILITIES = [("public", "সবার জন্য (Public)"), ("unlisted", "আনলিস্টেড"),
                ("private", "প্রাইভেট")]


class PublishPage(QWidget):
    step_index = 6

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self._loading = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "পাবলিশ করুন",
            "কোন প্ল্যাটফর্মে, কোন একাউন্টে যাবে ঠিক করুন — ড্রাই-রান দিয়ে টেস্টও করা যায়।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        target_card = widgets.Card(title="কোথায় যাবে", icon_name="upload")
        self.yt_check = QCheckBox("YouTube")
        self.fb_check = QCheckBox("Facebook (Reels)")
        self.yt_check.setChecked(True)
        self.fb_check.setChecked(True)
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self.yt_check)
        row.addWidget(self.fb_check)
        row.addStretch(1)
        target_card.add_layout(row)

        target_card.add(widgets.label("প্রোফাইল (একাধিক বেছে নিতে পারেন)", "dim"))
        self.profile_list = QListWidget()
        self.profile_list.setMinimumHeight(110)
        target_card.add(self.profile_list)
        self.profile_empty = widgets.empty_state(
            "কোনো প্রোফাইল নেই", "ধাপ ৬-এ গিয়ে একটি প্রোফাইল যোগ করুন", "user")
        target_card.add(self.profile_empty)

        self.visibility = QComboBox()
        for value, text in VISIBILITIES:
            self.visibility.addItem(text, value)
        self.delay_min = QSpinBox()
        self.delay_min.setRange(5, 3600)
        self.delay_min.setValue(30)
        self.delay_max = QSpinBox()
        self.delay_max.setRange(5, 7200)
        self.delay_max.setValue(90)
        pair = QHBoxLayout()
        pair.setSpacing(14)
        pair.addWidget(widgets.field_block("ভিজিবিলিটি", self.visibility,
                                           "ভিডিও কে দেখতে পাবে"), 1)
        pair.addWidget(widgets.field_block("কমপক্ষে ডিলে (সেকেন্ড)", self.delay_min,
                                           "আপলোডের আগে অপেক্ষা"), 1)
        pair.addWidget(widgets.field_block("বেশি হলে (সেকেন্ড)", self.delay_max,
                                           "এর মধ্যে র‍্যান্ডম"), 1)
        target_card.add_layout(pair)

        self.kids_switch = widgets.switch_row("বাচ্চাদের জন্য বানানো", "সাধারণত বন্ধ রাখুন",
                                              checked=False,
                                              on_change=lambda v: self._set("made_for_kids", v))
        self.dry_switch = widgets.switch_row(
            "ড্রাই-রান মোড", "সব ফিলাপ হবে কিন্তু Publish চাপা হবে না (পরীক্ষার জন্য)",
            checked=False, on_change=lambda v: self._set("dry_run", v))
        target_card.add(self.kids_switch)
        target_card.add(self.dry_switch)
        self.visibility.currentIndexChanged.connect(self._save)
        self.delay_min.valueChanged.connect(self._save)
        self.delay_max.valueChanged.connect(self._save)
        left.addWidget(target_card)

        video_card = widgets.Card(title="কোন ভিডিও", icon_name="film")
        self.video_list = QListWidget()
        self.video_list.setMinimumHeight(120)
        video_card.add(self.video_list)
        self.video_empty = widgets.empty_state(
            "কোনো ভিডিও নেই", "ধাপ ৫-এ গিয়ে ভিডিও তৈরি করুন", "film")
        video_card.add(self.video_empty)
        video_card.add(widgets.button("তালিকা রিফ্রেশ", "ghost", "refresh",
                                      on_click=self.refresh_videos))
        left.addWidget(video_card)

        queue_card = widgets.Card(title="কিউ", icon_name="layers")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ভিডিও", "প্ল্যাটফর্ম", "প্রোফাইল", "স্ট্যাটাস"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(160)
        queue_card.add(self.table)
        self.queue_hint = widgets.label(
            "এখনো কিছু পাবলিশ করা হয়নি — উপরে বেছে ‘পাবলিশ শুরু করুন’ চাপুন।", "muted", wrap=True)
        queue_card.add(self.queue_hint)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.publish_btn = widgets.button("পাবলিশ শুরু করুন", "primary", "upload",
                                          on_click=self.on_publish)
        row.addWidget(self.publish_btn)
        self.cancel_btn = widgets.button("বাতিল", "danger", "stop", on_click=self.on_cancel)
        self.cancel_btn.setEnabled(False)
        row.addWidget(self.cancel_btn)
        row.addStretch(1)
        queue_card.add_layout(row)
        left.addWidget(queue_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        summary_card = widgets.Card(title="সারসংক্ষেপ", icon_name="info")
        self.summary = widgets.label("", "muted", wrap=True)
        summary_card.add(self.summary)
        right.addWidget(summary_card)

        warn_card = widgets.Card(title="নিরাপত্তা", icon_name="alert")
        warn_card.add(widgets.label(
            "• প্রতিদিনের আপলোড লিমিট মেনে চলুন — একাউন্ট সুরক্ষার জন্যই।\n"
            "• ডিলে বেশি রাখলে স্প্যাম ফ্ল্যাগ কম হয়।\n"
            "• কনটেন্ট আপনার নিজের হতে হবে; কারও কপিরাইট করা ভিডিও আপলোড করবেন না।\n"
            "• প্ল্যাটফর্মের নিয়ম মানা এবং অটোমেশন ব্যবহারের দায়িত্ব আপনার নিজের।",
            "muted", wrap=True))
        right.addWidget(warn_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("accounts")))

        self._loading = False
        self.studio.project_changed.connect(lambda _p: self.refresh_videos())
        self.studio.render_done.connect(lambda _r: self.refresh_videos())
        self.refresh_profiles()
        self.refresh_videos()
        self._sync()

    # -------------------------------------------------------------- helpers
    def _set(self, key, value):
        self.studio.set_setting("upload", key, bool(value))
        self._sync()

    def _save(self):
        if self._loading:
            return
        self.studio.set_setting("upload", "visibility", self.visibility.currentData())
        self.studio.set_setting("upload", "delay_min", self.delay_min.value())
        self.studio.set_setting("upload", "delay_max", self.delay_max.value())
        self._sync()

    def _sync(self):
        upload = self.studio.get("upload") or {}
        for index in range(self.visibility.count()):
            if self.visibility.itemData(index) == upload.get("visibility", "public"):
                self.visibility.setCurrentIndex(index)
                break
        self.delay_min.setValue(int(upload.get("delay_min") or 30))
        self.delay_max.setValue(int(upload.get("delay_max") or 90))
        platforms = upload.get("platforms") or ["youtube", "facebook"]
        self.yt_check.setChecked("youtube" in platforms)
        self.fb_check.setChecked("facebook" in platforms)
        limit = upload.get("daily_limit", 6)
        left_today = limits_lib.remaining(limit)
        self.summary.setText(
            f"আজ আপলোড হয়েছে: {limits_lib.today_count()} · বাকি: "
            f"{'সীমা নেই' if left_today > 900 else left_today}\n"
            f"ডিলে: {self.delay_min.value()}–{self.delay_max.value()} সেকেন্ড · "
            f"ভিজিবিলিটি: {self.visibility.currentText()}\n"
            f"ড্রাই-রান: {'চালু' if self.dry_switch.toggle.isChecked() else 'বন্ধ'}")

    def refresh_profiles(self):
        self.profile_list.clear()
        from paths import profiles_dir
        base = profiles_dir()
        names = []
        if os.path.isdir(base):
            names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name == names[0] else Qt.Unchecked)
            self.profile_list.addItem(item)
        self.profile_list.setVisible(bool(names))
        self.profile_empty.setVisible(not names)
        if not names:
            self.studio.log("কোনো প্রোফাইল নেই — ধাপ ৬-এ যোগ করুন", "warn")

    def refresh_videos(self):
        self.video_list.clear()
        from core import projects as projects_lib
        from paths import outputs_dir

        entries = []
        seen = set()
        for project in projects_lib.list_all():
            path = project.get("video_path")
            if path and os.path.exists(path) and path not in seen:
                seen.add(path)
                entries.append((path, project.get("title") or os.path.basename(path)))
        folder = outputs_dir()
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder), reverse=True):
                if name.lower().endswith(".mp4"):
                    path = os.path.join(folder, name)
                    if path not in seen:
                        seen.add(path)
                        entries.append((path, name))
        for path, title in entries[:40]:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if self.video_list.count() == 0 else Qt.Unchecked)
            self.video_list.addItem(item)
        self.video_list.setVisible(bool(entries))
        self.video_empty.setVisible(not entries)
        if not entries:
            self.studio.log("কোনো ভিডিও নেই — আগে ধাপ ৫-এ রেন্ডার করুন", "warn")

    def selected_profiles(self):
        result = []
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            if item.checkState() == Qt.Checked:
                result.append(item.text())
        return result

    def selected_videos(self):
        result = []
        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            if item.checkState() == Qt.Checked:
                result.append((item.data(Qt.UserRole), item.text()))
        return result

    def selected_platforms(self):
        platforms = []
        if self.yt_check.isChecked():
            platforms.append("youtube")
        if self.fb_check.isChecked():
            platforms.append("facebook")
        return platforms

    def _fill_row(self, row_index, values):
        while self.table.rowCount() <= row_index:
            self.table.insertRow(self.table.rowCount())
        for column, value in enumerate(values):
            self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.queue_hint.setVisible(self.table.rowCount() == 0)
        self.table.scrollToBottom()

    # --------------------------------------------------------------- actions
    def on_cancel(self):
        self.studio.queue.cancel_current()
        self.studio.log("আপলোড বাতিলের অনুরোধ", "warn")

    def on_publish(self):
        studio = self.studio
        platforms = self.selected_platforms()
        profiles = self.selected_profiles()
        videos = self.selected_videos()
        if not platforms:
            studio.log("অন্তত একটি প্ল্যাটফর্ম বেছে নিন", "warn")
            return
        if not profiles:
            studio.log("অন্তত একটি প্রোফাইল বেছে নিন", "warn")
            return
        if not videos:
            studio.log("অন্তত একটি ভিডিও বেছে নিন", "warn")
            return

        upload = studio.get("upload") or {}
        visibility = self.visibility.currentData()
        made_for_kids = bool(self.kids_switch.toggle.isChecked())
        dry_run = bool(self.dry_switch.toggle.isChecked())
        headless = bool(upload.get("headless", False))
        delay = (self.delay_min.value(), max(self.delay_min.value(), self.delay_max.value()))
        limit = int(upload.get("daily_limit") or 6)
        studio.set_setting("upload", "platforms", platforms)

        self.publish_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.table.setRowCount(0)
        self.queue_hint.setVisible(False)

        script = studio.script or {}
        title = (script.get("title") or "").strip() or "নতুন ভিডিও"
        description = (script.get("description") or script.get("body") or "")[:4000]
        tags = script.get("tags") or []

        total = len(videos) * len(platforms) * len(profiles)

        def work(progress, log, cancel):
            from core.upload import facebook, youtube
            done = 0
            results = []
            remaining = limits_lib.remaining(limit)
            for video_path, video_title in videos:
                for platform in platforms:
                    module = youtube if platform == "youtube" else facebook
                    for profile in profiles:
                        if cancel():
                            return {"kind": "publish", "results": results, "cancelled": True}
                        if not dry_run and remaining <= 0:
                            log(f"আজকের লিমিট শেষ ({limit}) — বাকিগুলো বাদ দেওয়া হলো", "warn")
                            done += 1
                            continue
                        log(f"আপলোড: {os.path.basename(video_path)} → {platform} ({profile})")
                        progress(done / max(1, total), f"{done + 1}/{total} আপলোড")
                        entry = {"video": video_path, "platform": platform, "profile": profile}
                        try:
                            result = module.upload(
                                video_path, video_title or title, description, tags, profile,
                                headless=headless, visibility=visibility,
                                made_for_kids=made_for_kids, dry_run=dry_run,
                                on_status=lambda msg: log(msg, "dim"), cancel=cancel)
                            entry.update({"status": "done", "url": result.get("url", ""),
                                          "message": result.get("message", "")})
                            if not dry_run:
                                limits_lib.record(platform, profile, video_path, "done",
                                                  result.get("url", ""))
                                remaining -= 1
                            log("সফল: " + result.get("message", "সম্পন্ন"), "ok")
                        except Exception as exc:
                            entry.update({"status": "failed", "message": str(exc)})
                            limits_lib.record(platform, profile, video_path, "failed",
                                              "", str(exc))
                            log(f"ব্যর্থ ({platform}/{profile}): {exc}", "error")
                        results.append(entry)
                        done += 1
                        if done < total and not cancel():
                            wait = random.uniform(*delay)
                            log(f"পরের আপলোডের আগে {wait:.0f} সেকেন্ড অপেক্ষা", "dim")
                            slept = 0.0
                            while slept < wait and not cancel():
                                time.sleep(0.5)
                                slept += 0.5
            progress(1.0, "আপলোড ধাপ শেষ")
            return {"kind": "publish", "results": results}

        studio.submit("পাবলিশ", work)

    def show_result(self, result):
        self.publish_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        rows = result.get("results") or []
        for entry in rows:
            self._fill_row(self.table.rowCount(), [
                os.path.basename(entry.get("video", "")),
                entry.get("platform", ""),
                entry.get("profile", ""),
                {"done": "সফল", "failed": "ব্যর্থ"}.get(entry.get("status"), entry.get("status", "")),
            ])
        ok = len([r for r in rows if r.get("status") == "done"])
        failed = len([r for r in rows if r.get("status") == "failed"])
        self.queue_hint.setVisible(self.table.rowCount() == 0)
        self.studio.log(f"আপলোড শেষ — সফল: {ok}, ব্যর্থ: {failed}", "ok" if not failed else "warn")
        self._sync()
        self.refresh_videos()
