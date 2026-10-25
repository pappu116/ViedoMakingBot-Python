"""End-to-end pipeline: script -> voice -> visuals -> render -> mp4."""
import os
import shutil
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import render as render_lib
from core import tts as tts_lib
from core import video as video_lib
from paths import ensure_dirs, logs_dir, outputs_dir


def _noop(*_args, **_kwargs):
    return None


def spoken_text(script):
    parts = []
    hook = (script.get("hook") or "").strip()
    if hook:
        parts.append(hook)
    for scene in script.get("scenes") or []:
        text = (scene.get("text") or "").strip()
        if text:
            parts.append(text)
    cta = (script.get("cta") or "").strip()
    if cta:
        parts.append(cta)
    if not parts:
        parts = [(script.get("body") or "").strip()]
    return " ".join(p for p in parts if p).strip()


def _write_run_log(lines):
    try:
        ensure_dirs()
        path = os.path.join(logs_dir(), "run.log")
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as fh:
            for line in lines:
                fh.write(f"[{stamp}] {line}\n")
    except OSError:
        pass


def build_video(script, opts=None, progress=None, log=None, cancel=None, keep_work=False):
    """Build one video. Returns {video, thumbnail, plan, audio, duration, seconds}."""
    opts = dict(opts or {})
    progress = progress or _noop
    log = log or _noop
    ensure_dirs()

    job_id = uuid.uuid4().hex[:8]
    work_dir = os.path.join(outputs_dir(), "_work", job_id)
    os.makedirs(work_dir, exist_ok=True)
    started = time.time()
    messages = [f"job {job_id} শুরু: {script.get('title', '')}"]

    def logger(message):
        messages.append(str(message))
        log(message)

    def cancelled():
        return bool(cancel and cancel())

    audio_info = None
    lang = (script.get("lang") or "").strip() or opts.get("lang") or "bn"
    if opts.get("voiceover", True):
        text = spoken_text(script)
        if not text:
            raise RuntimeError("স্ক্রিপ্টে বলার মতো কোনো লেখা নেই")
        engine = opts.get("voice_engine") or "auto"
        voice_id = opts.get("voice") or ""
        engine_label = "স্বয়ংক্রিয়"
        progress(0.03, "ভয়েস তৈরি হচ্ছে…")
        audio_info = tts_lib.synthesize(
            text,
            lang=lang,
            gender=opts.get("gender") or "female",
            accent=opts.get("accent") or "bd",
            voice_id=voice_id or None,
            rate=int(opts.get("rate") or 0),
            pitch=int(opts.get("pitch") or 0),
            engine=engine if engine != "auto" else "auto",
        )
        engine_label = audio_info.get("engine", "?")
        logger(f"ভয়েস: {engine_label} · {audio_info.get('duration', 0):.1f} সেকেন্ড · "
               f"{len(audio_info.get('words') or [])} শব্দ")
        progress(0.10, "ভয়েস তৈরি হয়েছে")
    else:
        logger("ভয়েস বন্ধ — শুধু ভিজ্যুয়াল ও মিউজিক")

    if cancelled():
        raise RuntimeError("বাতিল করা হয়েছে")

    plan_opts = {
        "aspect": opts.get("aspect") or "mobile",
        "style": opts.get("style") or "cinematic",
        "caption_style": opts.get("caption_style") or "bold",
        "duration": opts.get("duration") or 45,
        "fps": opts.get("fps") or 24,
        "kenburns": opts.get("kenburns", True),
        "motion": opts.get("motion") or "auto",
        "subtitles": opts.get("subtitles", True),
        "progress_bar": opts.get("progress_bar", True),
        "watermark": opts.get("watermark") or "",
        "images": opts.get("images", True),
        "stock_video": opts.get("stock_video", True),
        "image_source": opts.get("image_source") or "auto",
        "own_images_dir": opts.get("own_images_dir") or "",
        "allow_network": opts.get("allow_network", True) if opts.get("images", True) else False,
        "image_token": opts.get("image_token") or "",
        "music_dir": opts.get("music_dir") or "",
    }
    plan = render_lib.build_plan(script, audio_info, plan_opts, work_dir=work_dir,
                                 progress=progress, cancel=cancel)
    plan["music_seed"] = job_id
    plan["music_dir"] = plan_opts["music_dir"]

    if cancelled():
        raise RuntimeError("বাতিল করা হয়েছে")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(outputs_dir(), f"video_{stamp}_{job_id}.mp4")
    progress(0.35, "ভিডিও রেন্ডার হচ্ছে…")
    video_lib.compose(plan, audio_info, out_path, opts=plan_opts,
                      progress=progress, log=logger, cancel=cancel)
    progress(0.95, "থাম্বনেইল তৈরি হচ্ছে…")

    from core import projects as projects_lib
    from paths import data_dir
    thumbnail = projects_lib.save_thumbnail(out_path, max(0.6, float(plan["duration"]) * 0.25))
    try:
        storyboard = video_lib.render_storyboard(
            plan, os.path.join(data_dir(), "thumbs", "_board"), count=5)
    except Exception:
        storyboard = []
    progress(1.0, "তৈরি হয়ে গেছে")

    elapsed = round(time.time() - started, 1)
    logger(f"সম্পন্ন: {out_path} ({elapsed} সেকেন্ড)")
    _write_run_log(messages)

    if not keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "video": out_path,
        "thumbnail": thumbnail,
        "storyboard": storyboard,
        "plan": plan,
        "audio": audio_info,
        "duration": plan["duration"],
        "seconds": elapsed,
    }


def build_scene_visual(script, opts=None, index=0, variant=0):
    """Fetch and grade one scene visual — used by the wizard's preview / re-roll."""
    from core import images as image_lib
    from core import script as script_lib
    from paths import data_dir

    opts = dict(opts or {})
    scenes = script.get("scenes") or []
    if not scenes:
        return {}
    scene_index = max(0, min(int(index), len(scenes) - 1))
    scene = scenes[scene_index]
    width, height = render_lib.resolve_size(opts.get("aspect") or "mobile")
    style = opts.get("style") or "cinematic"
    preset = render_lib.STYLE_PRESETS.get(style, render_lib.STYLE_PRESETS["cinematic"])
    prompt = (scene.get("image_prompt") or "").strip() or script_lib.make_image_prompt(
        scene.get("text", ""), script.get("topic", ""), style, scene_index,
        script.get("lang", "en"))

    if opts.get("images", True):
        source = opts.get("image_source") or "auto"
    else:
        source = "none"
    image, note, source_path = image_lib.scene_visual(
        prompt, width, height, index=scene_index, variant=int(variant), source=source,
        own_dir=opts.get("own_images_dir") or "",
        allow_network=bool(opts.get("allow_network", True)),
        token=opts.get("image_token") or "")
    graded = render_lib.grade_image(image, preset, width, height, seed=scene_index + int(variant))

    out_dir = os.path.join(data_dir(), "thumbs", "_scenes")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"scene_{scene_index:02d}_v{int(variant)}.jpg")
    graded.convert("RGB").save(path, quality=90)
    return {
        "kind": "scene_visual",
        "index": scene_index,
        "variant": int(variant),
        "image": path,
        "note": note,
        "prompt": prompt,
        "source": source_path or "",
    }


def build_storyboard(script, opts=None, count=4, progress=None, cancel=None, limit=None):
    """Fetch a thumbnail for several scenes at once (visual QA before rendering)."""
    scenes = script.get("scenes") or []
    total = len(scenes) if limit is None else min(len(scenes), int(limit))
    results = []
    for index in range(total):
        if cancel and cancel():
            break
        if progress:
            progress(index / max(1, total), f"দৃশ্য {index + 1}/{total} এর ছবি")
        results.append(build_scene_visual(script, opts, index=index, variant=0))
    return {"kind": "storyboard", "items": results}


def render_preview_frame(script, opts=None, index=0):
    """One graded still for the wizard preview (no video encode)."""
    opts = dict(opts or {})
    plan_opts = {
        "aspect": opts.get("aspect") or "mobile",
        "style": opts.get("style") or "cinematic",
        "images": opts.get("images", True),
        "image_source": opts.get("image_source") or "auto",
        "own_images_dir": opts.get("own_images_dir") or "",
        "allow_network": opts.get("allow_network", True),
        "subtitles": False,
        "progress_bar": False,
    }
    scenes = script.get("scenes") or []
    if not scenes:
        return ""
    scenes = [scenes[min(index, len(scenes) - 1)]]
    sub = dict(script)
    sub["scenes"] = scenes
    plan = render_lib.build_plan(sub, None, plan_opts, work_dir=os.path.join(outputs_dir(), "_preview"))
    return plan["shots"][0]["background"] if plan.get("shots") else ""
