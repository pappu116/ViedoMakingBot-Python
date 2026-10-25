"""Browser session helpers: persistent profiles, login detection, resilient clicking."""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from paths import ensure_dirs, logs_dir, profiles_dir

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
VIEWPORT = {"width": 1366, "height": 850}
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-infobars",
]


def debug_dir():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "output", "_upload_debug")
    os.makedirs(path, exist_ok=True)
    return path


def profile_dir(profile, platform):
    ensure_dirs()
    path = os.path.join(profiles_dir(), profile, platform + "_profile")
    os.makedirs(path, exist_ok=True)
    return path


def session_marker(profile, platform):
    return os.path.join(profiles_dir(), profile, platform + ".session")


def mark_session(profile, platform):
    ensure_dirs()
    path = session_marker(profile, platform)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(str(time.time()))
    return path


def has_session(profile, platform):
    return os.path.exists(session_marker(profile, platform))


def forget_session(profile, platform):
    path = session_marker(profile, platform)
    if os.path.exists(path):
        os.remove(path)
    return True


def session_age_days(profile, platform):
    path = session_marker(profile, platform)
    if not os.path.exists(path):
        return None
    return round((time.time() - os.path.getmtime(path)) / 86400.0, 1)


def log(message):
    try:
        ensure_dirs()
        with open(os.path.join(logs_dir(), "run.log"), "a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except OSError:
        pass


def launch(profile, platform, headless=False):
    """Open a persistent-context chromium window and return (playwright, context, page)."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    kwargs = {
        "user_data_dir": profile_dir(profile, platform),
        "headless": bool(headless),
        "args": LAUNCH_ARGS,
        "viewport": VIEWPORT,
        "user_agent": DEFAULT_UA,
        "locale": "en-US",
        "accept_downloads": True,
    }
    try:
        context = pw.chromium.launch_persistent_context(**kwargs)
    except Exception:
        kwargs.pop("viewport", None)
        kwargs.pop("user_agent", None)
        context = pw.chromium.launch_persistent_context(**kwargs)
    page = context.pages[0] if context.pages else context.new_page()
    try:
        page.set_default_timeout(20000)
    except Exception:
        pass
    return pw, context, page


def close(pw, context):
    for target in (context, pw):
        try:
            target.close() if target is context else target.stop()
        except Exception:
            pass


def human_pause(a=0.8, b=2.0):
    time.sleep(random.uniform(a, b))


def type_human(locator, text, min_delay=35, max_delay=95):
    try:
        locator.click()
    except Exception:
        pass
    for char in str(text):
        locator.type(char, delay=random.randint(min_delay, max_delay))


def find_first(page, selectors, timeout_ms=8000, visible=True):
    """Return the first locator that exists, trying each selector in order."""
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() and (not visible or locator.is_visible()):
                    return locator
            except Exception:
                continue
        time.sleep(0.4)
    return None


def click_first(page, selectors, timeout_ms=15000, required=True, force=False, label=""):
    locator = find_first(page, selectors, timeout_ms=timeout_ms)
    if locator is None:
        if required:
            raise RuntimeError(f"বাটন পাওয়া যায়নি: {label or selectors[0]}")
        return False
    try:
        locator.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        pass
    try:
        locator.click(timeout=8000)
    except Exception:
        if force:
            locator.click(timeout=8000, force=True)
        else:
            try:
                locator.click(timeout=8000, force=True)
            except Exception:
                if required:
                    raise
                return False
    human_pause(0.4, 1.1)
    return True


def fill_first(page, selectors, text, timeout_ms=12000, required=True, label="", human=True):
    locator = find_first(page, selectors, timeout_ms=timeout_ms)
    if locator is None:
        if required:
            raise RuntimeError(f"ইনপুট পাওয়া যায়নি: {label or selectors[0]}")
        return False
    try:
        locator.click()
        locator.fill("")
        if human:
            type_human(locator, text)
        else:
            locator.fill(text)
    except Exception:
        try:
            locator.fill(text)
        except Exception:
            if required:
                raise
            return False
    human_pause(0.3, 0.9)
    return True


def screenshot(page, tag="debug"):
    try:
        path = os.path.join(debug_dir(), f"{tag}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        page.screenshot(path=path, full_page=False)
        return path
    except Exception:
        return ""


def goto(page, url, wait="domcontentloaded", retries=2):
    last = None
    for _ in range(max(1, retries)):
        try:
            page.goto(url, wait_until=wait, timeout=60000)
            return True
        except Exception as exc:
            last = exc
            time.sleep(2)
    if last:
        raise last
    return False


def current_url(page):
    try:
        return page.url or ""
    except Exception:
        return ""


def cookie_names(context):
    names = set()
    try:
        for cookie in context.cookies():
            names.add(cookie.get("name", ""))
    except Exception:
        pass
    return names


def wait_until(predicate, timeout=300, poll=2.0, cancel=None, on_tick=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cancel and cancel():
            return False
        try:
            if predicate():
                return True
        except Exception:
            pass
        if on_tick:
            try:
                on_tick()
            except Exception:
                pass
        time.sleep(poll)
    return False
