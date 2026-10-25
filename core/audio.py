"""Voice post-processing so narration sounds produced instead of raw TTS.

Chain: rumble removal (high-pass) -> gentle compression -> loudness normalise.
All numpy, no extra dependencies, safe to run on every render.
"""
import numpy as np

DEFAULT_FPS = 44100
TARGET_RMS_DB = -15.0
PEAK_CEILING_DB = -1.0


def _to_db(value):
    return 20.0 * np.log10(max(float(value), 1e-9))


def _as_2d(samples):
    if samples.ndim == 1:
        return samples[:, None], True
    return samples, False


def _fir_highpass(cutoff, fps, taps=127):
    n = np.arange(taps) - (taps - 1) / 2.0
    fc = cutoff / fps
    kernel = -2.0 * fc * np.sinc(2.0 * fc * n)
    kernel[taps // 2] += 1.0
    kernel *= np.hamming(taps)
    total = np.sum(np.abs(kernel))
    if total > 0:
        kernel /= total
    return kernel.astype(np.float32)


def high_pass(samples, fps=DEFAULT_FPS, cutoff=85.0):
    """FIR high-pass: removes rumble and handling noise from the narration."""
    data, was_1d = _as_2d(samples)
    if len(data) == 0 or cutoff <= 0:
        return samples
    kernel = _fir_highpass(cutoff, fps)
    out = np.empty_like(data)
    for channel in range(data.shape[1]):
        out[:, channel] = np.convolve(data[:, channel], kernel, mode="same")
    return out[:, 0] if was_1d else out


def _envelope(samples, fps, attack=0.006, release=0.12, step=64):
    """Asymmetric peak envelope.

    The coarse grid uses peak-holding (block max), not decimation — decimating
    aliases the waveform and makes the compressor gain jump around.
    """
    data, _was_1d = _as_2d(samples)
    mono = np.abs(data).max(axis=1)
    frames = len(mono) // step
    if frames == 0:
        return np.ones(len(samples), dtype=np.float32)
    coarse = mono[:frames * step].reshape(frames, step).max(axis=1)
    attack_coef = np.exp(-1.0 / max(1.0, fps / step * attack))
    release_coef = np.exp(-1.0 / max(1.0, fps / step * release))
    envelope = np.empty(frames, dtype=np.float32)
    value = 0.0
    for index, sample in enumerate(coarse):
        coefficient = attack_coef if sample > value else release_coef
        value = coefficient * value + (1.0 - coefficient) * sample
        envelope[index] = value
    positions = (np.arange(frames) + 0.5) * step
    return np.interp(np.arange(len(samples)), positions, envelope).astype(np.float32)


def compress(samples, fps=DEFAULT_FPS, threshold_db=-20.0, ratio=3.0, makeup_db=2.5,
             attack=0.006, release=0.12):
    """Soft-knee compressor: evens out loud and quiet parts of the narration."""
    data, was_1d = _as_2d(samples)
    if len(data) == 0:
        return samples
    envelope = _envelope(data, fps, attack=attack, release=release)
    envelope_db = 20.0 * np.log10(np.maximum(envelope, 1e-6))
    over = np.maximum(0.0, envelope_db - threshold_db)
    gain_db = -over * (1.0 - 1.0 / max(1.0, ratio)) + makeup_db
    gain = np.power(10.0, gain_db / 20.0).astype(np.float32)
    out = data * gain[:, None]
    return out[:, 0] if was_1d else out


def normalize_loudness(samples, target_db=TARGET_RMS_DB, ceiling_db=PEAK_CEILING_DB):
    """Bring the whole track to a consistent, social-media friendly level."""
    if len(samples) == 0:
        return samples
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    if rms <= 0:
        return samples
    gain = 10.0 ** ((target_db - _to_db(rms)) / 20.0)
    out = samples * gain
    peak = float(np.max(np.abs(out)) or 0.0)
    ceiling = 10.0 ** (ceiling_db / 20.0)
    if peak > ceiling:
        out = out * (ceiling / peak)
    return out.astype(np.float32)


def polish(samples, fps=DEFAULT_FPS, log=None):
    """Full narration chain. `samples` is a float32 array shaped (n, channels)."""
    if samples is None or len(samples) == 0:
        return samples
    before = _to_db(float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))))
    out = high_pass(samples, fps=fps, cutoff=85.0)
    out = compress(out, fps=fps)
    out = normalize_loudness(out, target_db=TARGET_RMS_DB)
    if log:
        after = _to_db(float(np.sqrt(np.mean(out.astype(np.float64) ** 2))))
        log(f"ভয়েস প্রসেসিং: {before:.1f} dB → {after:.1f} dB (RMS)")
    return out


def add_edge_fades(samples, fps=DEFAULT_FPS, seconds=0.25):
    fade = int(fps * seconds)
    if len(samples) <= fade * 2 or fade <= 0:
        return samples
    samples[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    samples[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
    return samples
