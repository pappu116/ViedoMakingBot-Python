"""Step 6 — accounts: create profiles and log in without leaving the app."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget)

from paths import profiles_dir
from ui import theme, widgets
from ui.components import wizard

PLATFORMS = [("youtube", "YouTube", "youtube"), ("facebook", "Facebook", "facebook")]


class AccountsPage(QWidget):
    step_index = 5

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.platform = "youtube"
        self.selected_profile = ""
        self.profile_tiles = {}
        self.platform_buttons = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)
        outer.addWidget(wizard.StepHeader(
            self.step_index, "একাউন্ট যোগ করুন",
            "একবার লগইন করলেই সেশন সেভ হয়ে যাবে — পরে আর লগইন লাগবে না।"))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        platform_card = widgets.Card(title="প্ল্যাটফর্ম", icon_name="globe")
        row = QHBoxLayout()
        row.setSpacing(10)
        for key, title, icon_name in PLATFORMS:
            pill = QPushButton(title)
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            pill.setMinimumHeight(40)
            pill.clicked.connect(lambda _=False, k=key: self.set_platform(k))
            row.addWidget(pill)
            self.platform_buttons[key] = pill
        row.addStretch(1)
        platform_card.add_layout(row)
        left.addWidget(platform_card)

        profiles_card = widgets.Card(title="প্রোফাইল", icon_name="user",
                                     subtitle="প্রতিটি প্রোফাইল = আলাদা একাউন্ট")
        add_row = QHBoxLayout()
        add_row.setSpacing(10)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("acc1")
        add_row.addWidget(self.name_input, 1)
        add_row.addWidget(widgets.button("যোগ করুন", "ghost", "plus", on_click=self.on_add))
        profiles_card.add_layout(add_row)

        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(8)
        profiles_card.add_layout(self.list_box)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.login_btn = widgets.button("লগইন শুরু করুন", "primary", "external",
                                        on_click=self.on_login)
        actions.addWidget(self.login_btn)
        actions.addWidget(widgets.button("সেশন টেস্ট", "ghost", "check", on_click=self.on_test))
        actions.addWidget(widgets.button("রিফ্রেশ", "ghost", "refresh", on_click=self.refresh))
        actions.addStretch(1)
        profiles_card.add_layout(actions)
        left.addWidget(profiles_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(16)
        help_card = widgets.Card(title="কীভাবে লগইন করবেন", icon_name="info")
        help_card.add(widgets.label(
            "১. প্রোফাইলের নাম লিখে যোগ করুন (যেমন acc1)।\n"
            "২. প্ল্যাটফর্ম বেছে নিন।\n"
            "৩. ‘লগইন শুরু করুন’ চাপুন — ব্রাউজার খুলবে।\n"
            "৪. ব্রাউজারে নিজের একাউন্টে লগইন করুন।\n"
            "৫. অ্যাপ নিজেই ধরে ফেলবে এবং সেশন সেভ করবে।\n\n"
            "এরপর ‘সেশন টেস্ট’ দিয়ে যাচাই করে নিন।", "muted", wrap=True))
        right.addWidget(help_card)

        status_card = widgets.Card(title="সেশন অবস্থা", icon_name="key")
        self.status_label = widgets.label("—", "muted", wrap=True)
        status_card.add(self.status_label)
        right.addWidget(status_card)
        right.addStretch(1)
        columns.addLayout(right, 2)

        outer.addLayout(columns)
        outer.addWidget(wizard.back_next(on_back=lambda: self.studio.navigate.emit("preview"),
                                         on_next=lambda: self.studio.navigate.emit("publish"),
                                         next_text="পাবলিশ ধাপে যান"))

        self.set_platform("youtube")
        self.refresh()

    # -------------------------------------------------------------- helpers
    def set_platform(self, key):
        self.platform = key
        for name, pill in self.platform_buttons.items():
            active = name == key
            pill.setStyleSheet(
                f"QPushButton {{ border-radius: 10px; padding: 9px 22px;"
                f" background-color: {theme.ACCENT_SOFT if active else 'transparent'};"
                f" border: 1px solid {theme.ACCENT_HOVER if active else theme.BORDER_SOFT};"
                f" color: {'#FFFFFF' if active else theme.MUTED};"
                f" font-weight: {'700' if active else '500'}; }}")
        self.refresh()

    def profiles(self):
        base = profiles_dir()
        if not os.path.isdir(base):
            return []
        return sorted(name for name in os.listdir(base)
                      if os.path.isdir(os.path.join(base, name)))

    def refresh(self):
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.profile_tiles = {}
        from core.upload import browser as browser_lib

        names = self.profiles()
        if not names:
            self.list_box.addWidget(widgets.empty_state(
                "এখনো কোনো প্রোফাইল নেই", "উপরে একটি নাম দিয়ে যোগ করুন", "user"))
        for name in names:
            has_session = browser_lib.has_session(name, self.platform)
            age = browser_lib.session_age_days(name, self.platform)
            if has_session:
                subtitle = f"সেশন সেভ করা আছে — {age} দিন আগে ব্যবহৃত"
                badge = "প্রস্তুত"
            else:
                subtitle = "এখনো লগইন করা হয়নি"
                badge = ""
            tile = widgets.OptionTile(name, subtitle, icon_name="user", badge=badge, compact=True)
            tile.clicked.connect(lambda n=name: self.select(n))
            if name == self.selected_profile:
                tile.set_selected(True)
            self.list_box.addWidget(tile)
            self.profile_tiles[name] = tile

    def select(self, name):
        self.selected_profile = name
        for key, tile in self.profile_tiles.items():
            tile.set_selected(key == name)
        self.name_input.setText(name)

    def on_add(self):
        name = self.name_input.text().strip()
        if not name:
            self.studio.log("প্রোফাইলের নাম লিখুন", "warn")
            return
        os.makedirs(os.path.join(profiles_dir(), name), exist_ok=True)
        self.selected_profile = name
        self.studio.log("প্রোফাইল তৈরি: " + name, "ok")
        self.refresh()
        self.select(name)

    def _current_profile(self):
        name = self.selected_profile or self.name_input.text().strip()
        if not name:
            self.studio.log("আগে একটি প্রোফাইল বেছে নিন", "warn")
        return name

    def on_login(self):
        profile = self._current_profile()
        if not profile:
            return
        platform = self.platform
        studio = self.studio
        self.login_btn.setEnabled(False)
        self.status_label.setText("ব্রাউজার খোলা হচ্ছে…")

        def work(progress, log, cancel):
            from core.upload import facebook, youtube
            module = youtube if platform == "youtube" else facebook
            progress(0.05, "ব্রাউজার খোলা হচ্ছে — সেখানে লগইন করুন")
            result = module.login(profile, headless=False, timeout=900,
                                  on_status=lambda msg: log(msg, "dim"), cancel=cancel)
            progress(1.0, "লগইন ধাপ শেষ")
            return {"kind": "login", "platform": platform, "profile": profile, "result": result}

        studio.submit(f"লগইন ({platform})", work)

    def on_test(self):
        profile = self._current_profile()
        if not profile:
            return
        platform = self.platform
        studio = self.studio

        def work(progress, log, cancel):
            from core.upload import facebook, youtube
            module = youtube if platform == "youtube" else facebook
            progress(0.3, "সেশন যাচাই করা হচ্ছে…")
            result = module.check_session(profile, headless=True)
            progress(1.0, "যাচাই শেষ")
            log(("সেশন ঠিক আছে" if result.get("logged_in") else "সেশন নেই বা মেয়াদ শেষ"),
                "ok" if result.get("logged_in") else "warn")
            return {"kind": "session_test", "platform": platform, "profile": profile,
                    "result": result}

        studio.submit("সেশন টেস্ট", work)

    def on_forget(self):
        profile = self._current_profile()
        if not profile:
            return
        from core.upload import browser as browser_lib
        browser_lib.forget_session(profile, self.platform)
        self.studio.log("সেশন মুছে ফেলা হয়েছে: " + profile, "warn")
        self.refresh()

    def show_result(self, result):
        self.login_btn.setEnabled(True)
        kind = result.get("kind")
        payload = result.get("result") or {}
        if kind == "login":
            if payload.get("logged_in"):
                self.status_label.setText(
                    f"{result['profile']} — {result['platform']} লগইন সফল ও সেশন সেভ হয়েছে ✅")
            else:
                self.status_label.setText("লগইন সম্পন্ন হয়নি — আবার চেষ্টা করুন")
            self.refresh()
        elif kind == "session_test":
            state = "ঠিক আছে ✅" if payload.get("logged_in") else "নেই ✖"
            self.status_label.setText(f"{result['profile']} — {result['platform']}: সেশন {state}")
            self.refresh()
