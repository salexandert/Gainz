import os
import sys
from pathlib import Path


def executable_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def resource_dir():
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir).resolve()

    return Path(__file__).resolve().parent


def data_dir():
    configured = os.environ.get("GAINZ_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    return executable_dir()


def data_path(*parts):
    return data_dir().joinpath(*parts)


def resource_path(*parts):
    return resource_dir().joinpath(*parts)


def ensure_data_dir(*parts):
    path = data_path(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path
