#!/usr/bin/env python3

"""
Base classes for reading package data off atom/rss feeds
"""

# mypy: disable-error-code=import-untyped

import feedparser as fp


class _FeedReader:

    """Common class for feed readers"""

    def __init__(self, feed_url: str, metadata: dict):
        """Initialise _FeedReader class

        :feed_url: URL pointing to feed
        :metadata: Optional metadata to send to feed server

        """
        self.feed_url = feed_url
        self.no_update = False
        self.metadata: dict = metadata
        self._valid_feed = True


    def get_data(self) -> fp.FeedParserDict:
        """Parse and return feed data
        :returns: parses feed data

        """
        if self.metadata.get("feed_metadata"):
            self.etag = self.metadata["feed_metadata"].get("etag", "")
            self.modified = self.metadata["feed_metadata"].get("modified", "")
        else:
            self.etag = ""
            self.modified = ""
        try:
            feed_data = (fp.parse(self.feed_url, etag=self.etag,
                                  modified=self.modified) if
                         self.metadata.get("feed_metadata") else
                         fp.parse(self.feed_url))
        except Exception as e:
            raise e

        if feed_data.status >= 308:
            self._valid_feed = False
            raise RuntimeError(f"Error accessing {self.feed_url} [HTTP code {feed_data.status}]")

        if feed_data.status == 304:
            self.no_update = True
            return fp.FeedParserDict()  # This returned val is never actually used
        else:
            self.etag = feed_data.get("etag", "")
            self.modified = feed_data.get("modified", "")

        if not feed_data.entries:
            self._valid_feed = False
            raise RuntimeError(f"Invalid URL or empty feed: {self.feed_url}")

        return feed_data


class AtomReader(_FeedReader):
    """
    Base class for reading package data off atom/rss feeds. Must be derived from.
    """

    def __init__(self, feed_url: str, metadata: dict):
        super().__init__(feed_url, metadata)
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
        try:
            self.feed_data = self.get_data()
        except RuntimeError as _:
            self.feed_data = {}

    def get_tag_id(self, tag_num: int = 0) -> str:
        if self.no_update:
            return ""
        try:
            assert tag_num < len(self.feed_data.get("entries", []))
        except AssertionError:
            raise RuntimeError(
                f"Invalid item number {tag_num} for feed with"
                f" {len(self.feed_data.get('entries', []))} total entries"
            )

        ver = self.feed_data.entries[tag_num].get("title", "")
        return ver

