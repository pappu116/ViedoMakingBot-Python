"""Voice post-processing tests (numpy only, no audio hardware needed)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import audio as audio_lib

FPS = 22050


def _voice(seconds=2.0, amplitude=0.05, loud_from=None, loud_until=None, loud_gain=5.0):
    t = np.linspace(0, seconds, int(FPS * seconds), endpoint=False)
    signal = amplitude * np.sin(2 * np.pi * 190 * t)
    if loud_from is not None:
        signal[int(FPS * loud_from):int(FPS * (loud_until or loud_from + 0.3))] *= loud_gain
    stereo = np.stack([signal, signal], axis=1).astype(np.float32)
    return stereo


def _rms_db(data):
    return 20 * np.log10(max(float(np.sqrt(np.mean(np.asarray(data, dtype=np.float64) ** 2))), 1e-9))


def _peak(data):
    return float(np.max(np.abs(data)))


def test_high_pass_removes_low_rumble():
    t = np.linspace(0, 2.0, int(FPS * 2.0), endpoint=False)
    rumble = (0.3 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)
    speech = (0.1 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)
    mixed = np.stack([rumble + speech, rumble + speech], axis=1)
    filtered = audio_lib.high_pass(mixed, fps=FPS, cutoff=90)
    # the 30 Hz component must lose most of its energy
    assert _rms_db(filtered) < _rms_db(mixed) - 3
    # the high tone survives
    assert _rms_db(filtered) > -30


def test_compress_reduces_dynamic_range():
    """A compressor must shrink the gap between loud and quiet passages."""
    signal = _voice(2.0, amplitude=0.05, loud_from=0.8, loud_until=1.2, loud_gain=8.0)
    compressed = audio_lib.compress(signal, fps=FPS, makeup_db=0.0)

    def window(data, start, end):
        return data[int(FPS * start):int(FPS * end)]

    loud_before = _rms_db(window(signal, 0.9, 1.1))
    quiet_before = _rms_db(window(signal, 1.4, 1.9))
    loud_after = _rms_db(window(compressed, 0.9, 1.1))
    quiet_after = _rms_db(window(compressed, 1.4, 1.9))

    range_before = loud_before - quiet_before
    range_after = loud_after - quiet_after
    assert range_after < range_before - 2, f"{range_before:.1f} dB → {range_after:.1f} dB"
    # the loud burst itself must be tamed, the quiet part left alone
    assert loud_after < loud_before - 2
    assert abs(quiet_after - quiet_before) < 1.0


def test_normalize_hits_the_target_level():
    quiet = _voice(2.0, amplitude=0.02)
    loud = audio_lib.normalize_loudness(quiet, target_db=-15.0)
    assert abs(_rms_db(loud) - (-15.0)) < 0.7, _rms_db(loud)


def test_normalize_never_clips():
    quiet = _voice(2.0, amplitude=0.01, loud_from=0.5, loud_until=0.6, loud_gain=40.0)
    loud = audio_lib.normalize_loudness(quiet, target_db=-12.0, ceiling_db=-1.0)
    assert _peak(loud) <= 10 ** (-1.0 / 20.0) + 1e-3


def test_polish_raises_quiet_speech():
    """A raw edge-tts style level (~-24 dB RMS) must come up to about -15."""
    quiet = _voice(3.0, amplitude=0.02)
    before = _rms_db(quiet)
    polished = audio_lib.polish(quiet, fps=FPS)
    assert before < -20
    assert abs(_rms_db(polished) - (-15.0)) < 1.5
    assert _peak(polished) < 1.0


def test_polish_handles_mono_and_empty():
    mono = np.linspace(-0.1, 0.1, 5000).astype(np.float32)
    out = audio_lib.polish(mono, fps=FPS)
    assert out.shape == mono.shape
    assert audio_lib.polish(np.zeros((0, 2), dtype=np.float32), fps=FPS).shape[0] == 0


def test_edge_fades_start_and_end_silent():
    signal = _voice(1.0, amplitude=0.3)
    faded = audio_lib.add_edge_fades(signal, fps=FPS, seconds=0.2)
    assert abs(float(faded[0, 0])) < 1e-3
    assert abs(float(faded[-1, 0])) < 1e-3
    middle = faded[int(FPS * 0.4):int(FPS * 0.6)]
    assert np.sqrt(np.mean(middle ** 2)) > 0.05, "মাঝের অংশ চুপ হয়ে গেছে"
