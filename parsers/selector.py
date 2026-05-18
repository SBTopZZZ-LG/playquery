"""Main-content selector using an ordered fallback chain.

Mirrors the following strategy:
  1. <main>
  2. [role="main"]
  3. <article>  (stricter threshold)
  4. div[id*="content"]
  5. [class*="content"]
  6. Largest visible text-heavy container (section / main / article / div)
  7. <body> as last resort
"""

from typing import cast

from bs4 import BeautifulSoup, Tag

BLOCKED_TOKENS = [
    "menu",
    "nav",
    "modal",
    "audio",
    "overlay",
    "cookie",
    "ad",
    "banner",
    "sort",
    "filter",
    "sidebar",
    "drawer",
    "comment",
    "related",
    "sponsored",
    "promo",
    "share",
]

ARTICLE_BLOCKED_TOKENS = ["comment", "recipe", "schema", "grid-item"]


def is_hidden(tag: Tag) -> bool:
    """Determine if a tag is likely hidden based on common attributes."""

    style = str(tag.get("style", "")).replace(" ", "").lower()
    if "display:none" in style or "visibility:hidden" in style:
        return True
    if tag.get("aria-hidden") == "true":
        return True
    if tag.has_attr("hidden"):
        return True
    return False


def has_blocked_token(tag: Tag, tokens: list[str]) -> bool:
    """Check if the tag's id or class attributes contain any blocked tokens."""

    tag_id = str(tag.get("id", ""))
    tag_classes = " ".join(tag.get("class", []))
    combined = (tag_id + " " + tag_classes).lower()
    return any(token in combined for token in tokens)


def text_length(tag: Tag) -> int:
    """Calculate the length of the visible text content of a tag."""

    return len(tag.get_text(strip=True))


def is_acceptable(tag: Tag, min_chars: int, blocked: list[str] | None = None) -> bool:
    """Determine if a tag is an acceptable candidate for main content."""

    if is_hidden(tag):
        return False
    if text_length(tag) <= min_chars:
        return False
    if blocked and has_blocked_token(tag, blocked):
        return False
    return True


def largest_acceptable(
    tags: list[Tag],
    min_chars: int,
    blocked: list[str] | None = None,
) -> Tag | None:
    """Find the largest acceptable tag from a list of candidates, based on text length."""

    candidates = [tag for tag in tags if is_acceptable(tag, min_chars, blocked)]
    candidates.sort(key=text_length, reverse=True)
    return candidates[0] if candidates else None


def find_main_content(soup: BeautifulSoup) -> Tag:
    """Identify the main content area of the page using a series of heuristics."""

    candidate = cast(Tag | None, soup.find("main"))
    if candidate and is_acceptable(candidate, 500, BLOCKED_TOKENS):
        return candidate

    candidate = cast(Tag | None, soup.find(attrs={"role": "main"}))
    if candidate and is_acceptable(candidate, 500):
        return candidate

    candidate = cast(Tag | None, soup.find("article"))
    if candidate and is_acceptable(candidate, 1000, ARTICLE_BLOCKED_TOKENS):
        return candidate

    candidate = largest_acceptable(
        cast(list[Tag], soup.find_all("div", id=lambda v: v and "content" in v.lower())),
        500,
        BLOCKED_TOKENS,
    )
    if candidate:
        return candidate

    candidate = largest_acceptable(
        cast(
            list[Tag],
            soup.find_all(True, class_=lambda c: c and any("content" in v.lower() for v in c)),
        ),
        1000,
        BLOCKED_TOKENS,
    )
    if candidate:
        return candidate

    candidate = largest_acceptable(
        cast(list[Tag], soup.find_all(["section", "main", "article", "div"])),
        1000,
        BLOCKED_TOKENS,
    )
    if candidate:
        return candidate

    return cast(Tag, soup.body or soup)
