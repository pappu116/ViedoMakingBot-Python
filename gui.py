"""YTFB Studio — desktop app entry point (PySide6).

Run:  python gui.py
Test: python gui.py --selftest   (renders a tiny video headlessly and writes a report)
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_bundle_browsers = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browsers")
if getattr(sys, "frozen", False):
    _bundle_browsers = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)),
                                    "browsers")


def _prepare_browser_path():
    """Point Playwright at the right browser folder.

    Frozen builds get PLAYWRIGHT_BROWSERS_PATH=0 from the PyInstaller runtime hook,
    which means 'only browsers shipped inside the app'. We ship browsers next to the
    exe for the --with-browser build; otherwise the user installs them from the Tools
    page, so fall back to the per-user default location.
    """
    if os.path.isdir(_bundle_browsers):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _bundle_browsers
        return _bundle_browsers
    current = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if current in ("0", ""):
        default = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                               "ms-playwright")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = default
        return default
    return current


BROWSERS_PATH = _prepare_browser_path()

from paths import ensure_dirs, output_dir  # noqa: E402

ensure_dirs()

APP_NAME = "YTFB Studio"
LOCK_NAME = "ytfb-studio-single-instance"


def _write_report(text):
    try:
        os.makedirs(output_dir(), exist_ok=True)
        with open(os.path.join(output_dir(), "selftest_result.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        pass


def run_selftest():
    """Offline sanity check used for the frozen build as well."""
    lines = []
    try:
        from core import pipeline
        from core.script import from_own_text

        script = from_own_text(
            "এটি একটি পরীক্ষা। অ্যাপ ঠিকভাবে ভিডিও বানাতে পারে। ছোট এই ভিডিওটি পরীক্ষার জন্য।",
            title="সেলফ টেস্ট", lang="bn")
        opts = {
            "aspect": "mobile", "style": "cinematic", "duration": 8, "fps": 24,
            "images": False, "image_source": "none", "subtitles": True, "music": True,
            "music_volume": 0.15, "voiceover": True, "lang": "bn", "gender": "female",
            "accent": "bd", "voice_engine": "auto", "progress_bar": True,
            "watermark": "@selftest",
        }
        result = pipeline.build_video(script, opts, log=lambda m, level="info": lines.append(str(m)))
        path = result["video"]
        size = os.path.getsize(path) if os.path.exists(path) else 0
        lines.append(f"VIDEO={path}")
        lines.append(f"SIZE={size}")
        lines.append(f"DURATION={result.get('duration')}")
        lines.append(f"ENGINE={(result.get('audio') or {}).get('engine')}")
        lines.append("OK" if size > 10000 else "FAIL: output too small")
    except Exception as exc:
        lines.append("FAIL: " + str(exc))
        lines.append(traceback.format_exc())
    report = "\n".join(lines)
    _write_report(report)
    return report


def _single_instance(app):
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    socket = QLocalSocket()
    socket.connectToServer(LOCK_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return None
    server = QLocalServer()
    QLocalServer.removeServer(LOCK_NAME)
    server.listen(LOCK_NAME)
    return server


def main():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)

    server = _single_instance(app)
    if server is None:
        return 0

    from ui import icons, theme
    from ui.main_window import MainWindow
    from ui.state import Studio

    app.setWindowIcon(icons.app_icon())
    theme.apply(app)

    studio = Studio()
    window = MainWindow(studio)
    window.show()

    if server:
        def _incoming():
            try:
                while server.hasPendingConnections():
                    connection = server.nextPendingConnection()
                    connection.readyRead.connect(lambda: None)
                    window.showNormal()
                    window.raise_()
                    window.activateWindow()
            except Exception:
                pass
        server.newConnection.connect(_incoming)

    studio.log("YTFB Studio চালু হয়েছে — সব ফ্রি, কোনো paid API ছাড়াই।", "ok")
    studio.log("শুরু করতে ‘ভিডিও তৈরি করুন’ চাপুন।", "dim")
    return app.exec()


def run_browsertest():
    """Verify the Playwright browser stack from inside the packaged app."""
    lines = []
    try:
        from tools import playwright_install
        lines.append("frozen=" + str(getattr(sys, "frozen", False)))
        lines.append("browsers env=" + repr(os.environ.get("PLAYWRIGHT_BROWSERS_PATH")))
        lines.append("browsers dir=" + str(BROWSERS_PATH))
        result = playwright_install.verify(
            log=lambda message, level="info": lines.append(str(message)))
        lines.append(f"browsers_path={result.get('browsers_path')}")
        lines.append(f"builds={result.get('builds')}")
        lines.append(f"version={result.get('version')}")
        lines.append("OK" if result.get("ok") else "FAIL: " + str(result.get("error")))
    except Exception as exc:
        lines.append("FAIL: " + str(exc))
        lines.append(traceback.format_exc())
    report = "\n".join(lines)
    _write_report("BROWSER TEST\n" + report)
    return report


def run_cliptest():
    """Decode one cached stock clip inside the packaged app (verifies webm support)."""
    lines = []
    try:
        from core import video as video_lib
        from paths import data_dir

        clips_dir = os.path.join(data_dir(), "cache", "videos")
        clips = []
        if os.path.isdir(clips_dir):
            clips = [os.path.join(clips_dir, name) for name in sorted(os.listdir(clips_dir))
                     if name.lower().endswith((".webm", ".ogv", ".mp4"))]
        lines.append(f"clips found: {len(clips)}")
        if not clips:
            lines.append("SKIP: no cached clip (run a video with stock footage first)")
            return "\n".join(lines)

        plan = {
            "width": 540, "height": 960, "fps": 24, "duration": 2.0,
            "shots": [{
                "start": 0.0, "duration": 2.0, "background": clips[0],
                "background_kind": "video", "zoom_from": 1.0, "zoom_to": 1.05,
                "pan_from": (0, 0), "pan_to": (0, 0), "overlays": [],
            }],
            "progress_bar": None, "watermark": None,
        }
        composer = video_lib.FrameComposer(plan)
        try:
            frame = composer.frame(0.8)
            lines.append(f"frame shape={getattr(frame, 'shape', None)} dtype={getattr(frame, 'dtype', None)}")
            ok = getattr(frame, "shape", (0,))[:2] == (960, 540)
        finally:
            composer.close()
        lines.append("OK" if ok else "FAIL: unexpected frame")
    except Exception as exc:
        lines.append("FAIL: " + str(exc))
        lines.append(traceback.format_exc())
    report = "\n".join(lines)
    _write_report("CLIP TEST\n" + report)
    return report


def _safe_print(text):
    try:
        print(text)
    except Exception:
        try:
            print(text.encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _safe_print(run_selftest())
        sys.exit(0)
    if "--browsertest" in sys.argv:
        _safe_print(run_browsertest())
        sys.exit(0)
    if "--cliptest" in sys.argv:
        _safe_print(run_cliptest())
        sys.exit(0)
    sys.exit(main())
