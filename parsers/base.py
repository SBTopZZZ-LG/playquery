"""Parser base types."""

from dataclasses import dataclass


@dataclass
class ParseResult:
    """Represents the result of parsing a web page's HTML content."""

    url: str
    """URL of the page that was parsed."""

    title: str | None
    """The page title, if available."""

    text: str
    """The main textual content extracted from the page."""
