"""Video assembly.

Frames are composed directly in numpy (background motion + overlay paste + progress
bar + fades) instead of moviepy's composite machinery, which is several times slower
for full-HD vertical video.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import audio as audio_lib
from core import music as music_lib

AUDIO_FPS = 44100
CRF = "20"
FADE = 0.3
MOTION_STEPS_PER_SEC = 8


def _clamp(value, low, high):
    return max(low, min(high, value))


def _hex_rgb(value):
    value = (value or "#000000").lstrip("#")
    if len(value) == 8:
        value = value[:6]
    try:
        return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)
    except Exception:
        return np.array([0, 0, 0], dtype=np.uint8)


class _Overlay:
    """One RGBA layer with absolute timing, pre-multiplied once for fast pasting."""

    def __init__(self, entry, shot_start, shot_end, width, height):
        from PIL import Image

        self.path = entry["image"]
        self.x = int(entry.get("x", 0))
        self.y = int(entry.get("y", 0))
        self.kind = entry.get("kind", "overlay")
        image = Image.open(self.path).convert("RGBA")
        self.rgb = np.asarray(image)[:, :, :3].astype(np.float32)
        self.alpha = (np.asarray(image)[:, :, 3:4].astype(np.float32) / 255.0)
        self.height, self.width = self.rgb.shape[:2]
        self.x = max(0, min(self.x, width - 1))
        self.y = max(0, min(self.y, height - 1))
        if entry.get("kind") == "caption":
            self.start = float(entry.get("start", shot_start))
            self.end = float(entry.get("end", shot_end))
        else:
            self.start = shot_start
            self.end = shot_end

    def active(self, t):
        return self.start <= t < self.end

    def paste(self, frame):
        x0, y0 = self.x, self.y
        x1 = min(frame.shape[1], x0 + self.width)
        y1 = min(frame.shape[0], y0 + self.height)
        if x1 <= x0 or y1 <= y0:
            return
        cw, ch = x1 - x0, y1 - y0
        alpha = self.alpha[:ch, :cw, :]
        region = frame[y0:y1, x0:x1]
        blended = self.rgb[:ch, :cw, :] * alpha + region.astype(np.float32) * (1.0 - alpha)
        frame[y0:y1, x0:x1] = blended.astype(np.uint8)


class _Shot:
    """One time range: motion background (still or stock clip) plus its overlays."""

    def __init__(self, shot, width, height, index, total, opts):
        self.start = float(shot.get("start") or 0.0)
        self.duration = max(0.2, float(shot.get("duration") or 0.0))
        self.end = self.start + self.duration
        self.index = index
        self.path = shot["background"]
        self.kind = shot.get("background_kind") or "image"
        self.width = width
        self.height = height
        self.zoom_from = float(shot.get("zoom_from") or 1.0)
        self.zoom_to = float(shot.get("zoom_to") or 1.0)
        self.pan_from = shot.get("pan_from") or (0.0, 0.0)
        self.pan_to = shot.get("pan_to") or (0.0, 0.0)
        self.max_zoom = max(1.02, self.zoom_from, self.zoom_to)
        self.motion = shot.get("motion") or "auto"
        self.steps = max(2, int(self.duration * MOTION_STEPS_PER_SEC))
        self._scaled = None
        self._cached_step = -1
        self._cached_frame = None
        self._clip = None
        self._clip_duration = 0.0
        self.fade_in = FADE if index > 0 else 0.0
        self.fade_out = FADE if index < total - 1 else 0.0
        self.overlays = [_Overlay(entry, self.start, self.end, width, height)
                         for entry in (shot.get("overlays") or [])]

    def release(self):
        self._scaled = None
        self._cached_frame = None
        if self._clip is not None:
            try:
                self._clip.close()
            except Exception:
                pass
            self._clip = None

    def _load(self):
        from PIL import Image

        if self._scaled is None:
            image = Image.open(self.path).convert("RGB")
            self._scaled = image.resize(
                (max(1, int(self.width * self.max_zoom)), max(1, int(self.height * self.max_zoom))),
                Image.LANCZOS)
        return self._scaled

    def _load_clip(self):
        if self._clip is None:
            from moviepy import VideoFileClip
            self._clip = VideoFileClip(self.path)
            self._clip_duration = max(0.4, float(self._clip.duration or 0.0))
        return self._clip

    def _render_video(self, ratio, t_local):
        """Pull a frame from the stock clip and cover-crop it to the target frame."""
        from core import images as image_lib
        from PIL import Image

        clip = self._load_clip()
        source_time = (max(0.0, t_local) % self._clip_duration)
        source_time = min(source_time, max(0.0, self._clip_duration - 0.05))
        try:
            frame = clip.get_frame(source_time)
        except Exception:
            frame = clip.get_frame(0.0)
        image = Image.fromarray(frame)
        # follow the chosen camera movement so clips match the stills
        if self.motion == "none":
            zoom = 1.02
        elif self.motion == "zoom_out":
            zoom = 1.07 - 0.05 * ratio
        elif self.motion == "pan":
            zoom = 1.05
        else:
            zoom = 1.02 + 0.05 * ratio
        offset = (self.pan_from[0] * 0.4, self.pan_from[1] * 0.4) if self.motion != "pan" else (
            (self.pan_from[0] + (self.pan_to[0] - self.pan_from[0]) * ratio) * 0.4, 0.0)
        return np.asarray(image_lib.cover_resize(
            image, self.width, self.height, zoom=zoom, offset=offset))

    def _render(self, ratio):
        from PIL import Image

        scaled = self._load()
        scaled_w, scaled_h = scaled.size
        zoom = self.zoom_from + (self.zoom_to - self.zoom_from) * ratio
        crop_w = min(float(scaled_w), self.width * self.max_zoom / max(0.01, zoom))
        crop_h = min(float(scaled_h), self.height * self.max_zoom / max(0.01, zoom))
        crop_w, crop_h = max(16.0, crop_w), max(16.0, crop_h)
        slack_x = max(0.0, scaled_w - crop_w)
        slack_y = max(0.0, scaled_h - crop_h)
        pan_x = self.pan_from[0] + (self.pan_to[0] - self.pan_from[0]) * ratio
        pan_y = self.pan_from[1] + (self.pan_to[1] - self.pan_from[1]) * ratio
        left = _clamp(scaled_w / 2.0 + pan_x * slack_x / 2.0 - crop_w / 2.0, 0.0, slack_x)
        top = _clamp(scaled_h / 2.0 + pan_y * slack_y / 2.0 - crop_h / 2.0, 0.0, slack_y)
        frame = scaled.resize((self.width, self.height), Image.BICUBIC,
                              box=(left, top, left + crop_w, top + crop_h))
        return np.asarray(frame)

    def background_at(self, t):
        local = _clamp((t - self.start) / self.duration, 0.0, 1.0)
        step = min(self.steps, int(round(local * self.steps)))
        if step != self._cached_step or self._cached_frame is None:
            ratio = step / max(1, self.steps)
            if self.kind == "video":
                self._cached_frame = self._render_video(ratio, t - self.start)
            else:
                self._cached_frame = self._render(ratio)
            self._cached_step = step
        return self._cached_frame

    def fade_factor(self, t):
        local = t - self.start
        factor = 1.0
        if self.fade_in and local < self.fade_in:
            factor = local / self.fade_in
        remaining = self.duration - local
        if self.fade_out and remaining < self.fade_out:
            factor = min(factor, remaining / self.fade_out)
        return _clamp(factor, 0.0, 1.0)


class FrameComposer:
    """Builds every output frame: motion background, overlays, bar, fades."""

    def __init__(self, plan, opts=None, progress=None, cancel=None):
        opts = opts or {}
        self.width = int(plan["width"])
        self.height = int(plan["height"])
        self.duration = max(0.3, float(plan["duration"]))
        self.shots = [_Shot(shot, self.width, self.height, index, len(plan["shots"] or []), opts)
                      for index, shot in enumerate(plan["shots"] or [])]
        if not self.shots:
            raise RuntimeError("রেন্ডার প্ল্যানে কোনো দৃশ্য নেই")
        self.frames = max(1, int(self.duration * int(plan.get("fps") or 24)))
        self.progress = progress
        self.cancel = cancel
        self.counter = 0
        self._current = -1

        bar = plan.get("progress_bar")
        self.bar = None
        if bar:
            self.bar = {
                "height": max(4, int(bar.get("height") or 8)),
                "color": _hex_rgb(bar.get("color") or "#7C3AED"),
                "track": np.array([28, 34, 52], dtype=np.uint8),
            }
        mark = plan.get("watermark")
        self.watermark = None
        if mark:
            self.watermark = _Overlay(
                {"image": mark["image"], "x": mark.get("x", 0), "y": mark.get("y", 0)},
                0.0, self.duration, self.width, self.height)

    def _shot_at(self, t):
        for index, shot in enumerate(self.shots):
            if shot.start <= t < shot.end:
                return index, shot
        return len(self.shots) - 1, self.shots[-1]

    def close(self):
        for shot in self.shots:
            shot.release()

    def frame(self, t):
        if self.cancel and self.cancel():
            raise RuntimeError("বাতিল করা হয়েছে")
        t = _clamp(t, 0.0, max(0.0, self.duration - 1e-4))
        index, shot = self._shot_at(t)
        if index != self._current:
            self._current = index
            # stock clips keep an ffmpeg process open, so free anything we passed
            for other in self.shots:
                if other.index not in (index, index + 1):
                    other.release()
        frame = shot.background_at(t).copy()
        for overlay in shot.overlays:
            if overlay.active(t):
                overlay.paste(frame)
        if self.watermark:
            self.watermark.paste(frame)
        self._draw_bar(frame, t)
        factor = shot.fade_factor(t)
        if factor < 0.999:
            np.multiply(frame, factor, out=frame, casting="unsafe")
        self.counter += 1
        if self.progress and (self.counter % 6 == 0 or self.counter == self.frames):
            self.progress(0.35 + 0.55 * min(1.0, self.counter / float(self.frames)),
                          "ফ্রেম রেন্ডার হচ্ছে")
        return frame

    def _draw_bar(self, frame, t):
        if not self.bar:
            return
        height = self.bar["height"]
        y0 = max(0, self.height - height)
        ratio = _clamp(t / self.duration, 0.0, 1.0)
        filled = int(self.width * ratio)
        frame[y0:y0 + height, :] = self.bar["track"]
        if filled > 0:
            frame[y0:y0 + height, :filled] = self.bar["color"]


def _to_stereo(clip, duration, fps=AUDIO_FPS):
    samples = clip.to_soundarray(fps=fps)
    if samples.ndim == 1:
        samples = samples[:, None]
    if samples.shape[1] == 1:
        samples = np.repeat(samples, 2, axis=1)
    elif samples.shape[1] > 2:
        samples = samples[:, :2]
    target = int(duration * fps)
    if len(samples) < target:
        samples = np.vstack([samples, np.zeros((target - len(samples), 2), dtype=samples.dtype)])
    else:
        samples = samples[:target]
    return samples.astype(np.float32)


def _duck_envelope(voice, fps=AUDIO_FPS, window=0.06, threshold=0.035):
    if voice is None or len(voice) == 0:
        return np.ones(1, dtype=np.float32)
    mono = voice.mean(axis=1)
    size = max(1, int(fps * window))
    kernel = np.ones(size, dtype=np.float32) / size
    energy = np.sqrt(np.convolve(mono.astype(np.float32) ** 2, kernel, mode="same"))
    speaking = (energy > threshold).astype(np.float32)
    smooth = max(1, int(fps * 0.18))
    speaking = np.convolve(speaking, np.ones(smooth, dtype=np.float32) / smooth, mode="same")
    return np.clip(speaking, 0.0, 1.0)


def build_audio_track(plan, audio_info, opts, log=None):
    from moviepy import AudioArrayClip, AudioFileClip

    duration = max(0.5, float(plan["duration"]))
    voice = None
    voice_path = (audio_info or {}).get("audio")
    if opts.get("voiceover", True) and voice_path and os.path.exists(voice_path):
        clip = AudioFileClip(voice_path)
        try:
            voice = _to_stereo(clip, duration)
        finally:
            clip.close()
        voice = audio_lib.polish(voice, fps=AUDIO_FPS, log=log)
        voice = audio_lib.add_edge_fades(voice, fps=AUDIO_FPS, seconds=0.25)

    music_track = None
    if opts.get("music", True) and float(opts.get("music_volume", 0.18)) > 0.001:
        path = music_lib.pick(seed=plan.get("music_seed"), user_dir=opts.get("music_dir"))
        if path:
            if log:
                log("মিউজিক: " + os.path.basename(path))
            clip = AudioFileClip(path)
            try:
                if clip.duration < duration:
                    from moviepy import afx
                    clip = clip.with_effects([afx.AudioLoop(duration=duration)])
                music_track = _to_stereo(clip.subclipped(0, min(duration, clip.duration)), duration)
            finally:
                try:
                    clip.close()
                except Exception:
                    pass
            music_track = music_track / (float(np.max(np.abs(music_track)) or 1.0) or 1.0)
            volume = min(0.6, float(opts.get("music_volume", 0.18)))
            music_track = music_track * volume

    if music_track is not None and opts.get("ducking", True) and voice is not None:
        duck = _duck_envelope(voice)
        if len(duck) != len(music_track):
            duck = np.interp(np.linspace(0, len(duck) - 1, len(music_track)),
                             np.arange(len(duck)), duck).astype(np.float32)
        floor = 0.32
        music_track = music_track * (1.0 - duck * (1.0 - floor))[:, None]

    if voice is None and music_track is None:
        return None
    mix = voice if music_track is None else (music_track if voice is None else voice + music_track)
    peak = float(np.max(np.abs(mix)) or 0.0)
    if peak > 0.99:
        mix = mix / peak * 0.99
    return AudioArrayClip(np.clip(mix, -1.0, 1.0), fps=AUDIO_FPS)


def compose(plan, audio_info, out_path, opts=None, progress=None, log=None, cancel=None):
    """Render the final mp4 and return its path."""
    from moviepy import VideoClip

    opts = opts or {}
    fps = int(plan.get("fps") or 24)
    composer = FrameComposer(plan, opts=opts, progress=progress, cancel=cancel)

    if log:
        log(f"ভিডিও: {composer.width}x{composer.height} · {composer.duration:.1f} সেকেন্ড · "
            f"{len(composer.shots)} দৃশ্য")

    clip = VideoClip(composer.frame, duration=composer.duration)
    audio_track = build_audio_track(plan, audio_info, opts, log=log)
    if audio_track is not None:
        clip = clip.with_audio(audio_track)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    clip.write_videofile(
        out_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=max(2, (os.cpu_count() or 4) // 2),
        preset="fast",
        logger=None,
        ffmpeg_params=["-crf", CRF, "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    try:
        clip.close()
    except Exception:
        pass
    composer.close()
    return out_path


def render_storyboard(plan, out_dir, count=4):
    """Small preview frames for the wizard's storyboard strip."""
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    shots = plan.get("shots") or []
    if not shots:
        return []
    step = max(1, len(shots) // max(1, count))
    paths = []
    for index, shot in enumerate(shots[::step][:count]):
        try:
            if (shot.get("background_kind") or "image") == "video":
                from moviepy import VideoFileClip
                clip = VideoFileClip(shot["background"])
                try:
                    frame = clip.get_frame(min(0.8, max(0.0, clip.duration - 0.1)))
                finally:
                    clip.close()
                image = Image.fromarray(frame)
            else:
                image = Image.open(shot["background"]).convert("RGB")
            thumb = image.copy()
            thumb.thumbnail((260, 460))
            path = os.path.join(out_dir, f"board_{index:02d}.jpg")
            thumb.convert("RGB").save(path, quality=85)
            paths.append(path)
        except Exception:
            continue
    return paths
