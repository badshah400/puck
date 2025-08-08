#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import re
from pathlib import Path
from packaging.version import Version, parse
from puck.stdver import stdver

from .base.feed_reader import RssReader
from puck.metadata import load_cache_metadata, update_cache_metadata

class PyPI(RssReader):

    """PyPI look-up class"""

    MAX_TRIES = 5

    def __init__(self, pkg_cache_dir, obs_prj: str):
        """PyPI init function

        :pypi_prj: PyPI project name (str)
        :metadata: Optional feed metadata to send to feed server (dict)

        """
        pypre   = re.compile(r'^python[2-3]?\-')

        self._pypi_prj = pypre.subn('', obs_prj, 1)[0]
        self.url       = f'https://pypi.org/rss/project/{self._pypi_prj}/releases.xml'
        self.metadata_file: Path = pkg_cache_dir / "pypi.json"
        # try loading metadata from cache first
        try:
            self.metadata = load_cache_metadata(self.metadata_file)
        except FileNotFoundError:
            self.metadata: dict = {
                "upstream": "pypi",
                "project": self._pypi_prj,
                "feed_url": self.url
            }

        super().__init__(self.url, self.metadata)

    def get_version(self):
        ver = Version('0.0.0')
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

if __name__ == '__main__':
    pass
