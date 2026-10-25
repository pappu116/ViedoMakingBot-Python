"""Royalty-free background music: procedurally generated beds + user folders.

Everything generated here is original synthesis, so it is safe to publish.
"""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import ensure_dirs, music_dir, user_music_dir

SR = 44100
BUILTIN_MARKER = "builtin_v2"

MOODS = {
    "calm": {
        "bpm": 68,
        "chords": [[220.00, 261.63, 329.63], [196.00, 246.94, 293.66],
                   [174.61, 220.00, 261.63], [196.00, 246.94, 329.63]],
        "pad": 0.55, "arp": 0.10, "kick": 0.0, "bright": 1.0,
    },
    "uplift": {
        "bpm": 92,
        "chords": [[261.63, 329.63, 392.00], [293.66, 369.99, 440.00],
                   [349.23, 440.00, 523.25], [392.00, 493.88, 587.33]],
        "pad": 0.42, "arp": 0.16, "kick": 0.20, "bright": 1.35,
    },
    "focus": {
        "bpm": 76,
        "chords": [[196.00, 233.08, 293.66], [174.61, 220.00, 261.63],
                   [155.56, 196.00, 233.08], [174.61, 220.00, 261.63]],
        "pad": 0.5, "arp": 0.12, "kick": 0.0, "bright": 0.85,
    },
    "emotional": {
        "bpm": 64,
        "chords": [[174.61, 220.00, 261.63], [155.56, 196.00, 233.08],
                   [130.81, 174.61, 220.00], [146.83, 196.00, 246.94]],
        "pad": 0.6, "arp": 0.09, "kick": 0.0, "bright": 0.9,
    },
    "energetic": {
        "bpm": 110,
        "chords": [[261.63, 329.63, 392.00], [329.63, 415.30, 493.88],
                   [293.66, 369.99, 440.00], [392.00, 493.88, 587.33]],
        "pad": 0.34, "arp": 0.20, "kick": 0.34, "bright": 1.5,
    },
}


def _envelope(length, attack=0.08, release=0.5):
    env = np.ones(length)
    a = min(int(attack * SR), length // 2)
    r = min(int(release * SR), length // 2)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return env


def _tone(freq, duration, bright=1.0, detune=0.004):
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave_sum = np.sin(2 * np.pi * freq * t)
    wave_sum += 0.5 * bright * np.sin(2 * np.pi * freq * 2 * t)
    wave_sum += 0.22 * bright * np.sin(2 * np.pi * freq * 3 * t)
    wave_sum += 0.4 * np.sin(2 * np.pi * freq * (1 + detune) * t)
    return wave_sum / 2.2


def _kick(duration, amp):
    if amp <= 0:
        return np.zeros(int(SR * duration))
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    sweep = 110 * np.exp(-18 * t) + 42
    body = np.sin(2 * np.pi * np.cumsum(sweep) / SR)
    return amp * body * np.exp(-7 * t)


def _build_track(mood_name, seed=None, bars=8):
    rng = np.random.default_rng(seed)
    mood = MOODS[mood_name]
    beat = 60.0 / mood["bpm"]
    bar = beat * 4
    length = int(SR * bar * bars)
    buffer = np.zeros(length)

    chords = [mood["chords"][i % len(mood["chords"])] for i in range(bars)]
    for bar_index, chord in enumerate(chords):
        start = int(bar_index * bar * SR)
        for note_index, freq in enumerate(chord):
            segment = _tone(freq, bar, mood["bright"])
            segment = segment * _envelope(len(segment), attack=0.6, release=0.9)
            detune = 1 + rng.uniform(-0.002, 0.002)
            segment += _tone(freq * detune * 0.5, bar, mood["bright"] * 0.6) * 0.4
            end = min(length, start + len(segment))
            buffer[start:end] += segment[:end - start] * mood["pad"] / (1 + note_index * 0.35)

        if mood["arp"] > 0:
            for step in range(8):
                pos = start + int(step * beat / 2 * SR)
                if pos >= length:
                    break
                note = chord[step % len(chord)] * 2
                piece = _tone(note, beat * 0.9, mood["bright"] * 1.2)
                piece = piece * _envelope(len(piece), attack=0.02, release=0.35) * mood["arp"]
                end = min(length, pos + len(piece))
                buffer[pos:end] += piece[:end - pos]

    for bar_index in range(bars):
        if mood["kick"] <= 0:
            break
        for beat_index in (0, 2):
            pos = int((bar_index * bar + beat_index * beat) * SR)
            thump = _kick(0.5, mood["kick"])
            end = min(length, pos + len(thump))
            buffer[pos:end] += thump[:end - pos]

    # gentle low pass to remove harshness
    kernel = np.ones(24) / 24
    buffer = np.convolve(buffer, kernel, mode="same")
    peak = float(np.max(np.abs(buffer)) or 1.0)
    buffer = buffer / peak * 0.82
    return _loop_fade(buffer, seconds=1.2)


def _loop_fade(samples, seconds=1.2):
    n = min(int(SR * seconds), len(samples) // 4)
    if n <= 0:
        return samples
    samples[:n] *= np.linspace(0, 1, n)
    samples[-n:] *= np.linspace(1, 0, n)
    return samples


def _write_wav(path, samples):
    data = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    stereo = np.repeat(data[:, None], 2, axis=1)
    with wave.open(path, "w") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(stereo.tobytes())


def builtin_paths():
    """Generated tracks live in a writable folder (works inside a frozen exe too)."""
    ensure_dirs()
    return [os.path.join(user_music_dir(), f"builtin_{name}.wav") for name in MOODS]


def ensure_builtin(force=False, progress=None):
    """Generate the built-in royalty-free library once."""
    ensure_dirs()
    marker = os.path.join(user_music_dir(), BUILTIN_MARKER)
    paths = builtin_paths()
    if not force and os.path.exists(marker) and all(os.path.exists(p) for p in paths):
        return paths
    for name in MOODS:
        if progress:
            progress(f"মিউজিক তৈরি হচ্ছে: {name}")
        _write_wav(os.path.join(user_music_dir(), f"builtin_{name}.wav"),
                   _build_track(name, seed=hash(name) % 9999))
    with open(marker, "w", encoding="utf-8") as fh:
        fh.write("ok")
    return paths


def _scan(folder):
    if not folder or not os.path.isdir(folder):
        return []
    exts = (".mp3", ".wav", ".m4a", ".ogg")
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(exts)]


def library(user_dir=None):
    """All available music files: generated, bundled, then the user's folder.

    De-duplicated by file name so the same track is never listed twice.
    """
    ensure_dirs()
    files, seen = [], set()
    for path in builtin_paths():
        if os.path.exists(path):
            name = os.path.basename(path)
            files.append(path)
            seen.add(name)
    if not files:
        try:
            files = ensure_builtin()
            seen = {os.path.basename(p) for p in files}
        except Exception:
            files = []
    for folder in (music_dir(), user_dir):
        for path in _scan(folder):
            name = os.path.basename(path)
            if name not in seen:
                seen.add(name)
                files.append(path)
    return files


def pick(seed=None, user_dir=None, mood=None):
    import random
    files = library(user_dir)
    if mood:
        match = [f for f in files if mood in os.path.basename(f).lower()]
        if match:
            files = match
    if not files:
        return None
    return random.Random(seed).choice(files)


def tracks():
    """[{path, name, builtin}] for the UI list."""
    out = []
    for path in library():
        base = os.path.basename(path)
        out.append({
            "path": path,
            "name": base.replace("builtin_", "").replace(".wav", "").replace("_", " ").title(),
            "builtin": base.startswith("builtin_"),
        })
    return out
