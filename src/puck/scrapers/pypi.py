#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import re
from string import Template
from pathlib import Path
from packaging.version import Version, parse
from puck.stdver import stdver

from .base.feed_reader import RssReader
from puck.metadata import load_cache_metadata, update_cache_metadata


class PyPI(RssReader):
    """PyPI look-up class"""

    MAX_TRIES = 5

    def __init__(self, pkg_cache_dir: Path, obs_prj: str):
        """PyPI init function

        :pkg_cache_dir: Cache dir (Path)
        :obs_prj: OBS project name (str)

        """
        pypre = re.compile(r"^python[2-3]?\-")

        self._pypi_prj = pypre.subn("", obs_prj, 1)[0]
        url_template = Template("https://pypi.org/rss/project/${pypi_prj}/releases.xml")
        self.url = url_template.substitute(pypi_prj=self._pypi_prj)
        self.metadata_file: Path = pkg_cache_dir / "pypi.json"
        # try loading metadata from cache first
        try:
            self.metadata = load_cache_metadata(self.metadata_file)
        except FileNotFoundError:
            self.metadata: dict = {
                "upstream": "pypi",
                "hostname": "https://pypi.org",
                "project": self._pypi_prj,
                "feed_url": self.url,
            }

        super().__init__(self.url, self.metadata)
        if not self._valid_feed:
            # Try pre-pending "python-" to pypi project name
            new_url = url_template.substitute(pypi_prj=f"python-{self._pypi_prj}")
            super().__init__(new_url, self.metadata)
            if self._valid_feed:
                self._pypi_prj = f"python-{self._pypi_prj}"
                self.metadata["project"] = self._pypi_prj
                self.url = new_url
                self.metadata["feed_url"] = self.url

    def get_version(self):
        ver = Version("0.0.0")
        if not self._valid_feed:
            raise RuntimeError(f"Invalid PyPI project: {self._pypi_prj}")
        if self.no_update:
            ver = self.metadata["version"]
        else:
            self.metadata["feed_metadata"]: dict = {}
            self.metadata["feed_metadata"]["etag"] = self.etag
            self.metadata["feed_metadata"]["modified"] = self.modified
            for cnt in range(self.MAX_TRIES):
                tag_name = self.get_tag_id(cnt)
                ver = stdver(tag_name, self._pypi_prj)
                if not Version(ver).is_prerelease:
                    break
        try:
            self.metadata["version"] = str(ver)
            update_cache_metadata(self.metadata_file, self.metadata)
            return parse(ver)
        except Exception as e:
            raise e


if __name__ == "__main__":
    pass
