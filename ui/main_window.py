"""Main window: sidebar, topbar, wizard pages, log panel and notifications."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QScrollArea, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget)

from ui import icons, theme, widgets
from ui.components import wizard
from ui.pages.accounts import AccountsPage
from ui.pages.audio import AudioPage
from ui.pages.content import ContentPage
from ui.pages.dashboard import DashboardPage
from ui.pages.preview import PreviewPage
from ui.pages.projects import ProjectsPage
from ui.pages.publish import PublishPage
from ui.pages.script import ScriptPage
from ui.pages.settings import SettingsPage
from ui.pages.tools import ToolsPage
from ui.pages.visuals import VisualsPage
from ui.pages.voice import VoicePage

VERSION = "1.0"
NAV_ITEMS = [
    ("dashboard", "ড্যাশবোর্ড", "dashboard"),
    ("content", "কন্টেন্ট", "content"),
    ("script", "ভিডিও তৈরি করুন", "video"),
    ("projects", "প্রজেক্ট সমূহ", "projects"),
    ("tools", "টুলস", "tools"),
    ("settings", "সেটিংস", "settings"),
]
WIZARD_PAGES = ["script", "visuals", "voice", "audio", "preview", "accounts", "publish"]
PAGE_TITLES = {
    "dashboard": "ড্যাশবোর্ড",
    "content": "কন্টেন্ট লাইব্রেরি",
    "projects": "প্রজেক্ট সমূহ",
    "tools": "টুলস",
    "settings": "সেটিংস",
}


class MainWindow(QMainWindow):
    def __init__(self, studio):
        super().__init__()
        self.studio = studio
        self.setWindowTitle("YTFB Studio — ভিডিও অটোমেশন")
        self.setWindowIcon(icons.app_icon())
        self.resize(1360, 880)
        self.setMinimumSize(1120, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(18, 16, 18, 12)
        right.setSpacing(12)
        right.addWidget(self._build_topbar())
        self.step_strip = wizard.StepStrip()
        self.step_strip.go.connect(self.goto_step)
        right.addWidget(self.step_strip)

        self.stack = QStackedWidget()
        self.pages = {}
        self.scroll_areas = []
        self.area_for = {}
        self._register_pages()
        right.addWidget(self.stack, 1)
        right.addWidget(self._build_bottom())
        root.addLayout(right, 1)

        self._wire()
        self.navigate("dashboard")
        self._install_tray()

    # ------------------------------------------------------------- building
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(6)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icons.app_icon().pixmap(QSize(34, 34)))
        logo_row.addWidget(logo)
        name_box = QVBoxLayout()
        name_box.setSpacing(1)
        name_box.addWidget(widgets.label("YTFB Studio", "cardTitle"))
        name_box.addWidget(widgets.label("ভিডিও অটোমেশন", "muted"))
        logo_row.addLayout(name_box)
        logo_row.addStretch(1)
        layout.addLayout(logo_row)
        layout.addSpacing(6)
        layout.addWidget(widgets.label(f"সংস্করণ {VERSION}", "chip"))
        layout.addSpacing(10)

        self.nav_buttons = {}
        for key, title, icon_name in NAV_ITEMS:
            button = QPushButton("  " + title)
            button.setProperty("nav", "true")
            button.setIcon(icons.icon(icon_name, theme.TEXT_DIM, 19))
            button.setIconSize(QSize(19, 19))
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(42)
            button.clicked.connect(lambda _=False, k=key: self._nav_clicked(k))
            layout.addWidget(button)
            self.nav_buttons[key] = button

        layout.addStretch(1)
        layout.addWidget(self._divider())
        ring_row = QHBoxLayout()
        ring_row.setSpacing(10)
        self.ring = widgets.ProgressRing(size=62)
        ring_row.addWidget(self.ring)
        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(widgets.label("কাজের অবস্থা", "muted"))
        self.pending_label = widgets.label("প্রস্তুত", "dim", wrap=True)
        info.addWidget(self.pending_label)
        ring_row.addLayout(info, 1)
        layout.addLayout(ring_row)
        return sidebar

    def _divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.breadcrumb = widgets.label("ড্যাশবোর্ড", "h2")
        self.subtitle = widgets.label("", "muted")
        title_box.addWidget(self.breadcrumb)
        title_box.addWidget(self.subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)

        layout.addWidget(widgets.button("নতুন প্রজেক্ট", "ghost", "plus", on_click=self.new_project))
        self.status_pill = widgets.label("প্রস্তুত", "statusPill")
        layout.addWidget(self.status_pill)
        layout.addWidget(widgets.button("ভিডিও তৈরি করুন", "primary", "play",
                                        on_click=lambda: self.navigate("script")))
        return bar

    def _build_bottom(self):
        panel = QFrame()
        panel.setObjectName("logPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(widgets.label("লগ", "cardTitle"))
        self.progress = widgets.progress_bar(0, height=8)
        top.addWidget(self.progress, 1)
        self.cancel_btn = widgets.button("বাতিল", "danger", "stop", on_click=self.cancel_current)
        self.cancel_btn.setEnabled(False)
        top.addWidget(self.cancel_btn)
        top.addWidget(widgets.button("লগ সেভ", "ghost", "save", on_click=self.save_log))
        top.addWidget(widgets.button("ক্লিয়ার", "ghost", "trash", on_click=self.clear_log))
        layout.addLayout(top)

        self.console = widgets.LogConsole(height=118)
        layout.addWidget(self.console)
        return panel

    def _register_pages(self):
        self.script_page = ScriptPage(self.studio)
        self.visuals_page = VisualsPage(self.studio)
        self.voice_page = VoicePage(self.studio)
        self.audio_page = AudioPage(self.studio)
        self.preview_page = PreviewPage(self.studio)
        self.accounts_page = AccountsPage(self.studio)
        self.publish_page = PublishPage(self.studio)
        self.dashboard_page = DashboardPage(self.studio)
        self.content_page = ContentPage(self.studio)
        self.projects_page = ProjectsPage(self.studio)
        self.tools_page = ToolsPage(self.studio)
        self.settings_page = SettingsPage(self.studio)

        self.pages = {
            "dashboard": self.dashboard_page,
            "content": self.content_page,
            "script": self.script_page,
            "visuals": self.visuals_page,
            "voice": self.voice_page,
            "audio": self.audio_page,
            "preview": self.preview_page,
            "accounts": self.accounts_page,
            "publish": self.publish_page,
            "projects": self.projects_page,
            "tools": self.tools_page,
            "settings": self.settings_page,
        }
        for key, page in self.pages.items():
            area = self._scrolled(page)
            self.area_for[page] = area
            self.stack.addWidget(area)

    def _scrolled(self, page):
        """Wrap a page in a scroll area so content never gets squeezed."""
        page.setObjectName("page")
        page.setAttribute(Qt.WA_StyledBackground, True)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setViewportMargins(0, 0, 6, 0)
        area.viewport().setObjectName("viewport")
        area.viewport().setAttribute(Qt.WA_StyledBackground, True)
        area.setWidget(page)
        area.page = page
        self.scroll_areas.append(area)
        return area

    def current_page(self):
        widget = self.stack.currentWidget()
        return getattr(widget, "page", widget)

    def _install_tray(self):
        self.tray = None
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = QSystemTrayIcon(icons.app_icon(), self)
                self.tray.setToolTip("YTFB Studio")
                self.tray.show()
        except Exception:
            self.tray = None

    # ---------------------------------------------------------------- wiring
    def _wire(self):
        self.studio.navigate.connect(self.navigate)
        self.studio.status.connect(self.set_status)
        self.studio.logged.connect(self.on_log)
        queue = self.studio.queue
        queue.progressed.connect(self.on_progress)
        queue.started.connect(self.on_job_started)
        queue.finished.connect(self.on_job_finished)
        queue.failed.connect(self.on_job_failed)
        queue.changed.connect(self.on_queue_changed)

    def _nav_clicked(self, key):
        if key == "script":
            self.navigate("script")
        else:
            self.navigate(key)

    # ------------------------------------------------------------ navigation
    def navigate(self, key):
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(self.area_for.get(page, page))
        is_wizard = key in WIZARD_PAGES
        self.step_strip.setVisible(is_wizard)
        if is_wizard:
            self.step_strip.set_step(WIZARD_PAGES.index(key))
        title = PAGE_TITLES.get(key) or f"{wizard.STEP_TITLES[WIZARD_PAGES.index(key)]} — ধাপ {WIZARD_PAGES.index(key) + 1}"
        self.breadcrumb.setText(title)
        self.subtitle.setText("ভিডিও তৈরি করুন" if is_wizard else "")
        for name, button in self.nav_buttons.items():
            active = name == key or (name == "script" and is_wizard)
            button.setProperty("active", "true" if active else "false")
            button.setIcon(icons.icon(
                dict((k, i) for k, _t, i in NAV_ITEMS)[name],
                theme.ACCENT_HOVER if active else theme.TEXT_DIM, 19))
            button.style().unpolish(button)
            button.style().polish(button)
        if key == "projects":
            self.projects_page.refresh()
        elif key == "accounts":
            self.accounts_page.refresh()
        elif key == "publish":
            self.publish_page.refresh_profiles()
            self.publish_page.refresh_videos()
        elif key == "dashboard":
            self.dashboard_page.refresh()

    def goto_step(self, index):
        index = max(0, min(len(WIZARD_PAGES) - 1, int(index)))
        self.navigate(WIZARD_PAGES[index])

    def new_project(self):
        self.studio.set_script({})
        self.studio.project = None
        self.studio.last_render = {}
        self.navigate("script")
        self.toast("নতুন প্রজেক্ট শুরু হয়েছে", "info")

    # ------------------------------------------------------------- job wiring
    def on_job_started(self, name):
        self.cancel_btn.setEnabled(True)
        self.set_status("চলছে: " + name)

    def on_progress(self, ratio, message):
        self.progress.setValue(int(max(0.0, min(1.0, ratio)) * 1000))
        self.ring.set_value(ratio)
        if message:
            self.status_pill.setText(message[:60])
        page = self.current_page()
        if hasattr(page, "set_progress"):
            page.set_progress(ratio, message)

    def on_log(self, message, level="info"):
        self.console.append(message, level)

    def on_job_finished(self, name, result):
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(1000)
        self.ring.set_value(1.0)
        QTimer.singleShot(1500, lambda: self.progress.setValue(0))
        kind = result.get("kind")
        self._dispatch(kind, result)
        if (self.studio.get("ui") or {}).get("notify_on_done", True):
            self.notify(f"{name} সম্পন্ন হয়েছে")
        self.on_queue_changed()

    def on_job_failed(self, name, message):
        self.cancel_btn.setEnabled(False)
        self.set_status("ব্যর্থ: " + message)
        self.console.append(f"[{name}] {message}", "error")
        if (self.studio.get("ui") or {}).get("notify_on_done", True):
            self.notify(f"{name} ব্যর্থ: {message}", error=True)
        self.on_queue_changed()
        page = self.current_page()
        if page is self.preview_page:
            self.preview_page.render_btn.setEnabled(True)
            self.preview_page.cancel_btn.setEnabled(False)
        if page is self.publish_page:
            self.publish_page.publish_btn.setEnabled(True)
            self.publish_page.cancel_btn.setEnabled(False)
        if page is self.accounts_page:
            self.accounts_page.login_btn.setEnabled(True)

    def on_queue_changed(self):
        queue = self.studio.queue
        if queue.busy():
            self.pending_label.setText("চলছে…")
        elif queue.pending():
            self.pending_label.setText(f"অপেক্ষায় {queue.pending()}টি")
        else:
            self.pending_label.setText("প্রস্তুত")

    def _dispatch(self, kind, result):
        if kind == "script":
            script = result.get("script") or {}
            self.script_page._apply(script)
            if not result.get("cancelled"):
                self.navigate("visuals")
        elif kind == "preview":
            image = result.get("image")
            if image:
                self.navigate("visuals")
                self.visuals_page.phone.set_image(image)
                self.toast("প্রিভিউ তৈরি হয়েছে", "ok")
        elif kind == "voice_preview":
            self.voice_page.play_preview(result.get("audio") or {})
        elif kind == "scene_visual":
            self.preview_page.set_scene_visual(result)
        elif kind == "storyboard":
            self.navigate("preview")
            self.preview_page.set_storyboard(result.get("items") or [])
            self.toast("দৃশ্যের ছবি প্রস্তুত", "ok")
        elif kind == "ai_prompts":
            self.navigate("preview")
            self.studio.set_script(result.get("script") or {})
            self.preview_page.refresh_all()
            self.toast("AI দিয়ে সব দৃশ্যের প্রম্পট তৈরি হয়েছে", "ok")
        elif kind == "render":
            self.navigate("preview")
            self.preview_page.show_result(result)
            board = result.get("storyboard") or []
            if board:
                self.preview_page.set_board(board)
            self.toast(f"ভিডিও তৈরি — {result.get('seconds', 0)} সেকেন্ডে", "ok")
        elif kind in ("login", "session_test"):
            self.accounts_page.show_result(result)
        elif kind == "publish":
            self.publish_page.show_result(result)
        elif kind == "music_ready":
            self.audio_page.refresh_music()
            self.toast("মিউজিক লাইব্রেরি প্রস্তুত", "ok")
        elif kind == "fonts":
            self.toast("বাংলা ফন্ট সেটআপ শেষ", "ok")
            self.tools_page.refresh_info()
        elif kind in ("browser", "browser_verify"):
            self.tools_page.refresh_info()
            payload = result.get("result") or {}
            self.toast("ব্রাউজার প্রস্তুত" if payload.get("ok") else "ব্রাউজার সমস্যা",
                       "ok" if payload.get("ok") else "warn")

    # ------------------------------------------------------------- utilities
    def set_status(self, message):
        self.status_pill.setText(str(message)[:70])

    def cancel_current(self):
        self.studio.queue.cancel_current()
        self.console.append("বাতিলের অনুরোধ পাঠানো হয়েছে", "warn")

    def clear_log(self):
        self.console.clear()

    def save_log(self):
        try:
            from paths import logs_dir
            path = os.path.join(logs_dir(), f"session_{time.strftime('%Y%m%d_%H%M%S')}.log")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.console.text())
            self.toast("লগ সেভ হয়েছে: " + os.path.basename(path), "ok")
        except Exception as exc:
            self.toast("লগ সেভ হয়নি: " + str(exc), "error")

    def toast(self, message, kind="info"):
        popup = widgets.Toast(self, message, kind)
        popup.place(self.width() / 2 + 116, self.height() - 210)

    def notify(self, message, error=False):
        if self.tray:
            try:
                self.tray.showMessage("YTFB Studio", message,
                                      QSystemTrayIcon.Warning if error else QSystemTrayIcon.Information,
                                      5000)
                return
            except Exception:
                pass
        self.toast(message, "error" if error else "ok")

    def show_page_title(self, key):
        return PAGE_TITLES.get(key, key)

    def closeEvent(self, event):
        if self.studio.queue.busy():
            box = QMessageBox(self)
            box.setWindowTitle("কাজ চলছে")
            box.setText("একটি কাজ এখনো চলছে। বন্ধ করলে সেটি থেমে যাবে। বন্ধ করবেন?")
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            if box.exec() != QMessageBox.Yes:
                event.ignore()
                return
            self.studio.queue.cancel_all()
        try:
            if self.tray:
                self.tray.hide()
        except Exception:
            pass
        event.accept()
