"""Install / verify the Playwright chromium build, also from a frozen exe."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def browsers_path():
    return os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ms-playwright")


def installed_builds():
    path = browsers_path()
    if not os.path.isdir(path):
        return []
    return sorted(name for name in os.listdir(path) if name.startswith("chromium"))


def _command():
    if getattr(sys, "frozen", False):
        try:
            from playwright._impl._driver import compute_driver_executable
            driver = compute_driver_executable()
            node, cli = driver[0], driver[1]
            return [node, cli, "install", "chromium"]
        except Exception:
            return None
    return [sys.executable, "-m", "playwright", "install", "chromium"]


def install(progress=None, log=None):
    builds = installed_builds()
    if builds:
        if log:
            log("Playwright ব্রাউজার আগেই আছে: " + ", ".join(builds), "ok")
        return {"ok": True, "builds": builds, "already": True}

    command = _command()
    if not command:
        if log:
            log("ড্রাইভার খুঁজে পাওয়া যায়নি", "error")
        return {"ok": False, "builds": [], "error": "driver missing"}

    if progress:
        progress("Chromium নামানো হচ্ছে (প্রায় ১৫০ MB)…")
    if log:
        log("চালু: " + " ".join(command), "dim")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="ignore")
        for line in process.stdout or []:
            line = line.strip()
            if line and log:
                log(line, "dim")
        process.wait(timeout=1800)
    except Exception as exc:
        if log:
            log(f"ইনস্টল ব্যর্থ: {exc}", "error")
        return {"ok": False, "builds": installed_builds(), "error": str(exc)}

    builds = installed_builds()
    if log:
        log("ব্রাউজার ইনস্টল সম্পন্ন" if builds else "ইনস্টল হয়নি", "ok" if builds else "error")
    return {"ok": bool(builds), "builds": builds}


def verify(log=None):
    """Quick sanity check that a browser can actually start."""
    builds = installed_builds()
    result = {"browsers_path": browsers_path(), "builds": builds}
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=True)
            version = browser.version
            browser.close()
            result["ok"] = True
            result["version"] = version
        finally:
            pw.stop()
    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)
    if log:
        if result.get("ok"):
            log(f"ব্রাউজার ঠিক আছে (Chromium {result.get('version')})", "ok")
        else:
            log("ব্রাউজার চালু করা যায়নি: " + str(result.get("error")), "error")
    return result


if __name__ == "__main__":
    print(verify(log=lambda m, level="info": print(m)))
