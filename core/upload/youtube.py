"""YouTube Studio uploader (Playwright). Login is detected, never asked on stdin."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.upload import browser as browser_lib
from core.upload.selectors import YOUTUBE as SEL

STUDIO_URL = "https://studio.youtube.com"
GOOGLE_COOKIES = ("SID", "HSID", "SSID", "APISID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID")

VISIBILITY_MAP = {
    "public": "visibility_public",
    "unlisted": "visibility_unlisted",
    "private": "visibility_private",
}


def _status(on_status, message):
    if on_status:
        try:
            on_status(message)
        except Exception:
            pass
    browser_lib.log("[youtube] " + str(message))


def is_logged_in(page, context):
    url = browser_lib.current_url(page)
    if "accounts.google.com" in url or "/signin" in url or "/ServiceLogin" in url:
        return False
    cookies = browser_lib.cookie_names(context)
    if not any(name in cookies for name in GOOGLE_COOKIES):
        return False
    if "studio.youtube.com" in url:
        return browser_lib.find_first(page, SEL["signed_in"], timeout_ms=4000) is not None
    return True


def check_session(profile, headless=True):
    """Open the profile, report whether the saved session still works."""
    pw, context, page = browser_lib.launch(profile, "youtube", headless=headless)
    try:
        browser_lib.goto(page, STUDIO_URL)
        browser_lib.human_pause(2.0, 3.5)
        logged_in = is_logged_in(page, context)
        if logged_in:
            browser_lib.mark_session(profile, "youtube")
        return {"logged_in": logged_in, "url": browser_lib.current_url(page)}
    finally:
        browser_lib.close(pw, context)


def login(profile, headless=False, timeout=900, on_status=None, cancel=None):
    """Open a browser so the user can log in; detect success automatically."""
    pw, context, page = browser_lib.launch(profile, "youtube", headless=headless)
    try:
        _status(on_status, "ব্রাউজারে YouTube Studio খোলা হচ্ছে…")
        browser_lib.goto(page, STUDIO_URL)
        _status(on_status, "ব্রাউজারে লগইন করুন — হয়ে গেলে অ্যাপ নিজে থেকেই ধরবে")
        if is_logged_in(page, context):
            browser_lib.mark_session(profile, "youtube")
            _status(on_status, "আগেই লগইন করা আছে")
            return {"logged_in": True, "already": True}

        detected = browser_lib.wait_until(
            lambda: is_logged_in(page, context),
            timeout=timeout, poll=2.0, cancel=cancel,
        )
        if detected:
            browser_lib.human_pause(1.5, 2.5)
            browser_lib.mark_session(profile, "youtube")
            _status(on_status, "লগইন সফল — সেশন সেভ হয়েছে")
        else:
            _status(on_status, "সময় শেষ / বাতিল — লগইন হয়নি")
        return {"logged_in": bool(detected), "url": browser_lib.current_url(page)}
    finally:
        browser_lib.close(pw, context)


def upload(video_path, title, description="", tags=None, profile="acc1", headless=False,
           visibility="public", made_for_kids=False, dry_run=False, on_status=None,
           cancel=None):
    """Upload one video to YouTube Studio. Returns {ok, url, message, screenshot}."""
    tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        raise RuntimeError("ভিডিও ফাইল পাওয়া যায়নি: " + video_path)

    pw, context, page = browser_lib.launch(profile, "youtube", headless=headless)
    result = {"ok": False, "url": "", "message": "", "screenshot": ""}
    try:
        _status(on_status, "YouTube Studio খোলা হচ্ছে…")
        browser_lib.goto(page, STUDIO_URL)
        browser_lib.human_pause(2.5, 4.0)
        if not is_logged_in(page, context):
            raise RuntimeError("YouTube-এ লগইন করা নেই — আগে Accounts পেজ থেকে লগইন করুন")

        _status(on_status, "Create → Upload videos")
        browser_lib.click_first(page, SEL["create_button"], label="Create")
        browser_lib.human_pause(0.8, 1.6)
        browser_lib.click_first(page, SEL["upload_menu_item"], label="Upload videos")
        browser_lib.human_pause(1.5, 2.5)

        _status(on_status, "ভিডিও ফাইল দেয়া হচ্ছে…")
        file_locator = browser_lib.find_first(page, SEL["file_input"], timeout_ms=20000)
        if file_locator is None:
            raise RuntimeError("আপলোড ইনপুট পাওয়া যায়নি")
        file_locator.set_input_files(video_path)

        _status(on_status, "ফাইল আপলোড হচ্ছে, অপেক্ষা করুন…")
        browser_lib.find_first(page, SEL["dialog_title"], timeout_ms=60000)

        browser_lib.human_pause(2.0, 3.5)
        _status(on_status, "টাইটেল ও ডেসক্রিপশন লেখা হচ্ছে…")
        browser_lib.fill_first(page, SEL["title_box"], title[:95], label="title")
        if description:
            body = description
            if tags:
                body += "\n\n" + " ".join("#" + t.replace(" ", "") for t in tags[:12])
            browser_lib.fill_first(page, SEL["description_box"], body, label="description")

        if tags:
            try:
                browser_lib.click_first(page, SEL["show_more"], timeout_ms=6000,
                                        required=False, label="Show more")
                browser_lib.human_pause(0.4, 0.9)
                browser_lib.fill_first(page, SEL["tags_box"], ", ".join(tags[:15]),
                                       timeout_ms=6000, required=False, label="tags")
            except Exception:
                pass

        _status(on_status, "দর্শক সেটিং (kids)…")
        browser_lib.click_first(page, SEL["not_kids"], timeout_ms=10000,
                                required=False, label="not made for kids")

        if visibility != "private":
            _status(on_status, "চেক শেষ হওয়ার অপেক্ষা…")
            browser_lib.wait_until(
                lambda: browser_lib.find_first(page, SEL["checks_complete"], timeout_ms=1500) is not None,
                timeout=180, poll=4.0, cancel=cancel)

        _status(on_status, "ভিজিবিলিটি: " + visibility)
        browser_lib.click_first(page, SEL[VISIBILITY_MAP.get(visibility, "visibility_public")],
                               timeout_ms=15000, required=False, label="visibility")
        browser_lib.human_pause(0.6, 1.4)

        screenshot = ""
        if dry_run:
            screenshot = browser_lib.screenshot(page, "youtube_dryrun")
            result.update({"ok": True, "dry_run": True, "screenshot": screenshot,
                           "message": "ড্রাই-রান: সব ফিলাপ হয়েছে, Publish চাপা হয়নি"})
            _status(on_status, result["message"])
            return result

        _status(on_status, "Publish করা হচ্ছে…")
        browser_lib.click_first(page, SEL["publish_button"], label="Publish")
        browser_lib.human_pause(6.0, 9.0)
        link_locator = browser_lib.find_first(page, SEL["video_link"], timeout_ms=15000)
        url = ""
        if link_locator is not None:
            try:
                url = link_locator.get_attribute("href") or link_locator.inner_text()
            except Exception:
                url = ""
        result.update({"ok": True, "url": url, "message": "YouTube-এ আপলোড সম্পন্ন"})
        _status(on_status, result["message"])
        return result
    except Exception as exc:
        result["screenshot"] = browser_lib.screenshot(page, "youtube_error")
        result["message"] = str(exc)
        _status(on_status, "ব্যর্থ: " + str(exc))
        raise
    finally:
        browser_lib.close(pw, context)
