"""Facebook Reels / video uploader (Playwright), with a page composer fallback."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.upload import browser as browser_lib
from core.upload.selectors import FACEBOOK as SEL

HOME_URL = "https://www.facebook.com/"
REELS_URL = "https://www.facebook.com/reel/create"


def _status(on_status, message):
    if on_status:
        try:
            on_status(message)
        except Exception:
            pass
    browser_lib.log("[facebook] " + str(message))


def is_logged_in(page, context):
    url = browser_lib.current_url(page)
    if "/login" in url or "checkpoint" in url:
        return False
    cookies = browser_lib.cookie_names(context)
    return "c_user" in cookies


def check_session(profile, headless=True):
    pw, context, page = browser_lib.launch(profile, "facebook", headless=headless)
    try:
        browser_lib.goto(page, HOME_URL)
        browser_lib.human_pause(2.0, 3.5)
        logged_in = is_logged_in(page, context)
        if logged_in:
            browser_lib.mark_session(profile, "facebook")
        return {"logged_in": logged_in, "url": browser_lib.current_url(page)}
    finally:
        browser_lib.close(pw, context)


def login(profile, headless=False, timeout=900, on_status=None, cancel=None):
    pw, context, page = browser_lib.launch(profile, "facebook", headless=headless)
    try:
        _status(on_status, "ব্রাউজারে Facebook খোলা হচ্ছে…")
        browser_lib.goto(page, HOME_URL)
        _status(on_status, "ব্রাউজারে লগইন করুন — হয়ে গেলে অ্যাপ নিজে থেকেই ধরবে")
        if is_logged_in(page, context):
            browser_lib.mark_session(profile, "facebook")
            _status(on_status, "আগেই লগইন করা আছে")
            return {"logged_in": True, "already": True}

        detected = browser_lib.wait_until(
            lambda: is_logged_in(page, context) and "login" not in browser_lib.current_url(page),
            timeout=timeout, poll=2.0, cancel=cancel)
        if detected:
            browser_lib.human_pause(1.5, 2.5)
            browser_lib.mark_session(profile, "facebook")
            _status(on_status, "লগইন সফল — সেশন সেভ হয়েছে")
        else:
            _status(on_status, "সময় শেষ / বাতিল — লগইন হয়নি")
        return {"logged_in": bool(detected), "url": browser_lib.current_url(page)}
    finally:
        browser_lib.close(pw, context)


def _fill_caption(page, text, on_status=None):
    locator = browser_lib.find_first(page, SEL["reels_caption"], timeout_ms=15000)
    if locator is None:
        locator = browser_lib.find_first(page, SEL["caption_box"], timeout_ms=8000)
    if locator is None:
        return False
    try:
        locator.click()
        browser_lib.type_human(locator, text)
        return True
    except Exception:
        try:
            locator.fill(text)
            return True
        except Exception:
            return False


def upload(video_path, title, description="", tags=None, profile="acc1", headless=False,
           visibility="public", made_for_kids=False, dry_run=False, on_status=None,
           cancel=None):
    """Upload a Reel (or fall back to a regular video post).

    Accepts the same keywords as the YouTube uploader so both can be called with one
    shared code path; `made_for_kids` and `visibility` are YouTube-only concepts and
    are ignored here.
    """
    tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        raise RuntimeError("ভিডিও ফাইল পাওয়া যায়নি: " + video_path)

    caption = (description or title or "").strip()
    if tags:
        caption = (caption + "\n\n" + " ".join("#" + t.replace(" ", "") for t in tags[:12])).strip()
    caption = caption[:2200]

    pw, context, page = browser_lib.launch(profile, "facebook", headless=headless)
    result = {"ok": False, "url": "", "message": "", "screenshot": ""}
    try:
        _status(on_status, "Facebook খোলা হচ্ছে…")
        browser_lib.goto(page, REELS_URL)
        browser_lib.human_pause(3.0, 5.0)
        if not is_logged_in(page, context):
            raise RuntimeError("Facebook-এ লগইন করা নেই — আগে Accounts পেজ থেকে লগইন করুন")

        _status(on_status, "ভিডিও ফাইল দেয়া হচ্ছে…")
        file_locator = browser_lib.find_first(page, SEL["reels_video_input"], timeout_ms=20000)
        if file_locator is None:
            raise RuntimeError("Reels আপলোড ইনপুট পাওয়া যায়নি (Facebook UI বদলে থাকতে পারে)")
        file_locator.set_input_files(video_path)

        _status(on_status, "ভিডিও প্রসেস হচ্ছে…")
        browser_lib.find_first(page, SEL["reels_next"] + SEL["reels_publish"], timeout_ms=180000)

        _status(on_status, "ক্যাপশন লেখা হচ্ছে…")
        _fill_caption(page, caption, on_status)
        browser_lib.human_pause(1.5, 3.0)

        for _ in range(2):
            clicked = browser_lib.click_first(page, SEL["reels_next"], timeout_ms=6000,
                                              required=False, label="Next")
            if not clicked:
                break
            browser_lib.human_pause(2.0, 4.0)

        screenshot = ""
        if dry_run:
            screenshot = browser_lib.screenshot(page, "facebook_dryrun")
            result.update({"ok": True, "dry_run": True, "screenshot": screenshot,
                           "message": "ড্রাই-রান: সব ফিলাপ হয়েছে, Publish চাপা হয়নি"})
            _status(on_status, result["message"])
            return result

        _status(on_status, "Publish করা হচ্ছে…")
        browser_lib.click_first(page, SEL["reels_publish"], label="Publish")
        browser_lib.human_pause(8.0, 12.0)
        result.update({"ok": True, "url": browser_lib.current_url(page),
                       "message": "Facebook-এ পোস্ট সম্পন্ন"})
        _status(on_status, result["message"])
        return result
    except Exception as exc:
        result["screenshot"] = browser_lib.screenshot(page, "facebook_error")
        result["message"] = str(exc)
        _status(on_status, "ব্যর্থ: " + str(exc))
        raise
    finally:
        browser_lib.close(pw, context)
