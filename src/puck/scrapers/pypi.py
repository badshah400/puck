#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import re
from json import JSONDecodeError
from string import Template
from pathlib import Path
from packaging.version import Version, parse
from puck.stdver import stdver

from .base.feed_reader import RssReader
from puck.metadata import load_cache_metadata, update_cache_metadata
from .baseversion import UpstreamVersion


class PyPIVersion(RssReader, UpstreamVersion):
    """PyPI look-up class"""

    MAX_TRIES = 5

    def __init__(
        self, pkg_cache_dir: Path, src_url: str, obs_prj: str, url: str = ""
    ):
        """PyPI init function

        :pkg_cache_dir: Cache dir (Path)
        :obs_prj: OBS project name (str)

        """
        super(UpstreamVersion, self).__init__()
        pypre = re.compile(r"^python[2-3]?\-")
        src_url_tokens = src_url.split("/")

        if url:
            # PyPI url template: https://pypi.org/project/Mathics3/
            self._pypi_prj = url.rstrip("/").split("/")[-1]
        else:
            try:
                if src_url_tokens[2].find("pythonhosted.org") > 1:
                    self._pypi_prj = src_url_tokens[6]
                else:
                    raise RuntimeError(
                        "Unable to set pypi prj name from source url"
                    )
            except Exception:
                self._pypi_prj = pypre.subn("", obs_prj, 1)[0]

        self.metadata_file: Path = pkg_cache_dir / "pypi.json"
        # try loading metadata from cache first
        try:
            self.metadata = load_cache_metadata(self.metadata_file)

            if p := self.metadata.get("project"):
                self._pypi_prj = p
        except (FileNotFoundError, JSONDecodeError):
            self.metadata: dict = {
                "upstream": "pypi",
                "hostname": "https://pypi.org",
                "project": self._pypi_prj,
            }

        url_template = Template(
            "https://pypi.org/rss/project/${pypi_prj}/releases.xml"
        )
        self.url = url_template.substitute(pypi_prj=self._pypi_prj)
        self.metadata["feed_url"] = self.url

        super().__init__(self.url, self.metadata)

        if not self._valid_feed:
            # Try pre-pending "python-" to pypi project name
            new_url = url_template.substitute(
                pypi_prj=f"python-{self._pypi_prj}"
            )
            super().__init__(new_url, self.metadata)

            if self._valid_feed:
                self._pypi_prj = f"python-{self._pypi_prj}"
                self.metadata["project"] = self._pypi_prj
                self.url = new_url
                self.metadata["feed_url"] = self.url

        ver: str = "0.0.0"

        if not self._valid_feed:
            raise RuntimeError(f"Invalid PyPI project: {self._pypi_prj}")

        if self.no_update:
            ver = self.metadata["version"]
        else:
            self.metadata["feed_metadata"] = {}
            self.metadata["feed_metadata"]["etag"] = self.etag
            self.metadata["feed_metadata"]["modified"] = self.modified

            for cnt in range(self.MAX_TRIES):
                tag_name = self.get_tag_id(cnt)
                ver = stdver(tag_name, self._pypi_prj)

                if not Version(ver).is_prerelease:
                    break
        try:
            self.metadata["version"] = ver
            update_cache_metadata(self.metadata_file, self.metadata)
            self.version = ver
        except Exception as e:
            raise e

    def get_version(self) -> Version:
        return self.version or parse("0.0.0")


if __name__ == "__main__":
    pass
