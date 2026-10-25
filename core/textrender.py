"""Bangla-safe text rendering with Qt (HarfBuzz shaping) onto offscreen images.

Used for both the UI and the video caption/title layers, so Bengali conjuncts
(যুক্তাক্ষর), matras and punctuation always render correctly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import fonts_dir, user_fonts_dir

_app = None
_families = []

BUNDLED_FONTS = [
    ("NotoSansBengali-Regular.ttf", "regular"),
    ("NotoSansBengali-SemiBold.ttf", "semibold"),
    ("NotoSansBengali-Bold.ttf", "bold"),
]

SYSTEM_FALLBACKS = [
    "Nirmala UI",
    "Nirmala UI Semilight",
    "Vrinda",
    "Shonar Bangla",
    "Segoe UI",
]


def ensure_qt():
    """Create a QGuiApplication when running headless (CLI) so fonts/painting work."""
    global _app
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QCoreApplication
    if QCoreApplication.instance() is not None:
        return QCoreApplication.instance()
    if os.name != "nt":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    return _app


def load_fonts():
    """Register bundled fonts and remember the best available family."""
    global _families
    if _families:
        return _families
    ensure_qt()
    from PySide6.QtGui import QFontDatabase

    families = []
    for folder in (fonts_dir(), user_fonts_dir()):
        if not os.path.isdir(folder):
            continue
        for name, _weight in BUNDLED_FONTS:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id != -1:
                    families.extend(QFontDatabase.applicationFontFamilies(font_id))
    available = set(QFontDatabase.families())
    for candidate in families:
        if candidate in available and candidate not in _families:
            _families.append(candidate)
    for candidate in SYSTEM_FALLBACKS:
        if candidate in available and candidate not in _families:
            _families.append(candidate)
    if not _families:
        _families = ["Sans Serif"]
    return _families


def family(bold=False):
    fams = load_fonts()
    return fams[0] if fams else "Sans Serif"


def make_font(size, bold=False, italic=False, family_name=None):
    ensure_qt()
    from PySide6.QtGui import QFont
    font = QFont(family_name or family(bold))
    font.setPixelSize(max(8, int(size)))
    font.setBold(bool(bold))
    font.setItalic(bool(italic))
    return font


def font_summary():
    load_fonts()
    return {
        "families": list(_families),
        "bundled": [name for name, _ in BUNDLED_FONTS
                    if any(os.path.exists(os.path.join(folder, name))
                           for folder in (fonts_dir(), user_fonts_dir()))],
    }


def layout_lines(text, font, max_width):
    """Break text into lines using Qt's Unicode line breaking (Bangla aware)."""
    from PySide6.QtGui import QTextLayout
    text = (text or "").replace("\r", "")
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        layout = QTextLayout(paragraph, font)
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max_width)
            start = line.textStart()
            length = line.textLength()
            piece = paragraph[start:start + length].strip()
            if piece:
                lines.append(piece)
        layout.endLayout()
    return lines or [""]


def _rgba(color, alpha=None):
    from PySide6.QtGui import QColor
    qcolor = QColor(color)
    if alpha is not None:
        qcolor.setAlpha(int(alpha))
    return qcolor


def draw_text_block(painter, text, font, color, rect, align="center", line_spacing=1.35,
                    shadow_color=None, shadow_offset=3):
    """Draw wrapped text inside rect, honouring Bangla shaping."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFontMetricsF

    lines = layout_lines(text, font, rect.width())
    metrics = QFontMetricsF(font)
    line_height = metrics.height() * line_spacing
    total_height = line_height * len(lines)
    y = rect.top() + max(0.0, (rect.height() - total_height) / 2.0)

    for line in lines:
        width = metrics.horizontalAdvance(line)
        if align == "left":
            x = rect.left()
        elif align == "right":
            x = rect.right() - width
        else:
            x = rect.left() + (rect.width() - width) / 2.0
        baseline = y + metrics.ascent() + (line_height - metrics.height()) / 2.0
        if shadow_color is not None:
            painter.setPen(shadow_color)
            painter.drawText(QPoint(int(x + shadow_offset), int(baseline + shadow_offset)), line)
        painter.setPen(color)
        painter.drawText(QPoint(int(x), int(baseline)), line)
        y += line_height
    return total_height


def measure_text(text, font, max_width, line_spacing=1.35):
    from PySide6.QtGui import QFontMetricsF
    lines = layout_lines(text, font, max_width)
    metrics = QFontMetricsF(font)
    return lines, metrics.height() * line_spacing * len(lines)


def _new_image(width, height):
    from PySide6.QtGui import QImage
    image = QImage(int(width), int(height), QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    return image


def _new_painter(image):
    from PySide6.QtGui import QPainter
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    return painter


def rounded_rect_png(path, size, box, radius, fill_color, border_color=None, border_width=2):
    """Standalone rounded rectangle layer (used for badges / bars / panels)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QBrush, QPen
    image = _new_image(*size)
    painter = _new_painter(image)
    rect = QRectF(*box)
    painter.setBrush(QBrush(_rgba(fill_color)))
    if border_color:
        painter.setPen(QPen(_rgba(border_color), border_width))
    else:
        painter.setPen(0)
    painter.drawRoundedRect(rect, radius, radius)
    painter.end()
    return save(image, path)


CAPTION_STYLES = {
    "bold": {
        "label_bn": "বোল্ড আউটলাইন", "label_en": "Bold outline",
        "color": "#FFFFFF", "outline": "#000000", "outline_width": 12, "box": None,
        "highlight": "#FFD400", "per_word": False,
    },
    "karaoke": {
        "label_bn": "কারাওকে হাইলাইট", "label_en": "Karaoke highlight",
        "color": "#FFFFFF", "outline": "#000000", "outline_width": 12, "box": None,
        "highlight": "#FFD400", "per_word": True,
    },
    "yellow": {
        "label_bn": "হলুদ হাইলাইট", "label_en": "Yellow highlight",
        "color": "#FFD400", "outline": "#000000", "outline_width": 13, "box": None,
        "highlight": "#FFFFFF", "per_word": False,
    },
    "box": {
        "label_bn": "বক্স", "label_en": "Box",
        "color": "#FFFFFF", "outline": "#00000000", "outline_width": 0, "box": "#000000E0",
        "highlight": "#FFD400", "per_word": True,
    },
    "classic": {
        "label_bn": "সাদামাটা", "label_en": "Classic",
        "color": "#FFFFFF", "outline": "#000000", "outline_width": 6, "box": None,
        "highlight": "#FFD400", "per_word": False,
    },
}
DEFAULT_CAPTION_STYLE = "bold"


def caption_style_names():
    return list(CAPTION_STYLES)


def caption_style_label(style, ui_lang="bn"):
    preset = CAPTION_STYLES.get(style, CAPTION_STYLES[DEFAULT_CAPTION_STYLE])
    return preset.get("label_" + ui_lang) or preset["label_en"]


def _draw_outlined_words(painter, lines, font, metrics, line_height, top, left, box_width,
                         color, outline_color, outline_width, highlight_index, highlight_color):
    """Draw words with a real stroke outline; optionally highlight one word."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen

    space = metrics.horizontalAdvance(" ")
    word_index = 0
    y = top
    for line in lines:
        words = [w for w in line.split(" ") if w]
        if not words:
            y += line_height
            continue
        widths = [metrics.horizontalAdvance(word) for word in words]
        total = sum(widths) + space * max(0, len(words) - 1)
        x = left + max(0.0, (box_width - total) / 2.0)
        baseline = y + metrics.ascent()
        for word, width in zip(words, widths):
            fill = highlight_color if word_index == highlight_index else color
            path = QPainterPath()
            path.addText(QPointF(x, baseline), font, word)
            if outline_width > 0:
                pen = QPen(QColor(outline_color), outline_width)
                pen.setJoinStyle(Qt.RoundJoin)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(fill)))
            painter.drawPath(path)
            x += width + space
            word_index += 1
        y += line_height
    return word_index


def caption_layers(prefix, size, text, style=DEFAULT_CAPTION_STYLE, font_size=64,
                   color=None, outline=None, outline_width=None, box_color=None,
                   highlight_color=None, accent=None, max_width_ratio=0.88,
                   position="bottom", margin_ratio=0.17, radius=20, padding=26,
                   line_spacing=1.22, uppercase=False, animate_words=None):
    """Render caption layer(s).

    Returns a list of layers: normally one, but per-word (karaoke) styles return one
    layer per word so the active word can be highlighted as it is spoken.
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QBrush, QFontMetricsF, QPen

    if str(prefix).lower().endswith(".png"):
        prefix = str(prefix)[:-4]
    preset = CAPTION_STYLES.get(style, CAPTION_STYLES[DEFAULT_CAPTION_STYLE])
    color = color or preset["color"]
    outline = outline if outline is not None else preset["outline"]
    if outline_width is None:
        outline_width = preset["outline_width"]
    if box_color is None:
        box_color = preset["box"]
    highlight_color = highlight_color or preset["highlight"]
    per_word = preset["per_word"] if animate_words is None else bool(animate_words)

    width, height = size
    font = make_font(font_size, bold=True)
    metrics = QFontMetricsF(font)
    max_width = int(width * max_width_ratio)
    display = text.upper() if uppercase else text
    lines = layout_lines(display, font, max_width) or [display]

    line_height = metrics.height() * line_spacing
    space = metrics.horizontalAdvance(" ")
    widest = max((sum(metrics.horizontalAdvance(w) for w in line.split(" ") if w)
                  + space * max(0, len([w for w in line.split(" ") if w]) - 1))
                 for line in lines)
    box_width = int(min(max_width, max(60.0, widest)) + padding * 2)
    box_height = int(line_height * len(lines) + padding * 2)

    left = (width - box_width) / 2.0
    if position == "top":
        top = int(height * 0.12)
    elif position == "center":
        top = int((height - box_height) / 2.0)
    else:
        top = int(height - box_height - height * margin_ratio)

    # room for the outline to bleed outside the glyphs
    bleed = int(max(outline_width, 0) / 2) + 6
    image_w = box_width + bleed * 2
    image_h = box_height + bleed * 2

    total_words = max(1, sum(len([w for w in line.split(" ") if w]) for line in lines))
    indices = range(total_words) if per_word else [-1]

    layers = []
    for index in indices:
        image = _new_image(image_w, image_h)
        painter = _new_painter(image)
        if box_color:
            painter.setPen(QPen(_rgba(accent), 4) if accent else Qt.NoPen)
            painter.setBrush(QBrush(_rgba(box_color)))
            painter.drawRoundedRect(QRectF(bleed, bleed, box_width, box_height), radius, radius)
        _draw_outlined_words(
            painter, lines, font, metrics, line_height,
            bleed + padding, bleed + padding, box_width,
            _rgba(color), _rgba(outline), int(outline_width),
            index, _rgba(highlight_color))
        painter.end()
        path = f"{prefix}_w{index}.png" if per_word else f"{prefix}.png"
        layers.append({
            "path": save(image, path),
            "x": int(left - bleed),
            "y": int(top - bleed),
            "width": image_w,
            "height": image_h,
            "word_index": index if per_word else None,
            "words": total_words,
        })
    return layers


def caption_png(path, size, text, font_size=56, color="#FFFFFF", box_color="#000000B0",
                accent=None, max_width_ratio=0.86, position="bottom", margin_ratio=0.18,
                radius=22, padding=26, bold=True, uppercase=False):
    """Single caption bubble (kept for the style preview and simple callers)."""
    layers = caption_layers(
        path, size, text, style="classic", font_size=font_size,
        color=color, box_color=box_color, accent=accent, max_width_ratio=max_width_ratio,
        position=position, margin_ratio=margin_ratio, radius=radius, padding=padding,
        uppercase=uppercase)
    return layers[0]


def text_layer_png(path, size, text, font_size=64, color="#FFFFFF", align="center",
                   valign="center", box_color=None, radius=28, padding=34,
                   bold=True, max_width_ratio=0.84, accent=None, accent_width=6,
                   margin_ratio=0.1, line_spacing=1.35, outline_width=0,
                   outline_color="#000000"):
    """Text block as a tight layer (small image + its x/y position).

    With outline_width > 0 the glyphs get a real stroke, which stays readable on any
    footage (used for the title and call-to-action cards).
    """
    from PySide6.QtCore import QRect, QRectF
    from PySide6.QtGui import QBrush, QFontMetricsF, QPen

    width, height = size
    font = make_font(font_size, bold=bold)
    metrics = QFontMetricsF(font)
    max_width = int(width * max_width_ratio)
    lines = layout_lines(text, font, max_width) or [text]
    line_height = metrics.height() * line_spacing
    text_height = line_height * len(lines)

    box_width = max_width if box_color else int(max_width * 0.9)
    box_height = int(text_height + padding * 2)
    left = (width - box_width) / 2.0
    if valign == "top":
        top = int(height * margin_ratio)
    elif valign == "bottom":
        top = int(height - box_height - height * margin_ratio)
    else:
        top = int((height - box_height) / 2.0)

    pad = int(max(outline_width, 0) / 2) + 10
    image = _new_image(box_width + pad * 2, box_height + pad * 2)
    painter = _new_painter(image)
    if box_color:
        box = QRectF(pad, pad, box_width, box_height)
        painter.setBrush(QBrush(_rgba(box_color)))
        if accent:
            painter.setPen(QPen(_rgba(accent), accent_width))
        else:
            painter.setPen(0)
        painter.drawRoundedRect(box, radius, radius)
    if outline_width > 0:
        _draw_outlined_words(painter, lines, font, metrics, line_height,
                             pad + padding, pad + padding, box_width,
                             _rgba(color), _rgba(outline_color), int(outline_width),
                             -1, _rgba(color))
    else:
        text_rect = QRect(pad + padding, pad + padding,
                          int(box_width - padding * 2), int(box_height - padding * 2))
        draw_text_block(painter, text, font, _rgba(color), text_rect, align=align,
                        line_spacing=line_spacing,
                        shadow_color=_rgba("#000000", 200) if not box_color else _rgba("#000000", 120),
                        shadow_offset=3)
    painter.end()
    return {
        "path": save(image, path),
        "x": int(left - pad),
        "y": int(top - pad),
        "width": box_width + pad * 2,
        "height": box_height + pad * 2,
    }


def progress_layer_png(path, size, ratio, color="#7C3AED", track_color="#FFFFFF33",
                       height=10, margin_ratio=0.0, radius=6):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QBrush
    width, height = size
    bar_height = max(4, int(height))
    image = _new_image(width, size[1] if len(size) > 1 else bar_height)
    painter = _new_painter(image)
    track = QRectF(0, 0, width, bar_height)
    painter.setPen(0)
    painter.setBrush(QBrush(_rgba(track_color)))
    painter.drawRoundedRect(track, radius, radius)
    filled = QRectF(0, 0, max(1.0, width * max(0.0, min(1.0, ratio))), bar_height)
    painter.setBrush(QBrush(_rgba(color)))
    painter.drawRoundedRect(filled, radius, radius)
    painter.end()
    return save(image, path)


def save(image, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    if not image.save(path):
        raise RuntimeError("ছবি সেভ করা যায়নি: " + str(path))
    return path
