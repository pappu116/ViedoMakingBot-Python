"""Wizard chrome: the 'ধাপ N / ৭' badge and the clickable step strip."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui import theme, widgets

STEP_TITLES = [
    "আইডিয়া / স্ক্রিপ্ট",
    "স্টাইল ও ফ্রেম",
    "ভয়েস",
    "মিউজিক ও সাবটাইটেল",
    "প্রিভিউ ও রেন্ডার",
    "একাউন্ট",
    "পাবলিশ",
]
STEP_ICONS = ["content", "image", "mic", "music", "film", "user", "upload"]
STEP_COUNT = len(STEP_TITLES)


class StepStrip(QWidget):
    go = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.pills = []
        for index, title in enumerate(STEP_TITLES):
            pill = QPushButton(f"{index + 1}. {title}")
            pill.setCursor(Qt.PointingHandCursor)
            pill.setMinimumHeight(34)
            pill.clicked.connect(lambda _=False, i=index: self.go.emit(i))
            layout.addWidget(pill)
            self.pills.append(pill)
        layout.addStretch(1)
        self.set_step(0)

    def set_step(self, index):
        for position, pill in enumerate(self.pills):
            active = position == index
            done = position < index
            pill.setProperty("nav", "true")
            pill.setProperty("active", "true" if active else "false")
            color = "#FFFFFF" if active else (theme.SUCCESS if done else theme.MUTED)
            pill.setStyleSheet(
                f"QPushButton {{ text-align:center; padding: 8px 12px; border-radius: 10px;"
                f" color: {color}; border: 1px solid "
                f"{theme.ACCENT_HOVER if active else theme.BORDER_SOFT};"
                f" background-color: {theme.ACCENT_SOFT if active else 'transparent'};"
                f" font-weight: {'700' if active else '500'}; }}"
                f"QPushButton:hover {{ background-color: {theme.CARD_ALT}; color: {theme.TEXT}; }}")
            pill.style().unpolish(pill)
            pill.style().polish(pill)


class StepHeader(QWidget):
    """Heading + badge + helper text shown at the top of every wizard step."""

    def __init__(self, index, title, subtitle="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(widgets.label(title, "h1"))
        top.addWidget(widgets.label(f"ধাপ {index + 1} / {STEP_COUNT}", "stepBadge"))
        top.addStretch(1)
        layout.addLayout(top)
        if subtitle:
            layout.addWidget(widgets.label(subtitle, "muted", wrap=True))


def back_next(on_back=None, on_next=None, next_text="পরের ধাপ", back_text="আগের ধাপ",
              next_icon="chevron_right"):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    if on_back:
        layout.addWidget(widgets.button(back_text, "ghost", "chevron_left", on_click=on_back))
    layout.addStretch(1)
    if on_next:
        layout.addWidget(widgets.button(next_text, "primary", next_icon, on_click=on_next))
    return row
