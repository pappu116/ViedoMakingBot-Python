"""Inline SVG icon set rendered with QtSvg (no external asset files)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PATHS = {
    "dashboard": "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6V11h-6v9Zm0-16v5h6V4h-6Z",
    "content": "M8 3h8l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 1v5h5M9 13h8M9 17h6",
    "video": "M3 6.5A2.5 2.5 0 0 1 5.5 4h7A2.5 2.5 0 0 1 15 6.5v11A2.5 2.5 0 0 1 12.5 20h-7A2.5 2.5 0 0 1 3 17.5v-11ZM15 9.5l5-3v11l-5-3",
    "projects": "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z",
    "tools": "M14.7 6.3a4 4 0 1 0 5 5l-2 2-1.5-1.5-2 2L12.7 12l2-2L13.2 8.5l1.5-2.2ZM12.5 11.5 4 20l1.5 1.5 8.5-8.5",
    "settings": "M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7Zm8-3.5-.2 1.6 1.7 1.3-1.4 2.4-2-.7-1.4 1-.3 2.1h-2.8l-.3-2.1-1.4-1-2 .7L8.5 15l1.7-1.3L10 12l.2-1.6L8.5 9.1l1.4-2.4 2 .7 1.4-1L13.6 4h2.8l.3 2.1 1.4 1 2-.7 1.4 2.4-1.7 1.3.2 1.6",
    "plus": "M12 5v14M5 12h14",
    "check": "M4 12.5 9 17.5 20 6.5",
    "close": "M6 6l12 12M18 6 6 18",
    "chevron_right": "M9 5l7 7-7 7",
    "chevron_left": "M15 5l-7 7 7 7",
    "chevron_down": "M5 9l7 7 7-7",
    "chevron_up": "M5 15l7-7 7 7",
    "upload": "M12 16V4m0 0L7 9m5-5 5 5M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2",
    "download": "M12 4v12m0 0 5-5m-5 5-5-5M4 19h16",
    "play": "M7 4.5 19 12 7 19.5v-15Z",
    "pause": "M8 5v14M16 5v14",
    "refresh": "M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5",
    "trash": "M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13",
    "image": "M4 5h16v14H4V5Zm0 10 4.5-4.5L13 15l2.5-2.5L20 16M9.5 9.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z",
    "mic": "M12 15a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Zm6-3a6 6 0 0 1-12 0m6 6v3m-3 0h6",
    "music": "M9 18V6l10-2v12M9 18a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Zm10-2a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Z",
    "subtitles": "M3 6h18v12H3V6Zm3 6h5m-5 3h8m2-3h3",
    "sparkles": "M12 3l1.8 4.7L18.5 9.5 13.8 11.3 12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3Zm6.5 9.5.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9.9-2.3Z",
    "eye": "M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Zm9.5 2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
    "clock": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5l4 2",
    "user": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 9a8 8 0 0 1 16 0",
    "logout": "M15 12H4m0 0 4-4m-4 4 4 4M13 4h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-5",
    "folder_open": "M3 8a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v1M3 8v9a2 2 0 0 0 2 2h12.5a2 2 0 0 0 1.9-1.4l1.6-5A1 1 0 0 0 20 11H7",
    "alert": "M12 3 2.5 20h19L12 3Zm0 6v5m0 3v.5",
    "info": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v.5m0 3.5v5",
    "star": "M12 3.5l2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 10l6.1-.9L12 3.5Z",
    "youtube": "M21 8.5c-.2-1.6-.9-2.6-2.6-2.8C16.7 5.5 14.4 5.4 12 5.4s-4.7.1-6.4.3C3.9 5.9 3.2 6.9 3 8.5c-.2 1.4-.2 3.6 0 5 .2 1.6.9 2.6 2.6 2.8 1.7.2 4 .3 6.4.3s4.7-.1 6.4-.3c1.7-.2 2.4-1.2 2.6-2.8.2-1.4.2-3.6 0-5ZM10 15V9l5.5 3L10 15Z",
    "facebook": "M14 9V7.5c0-.9.3-1.5 1.6-1.5H17V3.2c-.3 0-1.3-.2-2.4-.2-2.4 0-4.1 1.5-4.1 4.2V9H8v3h2.5v9H14v-9h2.6l.4-3H14Z",
    "film": "M3 5h18v14H3V5Zm0 4.5h4M3 14.5h4M17 9.5h4M17 14.5h4M7 5v14m10-14v14",
    "layers": "M12 3 3 8l9 5 9-5-9-5Zm-9 9 9 5 9-5m-18 4 9 5 9-5",
    "key": "M15 8a3 3 0 1 0-2.6 3l-1.2 1.2-.6-.6-6.4 6.4H3v-2l7.6-7.6A3 3 0 0 0 15 8Z",
    "globe": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-9-9h18M12 3c2.5 2.4 3.7 5.4 3.7 9S14.5 18.6 12 21c-2.5-2.4-3.7-5.4-3.7-9S9.5 5.4 12 3Z",
    "wand": "M15 4l1 2.5L18.5 7 16 8l-1 2.5L14 8l-2.5-1L14 6.5 15 4ZM4 20l9-9 1.5 1.5-9 9L4 20Z",
    "bell": "M12 3a5 5 0 0 0-5 5v4l-1.5 3h13L17 12V8a5 5 0 0 0-5-5Zm-2 15a2 2 0 0 0 4 0",
    "stop": "M6 6h12v12H6z",
    "save": "M5 4h11l3 3v13H5V4Zm3 0v6h7V4M8 20v-6h8v6",
    "external": "M14 4h6v6M20 4l-8.5 8.5M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
}


def svg(name, color="#E6EAF2", size=24, stroke=1.8, fill=False):
    body = PATHS.get(name, PATHS["info"])
    if fill or name in ("play", "dashboard", "folder_open", "star", "youtube", "facebook", "stop"):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
                f'viewBox="0 0 24 24"><path d="{body}" fill="{color}"/></svg>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="{body}"/></svg>')


def icon(name, color="#E6EAF2", size=20):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(svg(name, color, size).encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def app_icon(size=256):
    """Rounded violet square with a play glyph — used for the window and tray."""
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)
    shape = QPainterPath()
    shape.addRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor("#8B5CF6"))
    gradient.setColorAt(1, QColor("#5B21B6"))
    painter.fillPath(shape, gradient)
    painter.setClipPath(shape)
    glyph = QSvgRenderer(QByteArray(svg("play", "#FFFFFF", size).encode("utf-8")))
    inset = size * 0.28
    glyph.render(painter, QRectF(inset, inset, size - inset * 2, size - inset * 2))
    painter.end()
    return QIcon(pix)


def pixmap(name, color="#E6EAF2", size=20):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(svg(name, color, size).encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return pix
