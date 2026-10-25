"""Design tokens and global stylesheet (dark navy + violet, Bengali UI)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------------ palette
BG = "#0B1020"
BG_SOFT = "#0E1424"
SIDEBAR = "#0A0E1A"
CARD = "#141B2D"
CARD_ALT = "#182034"
CARD_HOVER = "#1B2439"
BORDER = "#1E2A45"
BORDER_SOFT = "#182238"
TEXT = "#E6EAF2"
TEXT_DIM = "#C7CEE0"
MUTED = "#94A3B8"
MUTED_DARK = "#64748B"
ACCENT = "#7C3AED"
ACCENT_HOVER = "#8B5CF6"
ACCENT_PRESS = "#6D28D9"
ACCENT_SOFT = "#2A1E52"
BLUE = "#3B82F6"
SUCCESS = "#22C55E"
DANGER = "#EF4444"
DANGER_DARK = "#B91C1C"
WARN = "#F59E0B"
STYLE_COLORS = {
    "cinematic": "#7C3AED",
    "dramatic": "#DC2626",
    "educational": "#16A34A",
    "vibrant": "#F59E0B",
    "anime": "#EC4899",
    "cartoon2d": "#FBBF24",
    "whiteboard": "#E5E7EB",
    "sketch": "#D6C9A8",
    "realistic": "#0EA5E9",
    "slide": "#6366F1",
    "puppet": "#EA580C",
}

RADIUS = 16
RADIUS_SM = 10

_family = "Segoe UI"
_base_size = 10
_chevron = ""
_chevron_up = ""


def family():
    return _family


def _arrow_asset(key, icon_name, color=None):
    """Cache small arrow images so combos/spin boxes visibly look interactive."""
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer
    from paths import cache_dir
    from ui import icons

    try:
        os.makedirs(cache_dir(), exist_ok=True)
        path = os.path.join(cache_dir(), f"ui_{key}.png")
        if not os.path.exists(path):
            renderer = QSvgRenderer(
                QByteArray(icons.svg(icon_name, color or MUTED, 24).encode("utf-8")))
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            pixmap.save(path)
        return path.replace("\\", "/")
    except Exception:
        return ""


def apply(app):
    """Install fonts, palette and the global stylesheet."""
    global _family, _chevron, _chevron_up
    from PySide6.QtGui import QColor, QPalette
    from core import textrender
    textrender.load_fonts()
    _family = textrender.family()
    _chevron = _arrow_asset("chevron_down", "chevron_down")
    _chevron_up = _arrow_asset("chevron_up", "chevron_up")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor("#0E1526"))
    palette.setColor(QPalette.AlternateBase, QColor(CARD_ALT))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor("#6B7A99"))
    palette.setColor(QPalette.Button, QColor(CARD_ALT))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipBase, QColor(CARD))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(MUTED_DARK))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(MUTED_DARK))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(MUTED_DARK))
    app.setPalette(palette)

    app.setStyleSheet(stylesheet())
    return _family


def font(size=None, bold=False, italic=False):
    from PySide6.QtGui import QFont
    qfont = QFont(_family)
    qfont.setPixelSize(int(size or 15))
    qfont.setBold(bool(bold))
    qfont.setItalic(bool(italic))
    return qfont


def rule():
    return f"1px solid {BORDER}"


def stylesheet():
    return f"""
* {{
    font-family: "{_family}";
    outline: none;
}}
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: 15px;
}}
QMainWindow, QDialog {{ background-color: {BG}; }}
QWidget#page, QWidget#viewport {{ background-color: {BG}; }}

QFrame#sidebar {{ background-color: {SIDEBAR}; border: none; }}
QFrame#topbar {{ background-color: {BG}; border: none; }}
QFrame#card {{
    background-color: {CARD};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
}}
QFrame#cardFlat {{
    background-color: {CARD_ALT};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS_SM}px;
}}
QFrame#divider {{ background-color: {BORDER_SOFT}; max-height: 1px; border: none; }}
QFrame#logPanel {{ background-color: {SIDEBAR}; border: 1px solid {BORDER_SOFT}; border-radius: {RADIUS_SM}px; }}

QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 27px; font-weight: 700; color: {TEXT}; }}
QLabel#h2 {{ font-size: 19px; font-weight: 700; color: {TEXT}; }}
QLabel#cardTitle {{ font-size: 17px; font-weight: 700; color: {TEXT}; }}
QLabel#muted {{ color: {MUTED}; font-size: 14px; }}
QLabel#dim {{ color: {TEXT_DIM}; font-size: 14px; }}
QLabel#accent {{ color: {ACCENT_HOVER}; font-weight: 600; }}
QLabel#link {{ color: {BLUE}; }}
QLabel#stepBadge {{
    background-color: {ACCENT_SOFT};
    color: #C4B5FD;
    border: 1px solid #4C1D95;
    border-radius: 11px;
    padding: 3px 12px;
    font-size: 13px;
    font-weight: 600;
}}
QLabel#chip {{
    background-color: {CARD_ALT};
    color: {MUTED};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 13px;
}}
QLabel#chipAccent {{
    background-color: {ACCENT_SOFT};
    color: #C4B5FD;
    border: 1px solid #4C1D95;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 13px;
    font-weight: 600;
}}
QLabel#chipPop {{
    background-color: #14532D;
    color: #86EFAC;
    border: 1px solid #166534;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
}}
QLabel#statValue {{ font-size: 25px; font-weight: 700; color: {TEXT}; }}
QLabel#statusPill {{
    background-color: {CARD_ALT};
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
    padding: 5px 14px;
    color: {MUTED};
}}

QPushButton {{
    background-color: {CARD_ALT};
    color: {TEXT};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS_SM}px;
    padding: 9px 16px;
    font-size: 15px;
}}
QPushButton:hover {{ background-color: {CARD_HOVER}; border-color: {BORDER}; }}
QPushButton:pressed {{ background-color: #121A2C; }}
QPushButton:disabled {{ color: {MUTED_DARK}; background-color: #101728; border-color: {BORDER_SOFT}; }}
QPushButton[variant="primary"] {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT_HOVER};
    color: #FFFFFF;
    font-weight: 700;
    padding: 11px 22px;
}}
QPushButton[variant="primary"]:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {ACCENT_PRESS}; }}
QPushButton[variant="primary"]:disabled {{ background-color: #4C3A80; border-color: #4C3A80; color: #C9C2E0; }}
QPushButton[variant="ghost"] {{ background-color: transparent; border: 1px solid {BORDER}; color: {TEXT_DIM}; }}
QPushButton[variant="ghost"]:hover {{ background-color: {CARD_ALT}; color: {TEXT}; }}
QPushButton[variant="danger"] {{ background-color: #3B1113; border: 1px solid {DANGER_DARK}; color: #FCA5A5; }}
QPushButton[variant="danger"]:hover {{ background-color: {DANGER_DARK}; color: #FFFFFF; }}
QPushButton[variant="success"] {{ background-color: #0E3A22; border: 1px solid #166534; color: #86EFAC; }}
QPushButton[variant="success"]:hover {{ background-color: #166534; color: #FFFFFF; }}
QPushButton[nav="true"] {{
    text-align: left;
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 11px 14px;
    color: {TEXT_DIM};
    font-size: 15px;
}}
QPushButton[nav="true"]:hover {{ background-color: {CARD_ALT}; color: {TEXT}; }}
QPushButton[nav="true"][active="true"] {{ background-color: {ACCENT_SOFT}; color: #FFFFFF; font-weight: 700; }}
QPushButton[variant="icon"] {{ padding: 7px; border-radius: 10px; background-color: transparent; border: none; }}
QPushButton[variant="icon"]:hover {{ background-color: {CARD_ALT}; }}

QSpinBox {{
    background-color: #0E1526;
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 9px 30px 9px 12px;
    color: {TEXT};
    font-size: 15px;
    min-height: 20px;
}}
QSpinBox:hover {{ border-color: {ACCENT_HOVER}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 22px;
    border: none;
    background-color: {CARD_ALT};
}}
QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: {RADIUS_SM}px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: {RADIUS_SM}px; }}
QSpinBox::up-arrow {{ image: url("{_chevron_up}"); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url("{_chevron}"); width: 10px; height: 10px; }}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #0E1526;
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 10px 12px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
    font-size: 15px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{ border: 1px solid {ACCENT_HOVER}; }}
QLineEdit:disabled, QTextEdit:disabled {{ color: {MUTED_DARK}; }}
QLineEdit#search {{ padding-left: 38px; font-size: 16px; }}

QComboBox {{
    background-color: #0E1526;
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 9px 38px 9px 12px;
    color: {TEXT};
    min-height: 20px;
    font-size: 15px;
}}
QComboBox:hover {{ border-color: {ACCENT_HOVER}; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    image: url("{_chevron}");
    width: 14px;
    height: 14px;
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}}

QCheckBox {{ background: transparent; color: {TEXT_DIM}; spacing: 9px; font-size: 15px; }}
QCheckBox::indicator {{
    width: 20px; height: 20px;
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: #0E1526;
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT_HOVER}; }}
QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT_HOVER}; }}

QRadioButton {{ background: transparent; color: {TEXT_DIM}; spacing: 9px; font-size: 15px; }}
QRadioButton::indicator {{
    width: 18px; height: 18px; border-radius: 9px;
    border: 1px solid {BORDER}; background-color: #0E1526;
}}
QRadioButton::indicator:checked {{ background-color: {ACCENT}; border: 4px solid {BG}; }}

QSlider::groove:horizontal {{
    height: 6px; background: #1C2740; border-radius: 3px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: #FFFFFF; border: 3px solid {ACCENT};
    width: 14px; height: 14px; margin: -6px 0; border-radius: 10px;
}}
QSlider::handle:horizontal:hover {{ border-color: {ACCENT_HOVER}; }}

QProgressBar {{
    background-color: #131B2C; border: none; border-radius: 6px;
    height: 10px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 6px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #253049; border-radius: 5px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #253049; border-radius: 5px; min-width: 32px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QTableWidget {{
    background-color: transparent;
    border: none;
    gridline-color: {BORDER_SOFT};
    color: {TEXT_DIM};
    font-size: 14px;
}}
QTableWidget::item {{ padding: 8px; border: none; }}
QTableWidget::item:selected {{ background-color: {ACCENT_SOFT}; color: #FFFFFF; }}
QHeaderView::section {{
    background-color: {CARD_ALT};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER_SOFT};
    padding: 9px;
    font-size: 13px;
    font-weight: 700;
}}
QTableCornerButton::section {{ background-color: {CARD_ALT}; border: none; }}

QTabWidget::pane {{ border: 1px solid {BORDER_SOFT}; border-radius: {RADIUS_SM}px; background: {CARD}; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 9px 18px;
    border-radius: 9px; margin-right: 6px; font-size: 15px;
}}
QTabBar::tab:selected {{ background: {ACCENT_SOFT}; color: #FFFFFF; font-weight: 700; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QListWidget {{ background-color: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 9px 10px; border-radius: 8px; color: {TEXT_DIM}; }}
QListWidget::item:hover {{ background-color: {CARD_ALT}; }}
QListWidget::item:selected {{ background-color: {ACCENT_SOFT}; color: #FFFFFF; }}

QToolTip {{
    background-color: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px 9px;
    border-radius: 6px;
}}
QMenu {{ background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 8px 18px; border-radius: 7px; color: {TEXT_DIM}; }}
QMenu::item:selected {{ background-color: {ACCENT_SOFT}; color: #FFFFFF; }}

QMessageBox {{ background-color: {CARD}; }}
QMessageBox QLabel {{ color: {TEXT}; }}
QSplitter::handle {{ background-color: {BORDER_SOFT}; }}
QGroupBox {{
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS_SM}px;
    margin-top: 14px;
    padding: 12px;
    color: {MUTED};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT_HOVER}; }}
"""
