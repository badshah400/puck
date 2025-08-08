#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
# mypy: disable-error-code=import-untyped

from string import Template
from contextlib import suppress
import re
from pathlib import Path
from packaging.version import parse, InvalidVersion
import json

from .base.feed_reader import AtomReader
from puck.stdver import stdver


class GithubVersion(AtomReader):
    """
    Class to check version correspoding to latest tag from github
    """

    MAX_ENTRIES = 5
    ghuser: str | None = None
    ghrepo: str | None = None

    def __init__(
        self, pkg_cache_dir: Path, url: str, src_url: str = "", patt_sub: dict[str, str] = {}
    ):
        try:
            ghuser, ghrepo = src_url.split("/")[3:5]
        except Exception as e:
            raise RuntimeError(f"Cannot resolve GH project/repo ({e})")

        if not re.search(r"github\.com", src_url):
            if not re.search(r"github\.com", url):
                raise RuntimeError("Source does not point to github URL")

            ghuser, ghrepo = url.split("/")[3:5]

        # Handle %name in ghrepo
        for patt in patt_sub.items():
            ghrepo = re.sub(patt[0], patt[1], ghrepo)

        # Handle ghrepo ending in .git
        ghrepo = re.sub(r".git$", "", ghrepo)
        self.ghuser = ghuser
        self.ghrepo = ghrepo

        urlTemp = Template("https://github.com/${user}/${repo}/tags.atom")
        self.url = urlTemp.substitute(user=self.ghuser, repo=self.ghrepo)

        self.gh_mdata_file: Path = pkg_cache_dir / "github.json"
        self.gh_metadata: dict = {"user": self.ghuser, "repo": self.ghrepo}
        try:
            with open(self.gh_mdata_file, mode="r") as f:
                with suppress(json.JSONDecodeError):
                    self.gh_metadata = json.load(f)
        except FileNotFoundError as _:
            self.gh_metadata = {
                "user": self.ghuser,
                "repo": self.ghrepo,
                "feed_url": self.url,
            }

        super().__init__(self.url, self.gh_metadata.get("feed_metadata", {}))
        if not self.no_update:
            self.gh_metadata["feed_metadata"] = {
                "etag": self.feed_data.get("etag", ""),
                "modified": self.feed_data.get("modified", ""),
            }
        # ghrepo ending in digits messes up version search, drop them from tag name
        # along with separator, if any
        gh_repo_end_digits = re.search(r"\d+$", self.ghrepo)
        self.tag_end_digits_cleanup_regex = (
            re.compile(rf"{gh_repo_end_digits.group(0)}[_-]") if gh_repo_end_digits else None
        )

    def get_version(self):
        if self.no_update:
            ver = parse(self.gh_metadata.get("version"))
            return ver
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
                version = parse(ver.replace("_", "."))
                self.gh_metadata["version"] = str(version)
                with open(self.gh_mdata_file, mode="w") as f:
                    json.dump(self.gh_metadata, f)
                return version
            except InvalidVersion as _:
                continue
            except Exception as e:
                raise e

        raise RuntimeError(f"Unable to obtain version from last {self.MAX_ENTRIES:d} tags")


if __name__ == "__main__":
    pass
