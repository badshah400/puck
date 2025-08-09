# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

"""
Module for saving, loading metadata
"""

import json
from pathlib import Path
from contextlib import suppress


def load_cache_metadata(filename: Path | str) -> dict:
    """Save feed metadata as json file"""
    metadata: dict = {}
    try:
        with open(filename, mode="r") as f:
            with suppress(json.JSONDecodeError):
                metadata = json.load(f)
    except FileNotFoundError as e:
        raise e
    return metadata


def update_cache_metadata(filename: Path | str, metadata: dict):
    """Update metadata in file"""
    with open(filename, mode="w") as f:
        json.dump(metadata, f)
