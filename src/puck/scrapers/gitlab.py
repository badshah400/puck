#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import re
from pathlib import Path
from packaging.version import parse, InvalidVersion, Version

# Local modules
from .base.feed_reader import AtomReader
from puck.metadata import load_cache_metadata, update_cache_metadata
from puck.stdver import stdver

from .baseversion import UpstreamVersion

# Match any non-digits that come before a version string
NON_VERSION_PREFIX = re.compile(r"^[^0-9]*")

class GitlabVersion(AtomReader, UpstreamVersion):

    """Gitlab parser derived from AtomReader"""

    MAX_ENTRIES = 3
    def __init__(self, pkg_cache_dir: Path, url: str, src_url: str = ""):
        """Init gitlab class

        :pkg_cache_dir: Cache dir to store local data (Path)
        :url: Full gitlab repo URL (e.g. https://gitlab.gnome.org/GNOME/pan) (str)

        """

        super(UpstreamVersion, self).__init__()
        try:
            # If Source URL does not work, try url
            self._set_prj_repo_from_url(src_url)
        except (IndexError, TypeError):
            self._set_prj_repo_from_url(url)
        self.metadata_file: Path = pkg_cache_dir / "gitlab.json"
        self._src_url: str = src_url
        if self._src_url.split("/")[0] != "https:":
            # This means the src_url is just the file name
            self._src_url = url + f"/-/archive/%{{version}}/{src_url}"

        # try loading metadata from cache first
        try:
            self.metadata: dict = load_cache_metadata(self.metadata_file)
            self.feed_url: str = self.metadata.get("feed_url", self.feed_url)
        except FileNotFoundError:
            self.metadata = {
                "upstream": "gitlab",
                "hostname": self._gitlab_host,
                "user": self._prj_name,
                "repo": self._repo_name,
                "feed_url": self.feed_url,
            }

        super().__init__(self.feed_url, self.metadata)
        if not (self.feed_data.get("entries") or self.no_update):
            self._set_prj_repo_from_url(url)
            super().__init__(self.feed_url, self.metadata)
            if self.feed_data.get("entries"):
                self.metadata["hostname"] = self._gitlab_host
                self.metadata["user"] = self._prj_name
                self.metadata["repo"] = self._repo_name
                self.metadata["feed_url"] = self.feed_url

        if self.no_update:
            ver = self.metadata.get("version", "0.0.0")
            update_cache_metadata(self.metadata_file, self.metadata)
            self.version = ver
            return

        # Loop over feed entries to get tag with valid version, max 5 times,
        # otherwise give up
        for cnt in range(0, self.MAX_ENTRIES):
            tag = self.get_tag_id(cnt)
            ver = stdver(tag, self._repo_name)
            try:
                ver = ver.replace("_", ".")
                self.metadata["feed_metadata"] = {}
                self.metadata["feed_metadata"]["etag"] = self.etag
                self.metadata["feed_metadata"]["modified"] = self.modified
                self.metadata["version"] = ver
                update_cache_metadata(self.metadata_file, self.metadata)
                self.version = ver
            except InvalidVersion:
                continue
            except Exception as e:
                raise e

        raise RuntimeError(
            f"Unable to obtain version from last {self.MAX_ENTRIES:d} tags"
        )

    def _set_prj_repo_from_url(self, url: str):
        url_tokens: list[str] = url.split("/")
        if url_tokens[-1].endswith(
                (".tar", ".gz", ".xz", ".bz2", ".zst", ".zip")
        ):
            _ = url_tokens.pop()
        self._gitlab_host: str = "/".join(url_tokens[:3])
        self._prj_name: str = url_tokens[3]
        self._repo_name: str = "/".join(url_tokens[4:]).rstrip("#")
        self.feed_url = (
            f"{self._gitlab_host}/{self._prj_name}/{self._repo_name}"
            "/-/tags?format=atom"
        )

    def get_version(self) -> Version:
        return self.version or parse("0.0.0")


if __name__ == "__main__":
    pass
