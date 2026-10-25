import os
import sys


def bundle_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(".")


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def template_dir():
    return os.path.join(bundle_dir(), "content", "templates")


def assets_dir():
    return os.path.join(bundle_dir(), "media", "assets")


def fonts_dir():
    return os.path.join(assets_dir(), "fonts")


def user_fonts_dir():
    return os.path.join(data_dir(), "fonts")


def user_music_dir():
    return os.path.join(data_dir(), "music")


def music_dir():
    return os.path.join(assets_dir(), "music")


def backgrounds_dir():
    return os.path.join(assets_dir(), "bg")


def browsers_dir():
    return os.path.join(bundle_dir(), "browsers")


def config_path():
    return os.path.join(app_dir(), "config.json")


def profiles_dir():
    return os.path.join(app_dir(), "profiles")


def output_dir():
    return os.path.join(app_dir(), "output")


def logs_dir():
    return os.path.join(app_dir(), "logs")


def data_dir():
    return os.path.join(app_dir(), "data")


def cache_dir():
    return os.path.join(data_dir(), "cache")


def images_cache_dir():
    return os.path.join(cache_dir(), "images")


def tts_cache_dir():
    return os.path.join(cache_dir(), "tts")


def thumb_dir():
    return os.path.join(data_dir(), "thumbs")


def settings_path():
    return os.path.join(data_dir(), "settings.json")


def projects_path():
    return os.path.join(data_dir(), "projects.json")


def outputs_dir():
    return os.path.join(output_dir(), "videos")


def ensure_dirs():
    for d in (
        profiles_dir(), output_dir(), outputs_dir(), logs_dir(),
        data_dir(), cache_dir(), images_cache_dir(), tts_cache_dir(), thumb_dir(),
        fonts_dir(), user_fonts_dir(), music_dir(), user_music_dir(), backgrounds_dir(),
    ):
        os.makedirs(d, exist_ok=True)
