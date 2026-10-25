"""Download a free Bengali font (SIL Open Font License) into media/assets/fonts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import ensure_dirs, fonts_dir, user_fonts_dir

FONTS = [
    ("NotoSansBengali-Regular.ttf",
     "https://raw.githubusercontent.com/notofonts/bengali/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-Regular.ttf"),
    ("NotoSansBengali-SemiBold.ttf",
     "https://raw.githubusercontent.com/notofonts/bengali/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-SemiBold.ttf"),
    ("NotoSansBengali-Bold.ttf",
     "https://raw.githubusercontent.com/notofonts/bengali/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-Bold.ttf"),
]

MIRRORS = {
    "NotoSansBengali-Regular.ttf": [
        "https://github.com/notofonts/bengali/raw/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-Regular.ttf",
    ],
    "NotoSansBengali-SemiBold.ttf": [
        "https://github.com/notofonts/bengali/raw/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-SemiBold.ttf",
    ],
    "NotoSansBengali-Bold.ttf": [
        "https://github.com/notofonts/bengali/raw/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-Bold.ttf",
    ],
}


def installed():
    ensure_dirs()
    return [name for name, _url in FONTS
            if any(os.path.exists(os.path.join(folder, name))
                   for folder in (fonts_dir(), user_fonts_dir()))]


def install(force=False, progress=None, log=None):
    """Download the bundled Bengali font; harmless if it fails (system fonts remain)."""
    import requests

    ensure_dirs()
    target_dir = user_fonts_dir()
    done, failed = [], []
    for name, url in FONTS:
        target = os.path.join(target_dir, name)
        bundled = os.path.join(fonts_dir(), name)
        if not force and (os.path.exists(target) or os.path.exists(bundled)):
            done.append(name)
            continue
        if progress:
            progress(f"ফন্ট নামানো হচ্ছে: {name}")
        saved = False
        for candidate in [url] + MIRRORS.get(name, []):
            try:
                resp = requests.get(candidate, timeout=60)
                resp.raise_for_status()
                if len(resp.content) < 20000:
                    raise RuntimeError("ফাইলটি খুব ছোট")
                with open(target, "wb") as fh:
                    fh.write(resp.content)
                done.append(name)
                if log:
                    log(f"সেভ হয়েছে: {name}", "ok")
                saved = True
                break
            except Exception as exc:
                if log:
                    log(f"ব্যর্থ {name}: {exc}", "dim")
        if not saved:
            failed.append(name)
    if log:
        if done:
            log(f"বাংলা ফন্ট প্রস্তুত: {len(done)}টি", "ok")
        if failed:
            log("ফন্ট নামানো যায়নি — সিস্টেম ফন্ট (Nirmala UI) ব্যবহার হবে", "warn")
    return {"done": done, "failed": failed}


if __name__ == "__main__":
    install(force=True, log=lambda message, level="info": print(message))
