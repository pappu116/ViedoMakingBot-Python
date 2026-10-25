"""Reusable widgets: cards, tiles, switches, rings, console, phone preview."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt,
                            QTimer, Signal)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QSlider,
                               QToolButton, QVBoxLayout, QWidget)

from ui import icons, theme


# --------------------------------------------------------------------- basics
def label(text="", kind="body", parent=None, wrap=False):
    widget = QLabel(text, parent)
    styles = {
        "h1": "h1", "h2": "h2", "cardTitle": "cardTitle", "muted": "muted", "dim": "dim",
        "accent": "accent", "link": "link", "chip": "chip", "chipAccent": "chipAccent",
        "chipPop": "chipPop", "stepBadge": "stepBadge", "statValue": "statValue",
        "statusPill": "statusPill",
    }
    if kind in styles:
        widget.setObjectName(styles[kind])
    if wrap:
        widget.setWordWrap(True)
    return widget


def button(text="", variant="default", icon_name=None, parent=None, on_click=None,
           tooltip="", height=None):
    widget = QPushButton(text, parent)
    if variant != "default":
        widget.setProperty("variant", variant)
    if icon_name:
        widget.setIcon(icons.icon(icon_name, "#FFFFFF" if variant == "primary" else theme.TEXT_DIM, 18))
        widget.setIconSize(QSize(18, 18))
    widget.setMinimumHeight(height or (42 if variant == "primary" else 36))
    widget.setCursor(Qt.PointingHandCursor)
    if tooltip:
        widget.setToolTip(tooltip)
    if on_click:
        widget.clicked.connect(on_click)
    return widget


def icon_button(icon_name, parent=None, on_click=None, tooltip="", size=34, color=None):
    widget = QToolButton(parent)
    widget.setProperty("variant", "icon")
    widget.setIcon(icons.icon(icon_name, color or theme.TEXT_DIM, 20))
    widget.setIconSize(QSize(20, 20))
    widget.setFixedSize(size, size)
    widget.setCursor(Qt.PointingHandCursor)
    if tooltip:
        widget.setToolTip(tooltip)
    if on_click:
        widget.clicked.connect(on_click)
    return widget


def divider(parent=None):
    frame = QFrame(parent)
    frame.setObjectName("divider")
    frame.setFixedHeight(1)
    return frame


def spacer(width=0, height=0):
    widget = QWidget()
    if width:
        widget.setFixedWidth(width)
    if height:
        widget.setFixedHeight(height)
    return widget


class Card(QFrame):
    """Rounded panel with an optional header row."""

    def __init__(self, parent=None, title="", subtitle="", icon_name=None, accent_dot=True,
                 right_widget=None, padding=18):
        super().__init__(parent)
        self.setObjectName("card")
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(padding, padding, padding, padding)
        self.outer.setSpacing(12)
        self.header_row = None
        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        if title:
            self.header_row = QHBoxLayout()
            self.header_row.setSpacing(10)
            if accent_dot:
                dot = QLabel()
                dot.setFixedSize(9, 9)
                dot.setStyleSheet(f"background-color: {theme.ACCENT_HOVER}; border-radius: 4px;")
                self.header_row.addWidget(dot)
            if icon_name:
                icon_label = QLabel()
                icon_label.setPixmap(icons.pixmap(icon_name, theme.ACCENT_HOVER, 20))
                self.header_row.addWidget(icon_label)
            title_box = QVBoxLayout()
            title_box.setSpacing(2)
            title_box.addWidget(label(title, "cardTitle"))
            if subtitle:
                title_box.addWidget(label(subtitle, "muted", wrap=True))
            self.header_row.addLayout(title_box)
            self.header_row.addStretch(1)
            if right_widget:
                self.header_row.addWidget(right_widget)
            self.outer.addLayout(self.header_row)
        self.outer.addLayout(self.body)

    def add(self, widget):
        self.body.addWidget(widget)
        return widget

    def add_layout(self, layout):
        self.body.addLayout(layout)
        return layout

    def add_row(self, *widgets):
        row = QHBoxLayout()
        row.setSpacing(10)
        for widget in widgets:
            if widget is None:
                row.addStretch(1)
            elif isinstance(widget, int):
                row.addSpacing(widget)
            else:
                row.addWidget(widget)
        self.body.addLayout(row)
        return row


def field_block(title, widget, hint=""):
    """Label above the control — keeps a row of fields perfectly aligned."""
    block = QWidget()
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(label(title, "dim"))
    layout.addWidget(widget)
    if hint:
        layout.addWidget(label(hint, "muted", wrap=True))
    return block


def field_row(title, widget, hint="", width=210):
    """Label + control row used across the wizard steps."""
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    text_box = QVBoxLayout()
    text_box.setSpacing(2)
    name = label(title, "dim")
    text_box.addWidget(name)
    if hint:
        text_box.addWidget(label(hint, "muted", wrap=True))
    holder = QWidget()
    holder.setLayout(text_box)
    holder.setMinimumWidth(width)
    layout.addWidget(holder, 1)
    layout.addWidget(widget, 2)
    return wrapper


# --------------------------------------------------------------------- inputs
class Switch(QAbstractButton):
    """Animated pill toggle matching the reference design."""

    def __init__(self, parent=None, checked=True, on_color=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(50, 28)
        self._offset = 1.0 if checked else 0.0
        self._on_color = QColor(on_color or theme.ACCENT)
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, value):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if value else 0.0)
        self._anim.start()

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        track = QRectF(0, 2, self.width(), self.height() - 4)
        off = QColor("#2A3549")
        current = QColor(self._on_color)
        color = QColor(
            int(off.red() + (current.red() - off.red()) * self._offset),
            int(off.green() + (current.green() - off.green()) * self._offset),
            int(off.blue() + (current.blue() - off.blue()) * self._offset),
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        knob_size = self.height() - 8
        left = 4 + (self.width() - knob_size - 8) * self._offset
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(left, 4, knob_size, knob_size))
        painter.end()


def switch_row(title, hint="", checked=True, on_change=None, parent=None):
    wrapper = QWidget(parent)
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    text_box = QVBoxLayout()
    text_box.setSpacing(2)
    text_box.addWidget(label(title, "dim"))
    if hint:
        text_box.addWidget(label(hint, "muted", wrap=True))
    holder = QWidget()
    holder.setLayout(text_box)
    layout.addWidget(holder, 1)
    toggle = Switch(checked=checked)
    if on_change:
        toggle.toggled.connect(on_change)
    layout.addWidget(toggle, 0, Qt.AlignVCenter)
    wrapper.toggle = toggle
    return wrapper


class SliderRow(QWidget):
    """Label + slider + live value readout."""

    def __init__(self, title, minimum=0, maximum=100, value=50, suffix="", parent=None,
                 on_change=None, hint=""):
        super().__init__(parent)
        self.suffix = suffix
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(10)
        caption = QVBoxLayout()
        caption.setSpacing(2)
        caption.addWidget(label(title, "dim"))
        if hint:
            caption.addWidget(label(hint, "muted", wrap=True))
        holder = QWidget()
        holder.setLayout(caption)
        top.addWidget(holder, 1)
        self.value_label = label(f"{value}{suffix}", "accent")
        top.addWidget(self.value_label, 0, Qt.AlignTop)
        layout.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(minimum))
        self.slider.setMaximum(int(maximum))
        self.slider.setValue(int(value))
        self.slider.valueChanged.connect(self._changed)
        layout.addWidget(self.slider)
        self._on_change = on_change

    def _changed(self, value):
        self.value_label.setText(f"{value}{self.suffix}")
        if self._on_change:
            self._on_change(value)

    def value(self):
        return self.slider.value()

    def set_value(self, value):
        self.slider.setValue(int(value))


class SearchField(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setObjectName("search")
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(46)
        self._icon = icons.pixmap("wand", theme.MUTED_DARK, 18)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setOpacity(0.9)
        painter.drawPixmap(14, (self.height() - 18) // 2, self._icon)
        painter.end()


class PathPicker(QWidget):
    """Line edit + browse button (files or directories)."""

    def __init__(self, parent=None, mode="dir", placeholder="", file_filter="সব ফাইল (*.*)"):
        super().__init__(parent)
        self.mode = mode
        self.file_filter = file_filter
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        layout.addWidget(self.edit, 1)
        layout.addWidget(button("ব্রাউজ", "ghost", "folder_open", on_click=self._browse))

    def _browse(self):
        if self.mode == "dir":
            path = QFileDialog.getExistingDirectory(self, "ফোল্ডার নির্বাচন করুন", self.edit.text() or "")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "ফাইল নির্বাচন করুন", self.edit.text() or "",
                                                  self.file_filter)
        if path:
            self.edit.setText(os.path.normpath(path))

    def text(self):
        return self.edit.text().strip()

    def setText(self, value):
        self.edit.setText(value or "")


# --------------------------------------------------------------------- tiles
class OptionTile(QFrame):
    """Selectable card (aspect ratio, platform, account, ...)."""

    clicked = Signal()

    def __init__(self, title, subtitle="", icon_name=None, badge="", parent=None, badge_kind="chipPop",
                 compact=False):
        super().__init__(parent)
        self.setObjectName("cardFlat")
        self.setCursor(Qt.PointingHandCursor)
        self._selected = False
        self.setMinimumHeight(46 if compact else 96)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        self.icon_label = None
        if icon_name:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(icons.pixmap(icon_name, theme.ACCENT_HOVER, 26))
            self.icon_label.setFixedWidth(30)
            layout.addWidget(self.icon_label, 0, Qt.AlignTop)
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        header = QHBoxLayout()
        header.setSpacing(8)
        self.title_label = label(title, "dim")
        header.addWidget(self.title_label)
        if badge:
            header.addWidget(label(badge, badge_kind))
        header.addStretch(1)
        text_box.addLayout(header)
        if subtitle:
            self.subtitle_label = label(subtitle, "muted", wrap=True)
            text_box.addWidget(self.subtitle_label)
        layout.addLayout(text_box, 1)
        layout.addStretch(0)
        self.check = QLabel()
        self.check.setFixedWidth(22)
        layout.addWidget(self.check, 0, Qt.AlignVCenter)
        self._refresh()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._refresh()

    def is_selected(self):
        return self._selected

    def set_subtitle(self, text):
        if getattr(self, "subtitle_label", None):
            self.subtitle_label.setText(text)

    def _refresh(self):
        if self._selected:
            self.setStyleSheet(
                f"QFrame#cardFlat {{ background-color: {theme.ACCENT_SOFT};"
                f" border: 1.5px solid {theme.ACCENT_HOVER}; border-radius: {theme.RADIUS_SM}px; }}")
            self.check.setPixmap(icons.pixmap("check", theme.ACCENT_HOVER, 20))
            if self.icon_label:
                self.icon_label.setPixmap(icons.pixmap("check", theme.ACCENT_HOVER, 0))
        else:
            self.setStyleSheet("")
            self.check.setPixmap(QPixmap())
            if self.icon_label:
                self.icon_label.setPixmap(icons.pixmap(
                    getattr(self, "_icon_name", "layers") or "layers", theme.MUTED, 26))


class StyleTile(QFrame):
    """Colour swatch tile used for video styles."""

    clicked = Signal()

    def __init__(self, key, title, color, parent=None):
        super().__init__(parent)
        self.key = key
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(84)
        self._selected = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)
        self.swatch = QLabel()
        self.swatch.setFixedHeight(6)
        self.swatch.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        layout.addWidget(self.swatch)
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.title_label = label(title, "dim")
        bottom.addWidget(self.title_label, 1)
        self.check_label = QLabel()
        self.check_label.setFixedWidth(18)
        bottom.addWidget(self.check_label)
        layout.addLayout(bottom)
        self._color = color
        self._refresh()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._refresh()

    def _refresh(self):
        if self._selected:
            self.setStyleSheet(
                f"QFrame {{ background-color: {theme.ACCENT_SOFT};"
                f" border: 1.5px solid {self._color}; border-radius: {theme.RADIUS_SM}px; }}")
            self.check_label.setPixmap(icons.pixmap("check", self._color, 17))
        else:
            self.setStyleSheet(
                f"QFrame {{ background-color: {theme.CARD_ALT};"
                f" border: 1px solid {theme.BORDER_SOFT}; border-radius: {theme.RADIUS_SM}px; }}")
            self.check_label.setPixmap(QPixmap())


class StatCard(QFrame):
    def __init__(self, title, value="0", icon_name="star", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFlat")
        color = color or theme.ACCENT_HOVER
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label(title, "muted"))
        top.addStretch(1)
        icon_label = QLabel()
        icon_label.setPixmap(icons.pixmap(icon_name, color, 20))
        top.addWidget(icon_label)
        layout.addLayout(top)
        self.value_label = label(str(value), "statValue")
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


class ProgressRing(QWidget):
    """Circular progress used in the sidebar."""

    def __init__(self, parent=None, size=64, thickness=7, color=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._value = 0.0
        self._thickness = thickness
        self._color = QColor(color or theme.ACCENT_HOVER)

    def set_value(self, value):
        self._value = max(0.0, min(1.0, float(value)))
        self.update()

    def value(self):
        return self._value

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self._thickness / 2 + 1, self._thickness / 2 + 1,
                      self.width() - self._thickness - 2, self.height() - self._thickness - 2)
        pen = QPen(QColor("#1C2740"), self._thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        pen.setColor(self._color)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -int(360 * 16 * self._value))
        painter.setPen(QColor(theme.TEXT))
        font = QFont(theme.family())
        font.setPixelSize(max(12, int(self.width() * 0.26)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self._value * 100)}%")
        painter.end()


class PhonePreview(QFrame):
    """9:16 phone-shaped frame that hosts a preview image or video widget."""

    def __init__(self, parent=None, width=270):
        super().__init__(parent)
        self.setObjectName("cardFlat")
        self._aspect = 16 / 9
        self.setFixedWidth(width)
        radius = int(width * 0.09)
        self.setStyleSheet(
            f"QFrame#cardFlat {{ background-color: #0A0F1C;"
            f" border: 1.5px solid {theme.BORDER}; border-radius: {radius}px; }}")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(8, 8, 8, 8)
        self.content = QLabel()
        self.content.setAlignment(Qt.AlignCenter)
        self.content.setStyleSheet("background: transparent; border: none;")
        self.content.setText("প্রিভিউ\nদেখতে বাটন চাপুন")
        self.layout_.addWidget(self.content)
        self._screen_radius = radius - 6

    def set_aspect(self, width, height):
        self._aspect = (height / width) if width else 16 / 9
        self.setFixedHeight(int(self.width() * self._aspect))
        self._apply_mask()

    def _apply_mask(self):
        self.content.setStyleSheet("background: transparent; border: none;")

    def set_image(self, path):
        if not path or not os.path.exists(path):
            self.content.setPixmap(QPixmap())
            self.content.setText("প্রিভিউ নেই")
            return
        pix = QPixmap(path)
        target_w = self.content.width() or (self.width() - 16)
        target_h = self.content.height() or int(target_w * self._aspect)
        scaled = pix.scaled(target_w, target_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded = QPixmap(scaled.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        path_ = QPainterPath()
        path_.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 14, 14)
        painter.setClipPath(path_)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.content.setPixmap(rounded)

    def set_widget(self, widget):
        self.layout_.addWidget(widget)


class LogConsole(QFrame):
    """Coloured log panel used at the bottom of the window."""

    def __init__(self, parent=None, height=150):
        super().__init__(parent)
        self.setObjectName("logPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFrameStyle(0)
        self.view.setStyleSheet("background: transparent; border: none; font-size: 13px;")
        self.view.setMaximumBlockCount(4000)
        self.view.setFixedHeight(height)
        layout.addWidget(self.view)
        self._buffer = []

    def append(self, message, level="info"):
        colors = {"info": theme.TEXT_DIM, "ok": theme.SUCCESS, "warn": theme.WARN,
                  "error": theme.DANGER, "dim": theme.MUTED}
        color = colors.get(level, theme.TEXT_DIM)
        text = str(message)
        if self._buffer is not None and len(self._buffer) < 4000:
            self._buffer.append(text)
        from html import escape
        self.view.appendHtml(
            f'<span style="color:{color}; white-space:pre-wrap;">{escape(text)}</span>')
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    def text(self):
        return "\n".join(self._buffer or [])

    def clear(self):
        self.view.clear()
        self._buffer = []


class Toast(QLabel):
    """Small floating confirmation that fades out by itself."""

    def __init__(self, parent, message, kind="info", duration=2600):
        super().__init__(message, parent)
        palette = {"info": theme.ACCENT, "ok": theme.SUCCESS, "warn": theme.WARN, "error": theme.DANGER}
        color = palette.get(kind, theme.ACCENT)
        self.setStyleSheet(
            f"background-color: {theme.CARD}; color: {theme.TEXT};"
            f" border: 1px solid {color}; border-radius: 10px; padding: 10px 16px; font-size: 14px;")
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self.deleteLater)

    def place(self, x_center, y):
        self.move(int(x_center - self.width() / 2), int(y))
        self.raise_()


def empty_state(text, hint="", icon_name="info", parent=None):
    box = QWidget(parent)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 26, 0, 26)
    layout.setSpacing(8)
    icon_label = QLabel()
    icon_label.setPixmap(icons.pixmap(icon_name, theme.MUTED_DARK, 34))
    icon_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(icon_label)
    message = label(text, "dim")
    message.setAlignment(Qt.AlignCenter)
    layout.addWidget(message)
    if hint:
        sub = label(hint, "muted", wrap=True)
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)
    return box


def thumbnail_label(path, width=96, height=170, radius=10):
    holder = QLabel()
    holder.setFixedSize(width, height)
    holder.setAlignment(Qt.AlignCenter)
    holder.setStyleSheet(
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
        shape.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
        painter.setClipPath(shape)
        painter.drawPixmap((width - pix.width()) // 2, (height - pix.height()) // 2, pix)
        painter.end()
        holder.setPixmap(rounded)
    else:
        holder.setText("—")
    return holder


def progress_bar(value=0, height=8):
    bar = QProgressBar()
    bar.setRange(0, 1000)
    bar.setValue(int(value * 1000))
    bar.setTextVisible(False)
    bar.setFixedHeight(height)
    return bar


def scroll_container():
    from PySide6.QtWidgets import QScrollArea
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(0, 0, 6, 0)
    layout.setSpacing(14)
    area.setWidget(inner)
    return area, inner, layout
