#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

from string import Template
import re
from pathlib import Path
from packaging.version import parse, InvalidVersion, Version

from .base.feed_reader import AtomReader
from puck.stdver import stdver
from puck.metadata import load_cache_metadata, update_cache_metadata
from typing import Any


class GithubVersion(AtomReader):
    """
    Class to check version correspoding to latest tag from github
    """

    MAX_ENTRIES = 5
    ghuser: str = ""
    ghrepo: str = ""

    def __init__(self, pkg_cache_dir: Path, url: str, src_url: str = ""):
        try:
            ghuser, ghrepo = src_url.split("/")[3:5]
        except Exception as e:
            raise RuntimeError(f"Cannot resolve GH project/repo ({e})")

        if not re.search(r"github\.com", src_url):
            if not re.search(r"github\.com", url):
                raise RuntimeError("Source does not point to github URL")

            ghuser, ghrepo = url.split("/")[3:5]

        # Handle ghrepo ending in .git
        ghrepo = re.sub(r"\.git$", "", ghrepo)
        self.ghuser = ghuser
        self.ghrepo = ghrepo

        urlTemp = Template("https://github.com/${user}/${repo}/tags.atom")
        self.url: str = urlTemp.substitute(user=self.ghuser, repo=self.ghrepo)

        self.metadata_file: Path = pkg_cache_dir / "github.json"
        # try loading metadata from cache first
        try:
            self.metadata: dict[Any, Any] = load_cache_metadata(
                self.metadata_file
            )
            self.url = self.metadata.get("feed_url", self.url)
        except FileNotFoundError:
            self.metadata = {
                "upstream": "github",
                "hostname": "https://github.com",
                "user": self.ghuser,
                "repo": self.ghrepo,
                "feed_url": self.url,
            }

        super().__init__(self.url, self.metadata)

        # ghrepo ending in digits messes up version search, drop them from tag name
        # along with separator, if any
        gh_repo_end_digits = re.search(r"\d+$", self.ghrepo)
        self.tag_end_digits_cleanup_regex = (
            re.compile(rf"{gh_repo_end_digits.group(0)}[_-]")
            if gh_repo_end_digits
            else None
        )

    def get_version(self) -> Version:
        if self.no_update:
            return parse(self.metadata.get("version") or "0.0.0")
        # Loop entries to get tag with valid version, max 5 times, otherwise give up
        for cnt in range(0, self.MAX_ENTRIES):
            tag = self.get_tag_id(cnt)
            ver = stdver(tag, self.ghrepo)
            ver = (
                re.sub(self.tag_end_digits_cleanup_regex, "", ver)
                if self.tag_end_digits_cleanup_regex
                else ver
            )
            try:
                version: Version = parse(ver.replace("_", "."))
                self.metadata["feed_metadata"] = {}
                self.metadata["feed_metadata"]["etag"] = self.etag
                self.metadata["feed_metadata"]["modified"] = self.modified
                self.metadata["version"] = str(version)
                update_cache_metadata(self.metadata_file, self.metadata)
                return version
            except InvalidVersion:
                continue
            except Exception as e:
                raise e

        raise RuntimeError(f"Unable to obtain version from last {self.MAX_ENTRIES:d} tags")


if __name__ == "__main__":
    pass
