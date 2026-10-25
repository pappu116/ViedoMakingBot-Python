"""Projects list with thumbnails, status and re-use actions."""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from core import projects as projects_lib
from ui import widgets


class ProjectsPage(QWidget):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.addWidget(widgets.label("প্রজেক্ট সমূহ", "h1"))
        title_box.addWidget(widgets.label("আগের সব কাজ — আবার ব্যবহার বা রি-আপলোড করুন।", "muted"))
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(widgets.button("রিফ্রেশ", "ghost", "refresh", on_click=self.refresh))
        header.addWidget(widgets.button("আউটপুট ফোল্ডার", "ghost", "folder_open",
                                        on_click=self.open_output))
        outer.addLayout(header)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(12)
        container = QWidget()
        container.setLayout(self.list_box)
        outer.addWidget(container, 1)
        self.refresh()
        self.studio.render_done.connect(lambda _r: self.refresh())

    def refresh(self):
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        items = projects_lib.list_all()
        if not items:
            self.list_box.addWidget(widgets.empty_state(
                "এখনো কোনো প্রজেক্ট নেই", "ধাপ ১ থেকে শুরু করুন", "projects"))
            return
        for project in items:
            self.list_box.addWidget(self._row(project))
        self.list_box.addStretch(1)

    def _row(self, project):
        card = widgets.Card()
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(widgets.thumbnail_label(project.get("thumbnail"), 96, 170))

        info = QVBoxLayout()
        info.setSpacing(6)
        info.addWidget(widgets.label(project.get("title") or "প্রজেক্ট", "h2"))
        when = time.strftime("%d %b %Y, %H:%M", time.localtime(project.get("updated") or 0))
        duration = int(project.get("duration") or 0)
        info.addWidget(widgets.label(f"{when} · {duration} সেকেন্ড", "muted"))

        script = project.get("script") or {}
        scenes = len(script.get("scenes") or [])
        engine = (project.get("settings") or {}).get("voice_engine", "auto")
        info.addWidget(widgets.label(
            f"দৃশ্য: {scenes} · স্টাইল: {script.get('style', '—')} · কণ্ঠ: {engine}", "muted"))

        uploads = project.get("uploads") or {}
        if uploads:
            chips = QHBoxLayout()
            chips.setSpacing(8)
            for platform, data in uploads.items():
                chips.addWidget(widgets.label(f"{platform}: {data.get('status')}", "chip"))
            chips.addStretch(1)
            info.addLayout(chips)
        info.addStretch(1)
        row.addLayout(info, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        video = project.get("video_path")
        has_video = bool(video and os.path.exists(video))
        play_button = widgets.button("ভিডিও চালান", "ghost", "play",
                                     on_click=lambda v=video: self._play(v))
        play_button.setEnabled(has_video)
        buttons.addWidget(play_button)
        buttons.addWidget(widgets.button("স্ক্রিপ্ট খুলুন", "ghost", "content",
                                         on_click=lambda p=project: self._open(p)))
        buttons.addWidget(widgets.button("আবার রেন্ডার", "ghost", "refresh",
                                         on_click=lambda p=project: self._rerender(p)))
        buttons.addWidget(widgets.button("আপলোড", "ghost", "upload",
                                         on_click=lambda p=project: self._publish(p)))
        buttons.addWidget(widgets.button("মুছুন", "danger", "trash",
                                         on_click=lambda p=project: self._delete(p)))
        row.addLayout(buttons)
        card.add_layout(row)
        return card

    # -------------------------------------------------------------- actions
    def _play(self, path):
        if path and os.path.exists(path):
            _open_path(path)
        else:
            self.studio.log("এই প্রজেক্টের ভিডিও ফাইল নেই", "warn")

    def _open(self, project):
        self.studio.project = project
        self.studio.set_script(project.get("script") or {}, from_project=project)
        self.studio.navigate.emit("script")

    def _rerender(self, project):
        self.studio.project = project
        self.studio.set_script(project.get("script") or {}, from_project=project)
        self.studio.navigate.emit("preview")

    def _publish(self, project):
        self.studio.project = project
        script = project.get("script") or {}
        if script:
            self.studio.set_script(script, from_project=project)
        self.studio.navigate.emit("publish")

    def _delete(self, project):
        box = QMessageBox(self)
        box.setWindowTitle("মুছে ফেলবেন?")
        box.setText("প্রজেক্টটি তালিকা থেকে মুছে ফেলা হবে (ভিডিও ফাইল থাকবে)।")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        if box.exec() == QMessageBox.Yes:
            projects_lib.delete(project["id"])
            self.studio.log("প্রজেক্ট মুছে ফেলা হয়েছে", "warn")
            self.refresh()

    def open_output(self):
        from paths import outputs_dir
        _open_path(outputs_dir())


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
