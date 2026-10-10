"""Small DOM reader for public, server-rendered event archives."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class HtmlNode:
    """An element with its attributes, children, and visible text fragments."""

    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def walk(self):
        """Yield elements in document order."""
        yield self
        for child in self.children:
            if isinstance(child, HtmlNode):
                yield from child.walk()

    def has_class(self, name: str) -> bool:
        """Test an exact CSS class token."""
        return name in (self.attrs.get("class") or "").split()

    def text(self) -> str:
        """Read visible text with whitespace separating nested elements."""
        if self.tag in {"script", "style"}:
            return ""
        return " ".join(child.text() if isinstance(child, HtmlNode) else child for child in self.children)


class _TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = HtmlNode(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(payload: bytes) -> HtmlNode:
    """Parse UTF-8 HTML without running scripts or loading external resources."""
    parser = _TreeParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    parser.close()
    return parser.root
