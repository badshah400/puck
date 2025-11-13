#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

from pathlib import Path
import re
from packaging.version import Version, parse
import requests

from puck.stdver import stdver


class SFVersion:

    """Class for checking upstream version from sourceforge"""

    def __init__(self, pkg_cache_dir: Path, url: str, src_url: str):
        """Init class for SFVersion

        :pkg_cache_dir: cache dir (Path)
        :url: URL tag extracted from specfile (str)
        :src_url: Source URL extracted from specfile (str)

        """

        sf_dlurl_re1 = re.compile(r"^downloads?\.(sourceforge|sf)\.net$")
        sf_dlurl_re2 = re.compile(r"^(sourceforge|sf)\.net$")
        sf_prjurl_re1 = re.compile(r"(sourceforge|sf)\.net/projects/?")
        sf_prjurl_re2 = re.compile(r"\.(sourceforge|sf)\.(net|io)/?")
        url_http: re.Pattern[str] = re.compile(r"^https?:")

        # If src_url is not a URL (e.g. using a service file, etc.)
        if not url_http.match(src_url):
            src_parts: list[str] = [src_url]
        else:
            src_parts = src_url.split("/")[2:]  # Drop the leading 'http://'

        self.sfproj: str = ""

        # Figure out SF project name
        if sf_dlurl_re1.match(src_parts[0]):
            # This works when the srcURL is of the form:
            # http://downloads.sourceforge.net/<sfprj>/<src_file>
            # or http://downloads.sourceforge.net/project/<sfprj>/<src_file>
            self.sfproj = src_parts[2] if src_parts[1] == "project" else src_parts[1]
        elif sf_dlurl_re2.match(src_parts[0]):
            # This works when the srcURL is of the form:
            # http://sourceforge.net/projects/<sfproj>/files/...
            self.sfproj = src_parts[2]
        elif sf_prjurl_re1.search(url):
            # http://sourceforge.net/projects/<sfproj>/
            self.sfproj = url.split("/")[4]
        elif sf_prjurl_re2.search(url):
            # If the srcURL does not point to a dowload(s).s*f*.net then we look at the spec file's
            # URL, and split the sfprj from http://<sfprj>.sourceforge.net/
            self.sfproj = url.split("/")[2]
            self.sfproj = self.sfproj.split(".")[0]

        if not self.sfproj:
            raise RuntimeError(r"Source does not point to sourceforge URL.")

        self._pkg_cache_dir: Path = pkg_cache_dir
        self._url: str = url
        self._src_url: str = src_url
        headers: dict[str, str] = {
            "Accept": "*/*",
            "User-Agent": "curl/8.14.1",
            "cache-control": "no-cache",
            "Connection": "keep-alive",
        }
        self.data: requests.Response = requests.get(
            f"https://sourceforge.net/projects/{self.sfproj}/best_release.json",
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )

        if self.data.status_code == requests.codes["ok"]:
            self.json = self.data.json()
        else:
            self.data.raise_for_status()

    def get_version(self) -> Version:
        """Get version from decoded json data
        :returns: version as a packaging.version object

        """
        vertemp = r"[0-9]+" + r"(\.?[0-9]){0,6}" + r"([aA]lpha.*)?([Bb]eta.*)?"
        anyver = re.compile(f"[^a-zA-Z]{vertemp}")
        tarball_path = Path(self.json["release"]["filename"])

        if self.sfproj == "scintilla":
            # Hack for scintilla which drops the version sep '.' from the tarball name itself, but
            # has the correct version in the "parent dir". E.g.: "/SciTE/5.5.7/wscite557.tgz".
            ver = tarball_path.parts[-2]
        else:
            if mat := anyver.search(f"{tarball_path.stem}"):
                ver = mat.group()[1:]

        return parse(stdver(ver.replace("_", "."), self.sfproj))


if __name__ == "__main__":
    pass
