"""Uploader API contract tests.

The GUI publish page and the CLI call youtube.upload()/facebook.upload() through one
shared code path, so their signatures must stay interchangeable. These tests bind the
exact keyword set the callers use — no browser or network needed.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.upload import facebook, youtube

SHARED_UPLOAD_KEYWORDS = dict(
    video_path="video.mp4",
    title="শিরোনাম",
    description="বিবরণ",
    tags=["tag"],
    profile="acc1",
    headless=True,
    visibility="public",
    made_for_kids=False,
    dry_run=True,
    on_status=lambda _message: None,
    cancel=lambda: False,
)

SHARED_LOGIN_KEYWORDS = dict(
    profile="acc1",
    headless=False,
    timeout=60,
    on_status=lambda _message: None,
    cancel=lambda: False,
)


def test_both_uploaders_accept_the_shared_keywords():
    for name, function in (("youtube.upload", youtube.upload),
                           ("facebook.upload", facebook.upload)):
        signature = inspect.signature(function)
        try:
            signature.bind(**SHARED_UPLOAD_KEYWORDS)
        except TypeError as exc:
            raise AssertionError(f"{name} কল করা যাবে না: {exc}") from exc


def test_both_login_functions_accept_the_shared_keywords():
    for name, function in (("youtube.login", youtube.login),
                           ("facebook.login", facebook.login)):
        signature = inspect.signature(function)
        try:
            signature.bind(**SHARED_LOGIN_KEYWORDS)
        except TypeError as exc:
            raise AssertionError(f"{name} কল করা যাবে না: {exc}") from exc


def test_check_session_signature():
    for name, function in (("youtube.check_session", youtube.check_session),
                           ("facebook.check_session", facebook.check_session)):
        inspect.signature(function).bind(profile="acc1", headless=True)


def test_uploaders_have_no_stray_parameters():
    """Guards against leftover junk arguments nobody passes."""
    allowed = set(SHARED_UPLOAD_KEYWORDS)
    for name, function in (("youtube.upload", youtube.upload),
                           ("facebook.upload", facebook.upload)):
        extras = set(inspect.signature(function).parameters) - allowed
        assert not extras, f"{name}-এ অপ্রয়োজনীয় প্যারামিটার: {sorted(extras)}"


def test_preview_and_synthesize_agree_with_the_ui():
    from core import tts
    ui_preview = dict(text="পরীক্ষা", lang="bn", gender="female", accent="bd", voice_id=None,
                      rate=0, pitch=0, engine="auto")
    inspect.signature(tts.preview).bind(**ui_preview)
    pipeline_synthesize = dict(text="পরীক্ষা", lang="bn", gender="female", accent="bd",
                               voice_id=None, rate=0, pitch=0, engine="auto")
    inspect.signature(tts.synthesize).bind(**pipeline_synthesize)
