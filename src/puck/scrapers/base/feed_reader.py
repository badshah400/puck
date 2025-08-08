#!/usr/bin/env python3

"""Base class for reading package data off atom/rss feeds"""

# mypy: disable-error-code=import-untyped

import feedparser as fp
from urllib.error import HTTPError


class AtomReader:
    """
    Base class for reading package data off atom/rss feeds. Must be derived from.
    """

    def __init__(self, feed_url: str, feed_metadata: dict = {}):
        self.no_update = False
        try:
            if feed_metadata:
                self.feed_data = fp.parse(feed_url,
                                          etag=feed_metadata.get("etag"),
                                          modified=feed_metadata.get("modified"))
            else:
                self.feed_data = fp.parse(feed_url)
        except Exception as e:
            raise e

        if self.feed_data.status >= 308:
            raise HTTPError(f"Error accessing {feed_url} [HTTP code {self.feed_data.status}]")
        if not self.feed_data.entries:
            if self.feed_data.status == 304:
                self.no_update = True
            else:
                raise RuntimeError(f"Invalid URL or empty feed: {feed_url}")


    def get_tag_id(self, tag_num: int = 0) -> str:
        try:
            assert tag_num < len(self.feed_data.entries)
        except AssertionError:
            raise RuntimeError(
                f"Invalid item number {tag_num} for feed with {self.feed_data.entries} total entries"
            )
        current_tag = self.feed_data.entries[tag_num]
        ver = current_tag.id.split("/")[-1]
        # Drop leading 'v' from tag, if any
        ver = ver.lstrip('v')
        return ver
