# vim: set tw=80 ts=4 sw=4 et:

"""Base class for scrapers"""

from packaging.version import Version
from typing import Optional
from packaging.version import InvalidVersion, parse

class UpstreamVersion:

    """Base scraper class"""

    headers: dict[str, str] = {
        "Accept": "*/*",
        "User-Agent": "curl/8.14.1",
        "cache-control": "no-cache",
        "Connection": "keep-alive",
    }

    def __init__(self) -> None:
        """Base class initialisation (dummy)"""
        self._version: Optional[Version] = None
        pass

    @property
    def version(self) -> Optional[Version]:
        """return the version obtained from upstream"""
        return self._version

    @version.setter
    def version(self, value: str):
        try:
            self._version = parse(value)
        except InvalidVersion as e:
            raise e
