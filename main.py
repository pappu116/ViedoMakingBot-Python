"""YTFB Studio command line interface.

Same engine as the desktop app:  generate | login | upload | run | voices | selftest | gui
"""
import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_bundle_browsers = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browsers")
if getattr(sys, "frozen", False):
    _bundle_browsers = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)),
                                    "browsers")

if os.path.isdir(_bundle_browsers):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _bundle_browsers
elif os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "") in ("0", ""):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ms-playwright")

from core import pipeline, script as script_lib, script_ai, settings as settings_lib, tts  # noqa: E402
from paths import ensure_dirs  # noqa: E402

ensure_dirs()


def _console(message, level="info"):
    prefix = {"info": "", "ok": "[ok] ", "warn": "[!] ", "error": "[x] ", "dim": "    "}
    print(prefix.get(level, "") + str(message))


def _progress(ratio, message=""):
    if message:
        print(f"  [{ratio * 100:5.1f}%] {message}")


def _options(args, cfg):
    video = cfg.get("video") or {}
    voice = cfg.get("voice") or {}
    upload = cfg.get("upload") or {}
    return {
        "aspect": getattr(args, "type", None) or video.get("aspect", "mobile"),
        "style": getattr(args, "style", None) or video.get("style", "cinematic"),
        "duration": getattr(args, "duration", None) or int(video.get("duration") or 45),
        "fps": int(video.get("fps") or 24),
        "images": (video.get("images", True) if getattr(args, "images", None) is None
                   else args.images == "on"),
        "image_source": getattr(args, "image_source", None) or video.get("image_source", "auto"),
        "subtitles": video.get("subtitles", True),
        "music": (video.get("music", True) if getattr(args, "music", None) is None
                  else bool(args.music)),
        "music_volume": float(video.get("music_volume", 0.18)),
        "ducking": video.get("ducking", True),
        "kenburns": video.get("kenburns", True),
        "progress_bar": video.get("progress_bar", True),
        "watermark": getattr(args, "watermark", None) or video.get("watermark", ""),
        "own_images_dir": getattr(args, "images_dir", None) or video.get("own_images_dir", ""),
        "voiceover": video.get("voiceover", True),
        "lang": getattr(args, "lang", None) or voice.get("lang", "bn"),
        "gender": getattr(args, "gender", None) or voice.get("gender", "female"),
        "accent": getattr(args, "accent", None) or voice.get("accent", "bd"),
        "voice": getattr(args, "voice", None) or voice.get("voice", ""),
        "voice_engine": getattr(args, "voice_engine", None) or voice.get("engine", "auto"),
        "visibility": upload.get("visibility", "public"),
        "made_for_kids": bool(upload.get("made_for_kids", False)),
        "headless": bool(upload.get("headless", False)),
        "dry_run": bool(getattr(args, "dry_run", False)),
    }


def _build_script(args, cfg):
    script = _build_script_inner(args, cfg)
    forced_lang = getattr(args, "lang", None)
    if forced_lang:
        # an explicit --lang overrides the detected language for the whole render
        script["lang"] = script_lib.lang_code(forced_lang)
    return script


def _build_script_inner(args, cfg):
    lang = getattr(args, "lang", None) or (cfg.get("voice") or {}).get("lang", "bn")
    topic = getattr(args, "topic", None) or ""
    provider = getattr(args, "ai", None) or (cfg.get("ai") or {}).get("provider", "pollinations")
    style = getattr(args, "style", None) or (cfg.get("video") or {}).get("style", "cinematic")
    duration = getattr(args, "duration", None) or int((cfg.get("video") or {}).get("duration") or 45)

    script_file = getattr(args, "script", None)
    if script_file:
        text = script_lib.load_script_file(script_file)
        _console("নিজের স্ক্রিপ্ট ব্যবহার করা হচ্ছে: " + os.path.basename(script_file), "ok")
        return script_lib.from_own_text(text, title=topic or None, lang=lang, style=style)
    if getattr(args, "own", None):
        return script_lib.from_own_text(args.own, title=topic or None, lang=lang, style=style)
    if topic:
        ai = cfg.get("ai") or {}
        script = script_ai.generate_script(
            topic, provider=provider, keys=ai.get("keys") or {},
            model=ai.get("model") or None, lang=lang,
            tone=ai.get("tone", "educational"), duration_sec=duration, style=style,
            ollama_url=ai.get("ollama_url"))
        for warning in script.get("warnings") or []:
            _console(warning, "warn")
        return script
    niche = getattr(args, "niche", None) or "all"
    _console("টেমপ্লেট থেকে স্ক্রিপ্ট: " + niche, "dim")
    return script_lib.from_template(niche, 1)[0]


def cmd_generate(args):
    cfg = settings_lib.load()
    opts = _options(args, cfg)
    script = _build_script(args, cfg)
    _console("টাইটেল: " + script["title"], "ok")
    result = pipeline.build_video(script, opts, progress=_progress, log=_console)
    print("ভিডিও সেভ হয়েছে:", result["video"])
    return result


def cmd_run(args):
    cfg = settings_lib.load()
    opts = _options(args, cfg)
    count = int(getattr(args, "count", None) or 1)
    profiles = [p.strip() for p in (getattr(args, "profiles", None) or "acc1").split(",") if p.strip()]
    platforms = [p.strip() for p in (getattr(args, "platforms", None) or "youtube,facebook").split(",")
                 if p.strip()]
    delay = (int((cfg.get("upload") or {}).get("delay_min", 30)),
             int((cfg.get("upload") or {}).get("delay_max", 90)))

    for index in range(count):
        _console(f"[{index + 1}/{count}] ভিডিও তৈরি হচ্ছে…")
        script = _build_script(args, cfg)
        result = pipeline.build_video(script, opts, progress=_progress, log=_console)
        print("ভিডিও:", result["video"])
        if getattr(args, "no_upload", False):
            continue
        for platform in platforms:
            module = None
            if platform == "youtube":
                from core.upload import youtube as module
            elif platform == "facebook":
                from core.upload import facebook as module
            else:
                _console("অজানা প্ল্যাটফর্ম: " + platform, "warn")
                continue
            for profile in profiles:
                _console(f"আপলোড → {platform} ({profile})", "dim")
                try:
                    outcome = module.upload(
                        result["video"], script["title"], script.get("description", ""),
                        script.get("tags", []), profile, headless=opts["headless"],
                        visibility=opts["visibility"], made_for_kids=opts["made_for_kids"],
                        dry_run=opts["dry_run"], on_status=lambda m: _console(m, "dim"))
                    _console(outcome.get("message", "সম্পন্ন"), "ok")
                except Exception as exc:
                    _console(f"ব্যর্থ: {exc}", "error")
                time.sleep(random.uniform(*delay))
    return True


def cmd_login(args):
    if args.platform == "youtube":
        from core.upload import youtube as module
    else:
        from core.upload import facebook as module
    _console("ব্রাউজারে লগইন করুন — হয়ে গেলে অ্যাপ নিজেই ধরবে", "ok")
    result = module.login(args.profile, headless=False, on_status=lambda m: _console(m, "dim"))
    _console("সেশন সেভ হয়েছে" if result.get("logged_in") else "লগইন হয়নি",
             "ok" if result.get("logged_in") else "warn")
    return result


def cmd_upload(args):
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    cfg = settings_lib.load()
    upload_cfg = cfg.get("upload") or {}
    delay = (int(upload_cfg.get("delay_min", 30)), int(upload_cfg.get("delay_max", 90)))
    for platform in platforms:
        if platform == "youtube":
            from core.upload import youtube as module
        elif platform == "facebook":
            from core.upload import facebook as module
        else:
            continue
        for profile in profiles:
            _console(f"আপলোড → {platform} ({profile})", "dim")
            try:
                outcome = module.upload(
                    args.video, args.title or os.path.basename(args.video),
                    args.description or "", (args.tags or "").split(",") if args.tags else [],
                    profile, headless=bool(upload_cfg.get("headless", False)),
                    visibility=upload_cfg.get("visibility", "public"),
                    dry_run=bool(getattr(args, "dry_run", False)),
                    on_status=lambda m: _console(m, "dim"))
                _console(outcome.get("message", "সম্পন্ন"), "ok")
            except Exception as exc:
                _console(f"ব্যর্থ: {exc}", "error")
            time.sleep(random.uniform(*delay))
    return True


def cmd_voices(args):
    cfg = settings_lib.load()
    from core import voices as voice_lib
    _console("edge-tts কণ্ঠ (ইন্টারনেট লাগে):", "ok")
    for voice in voice_lib.VOICES:
        print(f"  {voice['id']:<28} {voice['bn']}")
    _console("এখন সেট করা কণ্ঠ: " + (cfg.get("voice") or {}).get("voice", "(স্বয়ংক্রিয়)"), "dim")
    _console("অফলাইন কণ্ঠ (pyttsx3):", "ok")
    for voice_id, name in tts.list_offline_voices():
        print("  " + str(name))
    return True


def cmd_selftest(args):
    from gui import run_selftest
    print(run_selftest())
    return True


def cmd_gui(args):
    from gui import main
    return main()


def interactive_menu():
    try:
        import questionary as q
    except Exception:
        print("questionary নেই — CLI ফ্ল্যাগ ব্যবহার করুন (--help)")
        return
    topic = q.text("ভিডিওর বিষয় কী?").ask()
    lang = q.select("ভাষা?", choices=["বাংলা", "ইংরেজি"], default="বাংলা").ask()
    count = int(q.text("কতটি ভিডিও?", default="1").ask())
    platforms = q.checkbox("কোথায় আপলোড হবে?", choices=["youtube", "facebook"],
                           default=["youtube", "facebook"]).ask()
    profiles = q.text("প্রোফাইল (কমা দিয়ে)", default="acc1").ask()
    args = argparse.Namespace(
        topic=topic, lang="bn" if lang == "বাংলা" else "en", count=count,
        platforms=",".join(platforms or []), profiles=profiles, no_upload=not platforms,
        type="mobile", style="cinematic", duration=45, images=None, music=None,
        watermark=None, images_dir=None, gender=None, accent=None, voice=None,
        voice_engine=None, ai=None, niche="all", script=None, own=None, dry_run=False)
    cmd_run(args)


def build_parser():
    parser = argparse.ArgumentParser(description="YTFB Studio — ফ্রি ভিডিও অটোমেশন")
    sub = parser.add_subparsers(dest="cmd")

    def add_common(target):
        target.add_argument("--topic", default=None, help="ভিডিওর বিষয় (AI লিখবে)")
        target.add_argument("--script", default=None, help="নিজের স্ক্রিপ্ট ফাইল (.txt/.md/.srt)")
        target.add_argument("--own", default=None, help="সরাসরি স্ক্রিপ্ট টেক্সট")
        target.add_argument("--niche", default=None, help="টেমপ্লেট নিশ")
        target.add_argument("--type", default=None, help="mobile|landscape|square")
        target.add_argument("--style", default=None, help="cinematic|dramatic|educational|vibrant|anime|...")
        target.add_argument("--duration", type=int, default=None)
        target.add_argument("--images", choices=["on", "off"], default=None)
        target.add_argument("--image-source", default=None, help="auto|ai|stock|own|none")
        target.add_argument("--images-dir", default=None, help="নিজের ছবির ফোল্ডার")
        target.add_argument("--music", dest="music", action="store_true", default=None)
        target.add_argument("--no-music", dest="music", action="store_false")
        target.add_argument("--watermark", default=None)
        target.add_argument("--lang", default=None, help="bn|en")
        target.add_argument("--gender", default=None, help="male|female")
        target.add_argument("--accent", default=None, help="bd|in|us|uk|au")
        target.add_argument("--voice", default=None, help="edge-tts ভয়েস আইডি")
        target.add_argument("--voice-engine", default=None, help="auto|edge|gtts|pyttsx3")
        target.add_argument("--ai", default=None, help="pollinations|gemini|groq|openrouter|ollama")
        target.add_argument("--dry-run", action="store_true", help="আপলোড টেস্ট, Publish চাপে না")

    g = sub.add_parser("generate", help="শুধু ভিডিও তৈরি")
    add_common(g)
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("run", help="ভিডিও তৈরি করে আপলোড")
    add_common(r)
    r.add_argument("--count", type=int, default=1)
    r.add_argument("--platforms", default=None)
    r.add_argument("--profiles", default=None)
    r.add_argument("--no-upload", action="store_true")
    r.set_defaults(func=cmd_run)

    login = sub.add_parser("login", help="একাউন্ট লগইন")
    login.add_argument("--platform", required=True, choices=["youtube", "facebook"])
    login.add_argument("--profile", required=True)
    login.set_defaults(func=cmd_login)

    up = sub.add_parser("upload", help="আগের ভিডিও আপলোড")
    up.add_argument("--video", required=True)
    up.add_argument("--title", default=None)
    up.add_argument("--description", default=None)
    up.add_argument("--tags", default=None)
    up.add_argument("--platforms", default="youtube,facebook")
    up.add_argument("--profiles", default="acc1")
    up.add_argument("--dry-run", action="store_true")
    up.set_defaults(func=cmd_upload)

    sub.add_parser("voices", help="কণ্ঠের তালিকা").set_defaults(func=cmd_voices)
    sub.add_parser("selftest", help="নিজেই পরীক্ষা করে দেখুন").set_defaults(func=cmd_selftest)
    sub.add_parser("gui", help="ডেস্কটপ অ্যাপ খুলুন").set_defaults(func=cmd_gui)
    return parser


def main():
    if len(sys.argv) == 1:
        interactive_menu()
        return
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
