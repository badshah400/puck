#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
# mypy: disable-error-code=import-untyped

from pathlib import Path
import requests
import re
from lxml import etree
from packaging.version import parse, InvalidVersion


class HepForgeVersion:
    """Class for checking latest versions from HepForge"""

    def __init__(self, pkg_cache_dir: Path, url: str, src_url: str):
        """Init function for HepForgeVersion class

        :pkg_cache_dir: cache dir for puck packages (Path)
        :url: url extracted from specfile (str)
        :src_url: source url extracted from specfile (str)

        """

        self._url = url
        self._src_url = src_url

        if re.search(r"hepforge\.org", self._url):
            re_http = re.compile("^https?://")
            self.proj_name = re_http.sub("", self._url).split(".")[0]

            # Handle URL's in the form: http://projects.hepforge.org/pyfeyn/
            if self.proj_name == "projects":
                self.proj_name = re_http.sub("", self._url).rstrip("/").split("/")[-1]

        elif re.search(r"hepforge\.org", self._src_url):
            self.proj_name = self._src_url.split("/")[4]
        else:
            raise RuntimeError(r"Source does not point to hepforge URL")

        self.proj_url = f"https://{self.proj_name}.hepforge.org/downloads"
        headers = {
            "Accept": "text/html",
            "User-Agent": "curl/8.14.1",
            "cache-control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/html; charset=utf-8",
        }
        self.data = requests.get(
            self.proj_url,
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )

        self.text_in_name_node: str = ""

        if self.data.status_code != requests.codes["ok"]:
            self.data.raise_for_status()

    def get_version(self):
        """Get version from list of downloads for source tarball

        :returns: version as packaging.version object

        """
        allowed_src_exts = [".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".xz", ".zip", "zst"]
        tar_prefix = re.compile("^[a-zA-Z_.-]+")
        html_name_nodes = etree.HTML(self.data.text).findall('.//*[@class="name"]/a')
        MAX_TRIES: int = 5
        ver: str = ""
        try:
            for i in range(MAX_TRIES):
                text_in_name_node = html_name_nodes[i].text
                if Path(text_in_name_node).suffix in allowed_src_exts:
                    ver = tar_prefix.sub("", text_in_name_node)
                    while Path(ver).suffix in allowed_src_exts:
                        ver = ver.rsplit(".", 1)[0].strip()
                    break
            else:
                raise RuntimeError("Not listed on hepforge downloads page")
        except IndexError:
            raise RuntimeError(f"Unable to find list of downloads at {self.proj_url}.")
        try:
            return parse(ver)
        except InvalidVersion as e:
            raise e


if __name__ == "__main__":
    pass
