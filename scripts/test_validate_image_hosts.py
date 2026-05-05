#!/usr/bin/env python3
"""Self-tests for validate_image_hosts.classify().

Run with: python scripts/test_validate_image_hosts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_image_hosts import classify  # noqa: E402


REJECT_CASES = [
    # The five real URLs that motivated this check (issue #66).
    "https://scontent.fpdl2-1.fna.fbcdn.net/v/t39.30808-6/657657905_1394399412730470_n.jpg?oe=69DB5E20",
    "https://scontent.fpdl2-1.fna.fbcdn.net/v/t39.30808-6/659878910_1394399549397123_n.jpg?oe=69DB5DD6",
    "https://scontent.fpdl2-1.fna.fbcdn.net/v/t39.30808-6/661417057_1399014948935583_n.jpg?oe=69DB5394",
    "https://www.facebook.com/MunicipioPraiaVitoria",
    "https://fb.me/e/4pSYHQ8m5",
    # Variants of the same hosts.
    "http://scontent.fra1-1.fna.fbcdn.net/anything.jpg",
    "https://FB.ME/e/abc",  # case-insensitive
    "https://facebook.com/SomePage",  # no www
    "https://www.facebook.com/SomePage/",  # trailing slash
    "https://www.facebook.com/SomePage?ref=whatever",  # querystring still a bare page
    # Instagram's public CDN is also under fbcdn.net with the same oe= /
    # hotlink-block behavior. The fbcdn.net rule catches it too, which is
    # what we want.
    "https://instagram.fopo1-1.fna.fbcdn.net/v/t51.2885-15/foo.jpg",
]

ALLOW_CASES: list[str | None] = [
    # Real allow-list examples that must keep working.
    "/assets/images/events/festival-teatro-2026.jpg",
    "https://github.com/user-attachments/assets/f4d41d0d-bf3a-43ba-8a55-1a2953f91998",
    # The format produced by scripts/rehost_image.py — must stay allowed.
    "https://github.com/TerceiraEvents/EventosTerceira.pt/releases/download/event-images/escama-de-dragao-1-20260417-a1f76d95.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/foo.JPG/1280px-foo.JPG",
    # Anything under facebook.com that *points at a structural path* (photos, events, posts)
    # — these have a chance of being image-adjacent, whereas a bare page is not.
    "https://www.facebook.com/MunicipioPraiaVitoria/photos/pb.100/1234567/",
    "https://www.facebook.com/events/1234567890/",
    "",  # empty / missing image field
    None,
]


def main() -> int:
    failed = 0

    for url in REJECT_CASES:
        reason = classify(url)
        if reason is None:
            print(f"FAIL: expected reject, got OK: {url}", file=sys.stderr)
            failed += 1

    for url in ALLOW_CASES:
        reason = classify(url)  # type: ignore[arg-type]
        if reason is not None:
            print(f"FAIL: expected OK, got reject ({reason}): {url}", file=sys.stderr)
            failed += 1

    if failed:
        print(f"{failed} failure(s)", file=sys.stderr)
        return 1
    print(f"OK ({len(REJECT_CASES)} rejects, {len(ALLOW_CASES)} allows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
