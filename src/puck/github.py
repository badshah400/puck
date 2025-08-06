#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
# mypy: disable-error-code=import-untyped

from string import Template
import re
from packaging.version import parse
import osc.conf

from puck.scrapers.base.atom_reader import AtomReader
from puck.stdver import stdver

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config["apiurl"]


class GithubVersion(AtomReader):
    """
    Class to check version correspoding to latest tag from github
    """

    MAX_ENTRIES = 5
    ghuser: str | None = None
    ghrepo: str | None = None

    def __init__(self, url: str, src_url: str = "", patt_sub: dict[str, str] = {}):
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
        super().__init__(self.url)
        # ghrepo ending in digits messes up version search, drop them from tag name
        # along with separator, if any
        gh_repo_end_digits = re.search(r"\d+$", self.ghrepo)
        self.tag_end_digits_cleanup_regex = (
            re.compile(rf"{gh_repo_end_digits.group(0)}[_-]") if gh_repo_end_digits else None
        )

    def get_version(self):
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
                return parse(ver.replace("_", "."))
            except Exception:
                pass

        raise RuntimeError(f"Unable to obtain version from last {self.MAX_ENTRIES:d} tags")


if __name__ == "__main__":
    pass
