#!/usr/bin/env python3

"""
Base classes for reading package data off atom/rss feeds
"""

# mypy: disable-error-code=import-untyped

import feedparser as fp
from urllib.error import HTTPError

class _FeedReader:

    """Common class for feed readers"""

    def __init__(self, feed_url: str, metadata:dict = {}):
        """Initialise _FeedReader class

        :feed_url: URL pointing to feed
        :metadata: Optional metadata to send to feed server

        """
        self.feed_url = feed_url
        self.no_update = False
        self.metadata = metadata
        self.etag = self.metadata.get("etag", "")
        self.modified = self.metadata.get("modified", "")

    def get_data(self) -> fp.FeedParserDict:
        """Parse and return feed data
        :returns: feed

        """
        try:
            feed_data = (fp.parse(self.feed_url, etag=self.etag,
                                  modified=self.modified) if self.metadata else
                         fp.parse(self.feed_url))
        except Exception as e:
            raise e

        # Update etag and modified stamps
        self.etag = feed_data.get("etag", "")
        self.modified = feed_data.get("modified", "")

        if feed_data.status >= 308:
            raise HTTPError(f"Error accessing {self.feed_url} [HTTP code {feed_data.status}]")
        if not feed_data.entries:
            if feed_data.status == 304:
                self.no_update = True
            else:
                raise RuntimeError(f"Invalid URL or empty feed: {self.feed_url}")
        return feed_data


class AtomReader(_FeedReader):
    """
    Base class for reading package data off atom/rss feeds. Must be derived from.
    """

    def __init__(self, feed_url: str, feed_metadata: dict = {}):
        super().__init__(feed_url, feed_metadata)
        self.feed_data = self.get_data()

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


class RssReader(_FeedReader):
    """Base class for reading RSS feeds; must be derived from"""

    def __init__(self, feed_url: str, feed_metadata: dict = {}):
        """Initialiser RSS_Reader class

        :feed_url: URL to the RSS feed reader
        :feed_metadata: Optional metadata to send to RSS feed server

        """
        super().__init__(feed_url, feed_metadata)
        self.feed_data = self.get_data()

    def get_tag_id(self, tag_num: int = 0) -> str:
        try:
            assert tag_num < len(self.feed_data.entries)
        except AssertionError:
            raise RuntimeError(
                f"Invalid item number {tag_num} for feed with {self.feed_data.entries} total entries"
            )

        ver = self.feed_data.entries[tag_num].get("title", "")
        return ver

