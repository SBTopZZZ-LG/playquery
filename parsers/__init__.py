"""HTML parsing utilities."""

from typing import cast

from bs4 import BeautifulSoup, Tag

from .base import ParseResult
from .selector import find_main_content

__all__ = ["ParseResult", "parse"]


def parse(html: str, url: str) -> ParseResult:
    soup = BeautifulSoup(html, "lxml")

    title_tag = cast(Tag | None, soup.find("title"))
    title = title_tag.get_text(strip=True) if title_tag else None

    main = find_main_content(soup)
    text = main.get_text(separator="\n", strip=True)

    return ParseResult(url=url, title=title, text=text)
