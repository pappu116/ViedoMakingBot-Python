"""In-app media playback: audio preview and video player widgets."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QHBoxLayout, QSlider, QVBoxLayout, QWidget

from ui import theme, widgets


class AudioPreview(QWidget):
    """Compact audio player used by the voice step's listen button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.output.setVolume(0.9)
        self.player.errorOccurred.connect(self._on_error)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.play_button = widgets.icon_button("play", on_click=self.toggle, tooltip="শুনুন")
        layout.addWidget(self.play_button)
        self.status = widgets.label("কণ্ঠ শুনতে চাপুন", "muted")
        layout.addWidget(self.status, 1)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)
        self._duration = 0

    def _on_error(self, *_args):
        message = ""
        try:
            message = self.player.errorString()
        except Exception:
            pass
        self.status.setText("চালানো যায়নি" + (f": {message}" if message else ""))

    def play(self, path):
        if not path or not os.path.exists(path):
            self.status.setText("অডিও ফাইল নেই")
            return
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.player.play()
        self.status.setText("বাজছে… " + os.path.basename(path))

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_position(self, position):
        if self._duration:
            self.status.setText(f"বাজছে… {position // 1000}s / {self._duration // 1000}s")

    def _on_state(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_button.setIcon(_play_icon("pause"))
        else:
            self.play_button.setIcon(_play_icon("play"))


def _play_icon(name):
    from ui import icons
    return icons.icon(name, theme.TEXT, 20)


class VideoPlayer(QWidget):
    """Simple video player (play/pause, seek, time) for the render preview."""

    ended = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.output.setVolume(0.85)
        self.video = QVideoWidget(self)
        self.video.setStyleSheet("background-color: #05080F; border: none;")
        self.player.setVideoOutput(self.video)
        self.player.errorOccurred.connect(self._on_error)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.video, 1)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.play_button = widgets.icon_button("play", on_click=self.toggle, tooltip="চালান")
        controls.addWidget(self.play_button)
        self.position = QSlider(Qt.Horizontal)
        self.position.setRange(0, 1000)
        self.position.sliderMoved.connect(self._seek)
        controls.addWidget(self.position, 1)
        self.time_label = widgets.label("০:০০", "muted")
        controls.addWidget(self.time_label)
        layout.addLayout(controls)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_status)
        self._duration = 0

    def _on_error(self, *_args):
        try:
            self.time_label.setText("ত্রুটি: " + self.player.errorString())
        except Exception:
            pass

    def load(self, path, autoplay=False):
        if not path or not os.path.exists(path):
            return False
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        if autoplay:
            self.player.play()
        return True

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()

    def _seek(self, value):
        if self._duration:
            self.player.setPosition(int(self._duration * value / 1000))

    def _on_duration(self, duration):
        self._duration = duration
        self.time_label.setText(_format_ms(duration))

    def _on_position(self, position):
        if not self.position.isSliderDown() and self._duration:
            self.position.setValue(int(position * 1000 / self._duration))
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(self._duration)}")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlayingState
        self.play_button.setIcon(_play_icon("pause" if playing else "play"))

    def _on_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.ended.emit()


def _format_ms(ms):
    seconds = max(0, int(ms / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"
