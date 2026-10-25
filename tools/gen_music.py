"""Regenerate the built-in royalty-free music library (all procedurally synthesised)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import music

if __name__ == "__main__":
    paths = music.ensure_builtin(force=True, progress=print)
    print("Generated music:")
    for path in paths:
        print(" -", path, os.path.getsize(path) // 1024, "KB")
