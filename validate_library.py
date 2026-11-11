#!/usr/bin/env python3
"""Validate Rex icon-library structure and a sample of remote poster links."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file")
    parser.add_argument("--check-links", type=int, default=0)
    return parser.parse_args()


def sampled(items: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if count <= 0:
        return []
    if count == 1:
        return items[:1]
    if count >= len(items):
        return items
    return [items[round(index * (len(items) - 1) / (count - 1))] for index in range(count)]


def check_link(url: str) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "rex-tmdb-poster-library-validator/1.0", "Range": "bytes=0-0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get_content_type()
        if response.status not in {200, 206} or not content_type.startswith("image/"):
            raise RuntimeError(f"HTTP {response.status}, Content-Type {content_type}")


def main() -> int:
    args = parse_args()
    path = Path(args.json_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"name", "description", "icons"}:
        raise ValueError("顶层必须且只能包含 name、description、icons")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("name 必须是非空字符串")
    if not isinstance(data["description"], str):
        raise ValueError("description 必须是字符串")
    if not isinstance(data["icons"], list):
        raise ValueError("icons 必须是数组")

    seen_urls: set[str] = set()
    for index, icon in enumerate(data["icons"]):
        if not isinstance(icon, dict) or set(icon) != {"name", "url"}:
            raise ValueError(f"icons[{index}] 必须且只能包含 name、url")
        if not isinstance(icon["name"], str) or not icon["name"].strip():
            raise ValueError(f"icons[{index}].name 必须是非空字符串")
        if not isinstance(icon["url"], str) or not icon["url"].startswith(
            "https://image.tmdb.org/t/p/"
        ):
            raise ValueError(f"icons[{index}].url 不是 TMDB HTTPS 图片链接")
        if icon["url"] in seen_urls:
            raise ValueError(f"重复图片链接：{icon['url']}")
        seen_urls.add(icon["url"])

    failures: list[str] = []
    for icon in sampled(data["icons"], args.check_links):
        try:
            check_link(icon["url"])
        except (urllib.error.URLError, RuntimeError) as exc:
            failures.append(f"{icon['name']}: {exc}")
    if failures:
        raise RuntimeError("海报链接检查失败：\n" + "\n".join(failures))
    print(f"验证通过：{len(data['icons'])} 条；远程链接抽检 {min(args.check_links, len(data['icons']))} 条。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"验证失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
