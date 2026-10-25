"""Dashboard: stats, quick start and recent projects."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from core import projects as projects_lib
from ui import theme, widgets


class DashboardPage(QWidget):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.addWidget(widgets.label("ড্যাশবোর্ড", "h1"))
        title_box.addWidget(widgets.label(
            "এক জায়গা থেকে স্ক্রিপ্ট, ভিডিও আর আপলোড — পুরো কাজের হিসাব।", "muted"))
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(widgets.button("নতুন ভিডিও বানান", "primary", "plus",
                                        on_click=lambda: self._start_new()))
        outer.addLayout(header)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.stat_projects = widgets.StatCard("প্রজেক্ট", "0", "projects", theme.ACCENT_HOVER)
        self.stat_videos = widgets.StatCard("ভিডিও তৈরি", "0", "film", theme.BLUE)
        self.stat_uploads = widgets.StatCard("আপলোড সফল", "0", "upload", theme.SUCCESS)
        self.stat_minutes = widgets.StatCard("মোট মিনিট", "0", "clock", theme.WARN)
        for card in (self.stat_projects, self.stat_videos, self.stat_uploads, self.stat_minutes):
            stats_row.addWidget(card)
        outer.addLayout(stats_row)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(16)

        steps_card = widgets.Card(title="কীভাবে শুরু করবেন", icon_name="info")
        steps = [
            ("১", "আইডিয়া বা নিজের স্ক্রিপ্ট দিন", "AI, টেমপ্লেট বা নিজের লেখা — তিনভাবেই চলে", "script"),
            ("২", "স্টাইল ও ফ্রেম বাছুন", "৯:১৬ শর্টস, ১৬:৯ ইউটিউব বা স্কয়ার", "visuals"),
            ("৩", "ভয়েস শুনে নিন", "বাংলা/ইংরেজি, পুরুষ/মহিলা, বাংলাদেশ/ভারত", "voice"),
            ("৪", "মিউজিক ও সাবটাইটেল", "রয়্যালটি-ফ্রি মিউজিক, সিঙ্ক করা ক্যাপশন", "audio"),
            ("৫", "ভিডিও তৈরি করুন", "এক ক্লিকে রেন্ডার, এখানেই প্রিভিউ", "preview"),
            ("৬", "একাউন্ট লগইন", "একবার লগইন — সেশন সেভ থাকবে", "accounts"),
            ("৭", "YouTube ও Facebook-এ পাবলিশ", "ড্রাই-রান দিয়ে আগে পরীক্ষা করে নিন", "publish"),
        ]
        grid = QGridLayout()
        grid.setSpacing(10)
        for index, (number, title, hint, target) in enumerate(steps):
            tile = widgets.OptionTile(title, hint, icon_name="chevron_right",
                                      badge=f"ধাপ {number}", badge_kind="chipAccent", compact=True)
            tile.clicked.connect(lambda t=target: self.studio.navigate.emit(t))
            grid.addWidget(tile, index // 2, index % 2)
        steps_card.add_layout(grid)
        left.addWidget(steps_card)

        recent_card = widgets.Card(title="সাম্প্রতিক প্রজেক্ট", icon_name="projects")
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(8)
        recent_card.add_layout(self.recent_box)
        left.addWidget(recent_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        quick_card = widgets.Card(title="দ্রুত কাজ", icon_name="sparkles")
        quick_card.add(widgets.button("টেমপ্লেট থেকে নতুন ভিডিও", "ghost", "content",
                                      on_click=lambda: self.studio.navigate.emit("content")))
        quick_card.add(widgets.button("প্রজেক্ট সমূহ দেখুন", "ghost", "folder_open",
                                      on_click=lambda: self.studio.navigate.emit("projects")))
        quick_card.add(widgets.button("টুলস ও সেটআপ", "ghost", "tools",
                                      on_click=lambda: self.studio.navigate.emit("tools")))
        quick_card.add(widgets.button("সেটিংস", "ghost", "settings",
                                      on_click=lambda: self.studio.navigate.emit("settings")))
        right.addWidget(quick_card)

        self.queue_card = widgets.Card(title="চলমান কাজ", icon_name="clock")
        self.queue_label = widgets.label("কোনো কাজ চলছে না", "muted", wrap=True)
        self.queue_card.add(self.queue_label)
        right.addWidget(self.queue_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        self.refresh()
        self.studio.render_done.connect(lambda _r: self.refresh())
        self.studio.project_changed.connect(lambda _p: self.refresh())
        self.studio.queue.changed.connect(self.refresh_queue)

    def _start_new(self):
        self.studio.set_script({})
        self.studio.project = None
        self.studio.navigate.emit("script")

    def refresh_queue(self):
        queue = self.studio.queue
        if queue.busy():
            self.queue_label.setText("একটি কাজ চলছে: " + (queue.current.name if queue.current else ""))
        elif queue.pending():
            self.queue_label.setText(f"অপেক্ষমাণ কাজ: {queue.pending()}টি")
        else:
            self.queue_label.setText("কোনো কাজ চলছে না")

    def refresh(self):
        stats = projects_lib.stats()
        self.stat_projects.set_value(stats["projects"])
        self.stat_videos.set_value(stats["videos"])
        self.stat_uploads.set_value(stats["uploads"])
        self.stat_minutes.set_value(stats["minutes"])
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        items = projects_lib.list_all()[:5]
        if not items:
            self.recent_box.addWidget(widgets.empty_state(
                "এখনো কোনো প্রজেক্ট নেই", "উপরের ‘নতুন ভিডিও বানান’ চাপুন", "projects"))
        for project in items:
            when = time.strftime("%d %b, %H:%M", time.localtime(project.get("updated") or 0))
            uploads = project.get("uploads") or {}
            uploaded = len([u for u in uploads.values() if u.get("status") == "done"])
            badge = f"{uploaded} আপলোড" if uploaded else ""
            tile = widgets.OptionTile(
                project.get("title") or "প্রজেক্ট",
                f"{when} · {int(project.get('duration') or 0)} সেকেন্ড",
                icon_name="film", badge=badge, badge_kind="chipAccent", compact=True)
            tile.clicked.connect(lambda p=project: self._open_project(p))
            self.recent_box.addWidget(tile)

    def _open_project(self, project):
        self.studio.project = project
        self.studio.set_script(project.get("script") or {}, from_project=project)
        self.studio.project_changed.emit(project)
        self.studio.navigate.emit("preview" if project.get("video_path") else "script")
