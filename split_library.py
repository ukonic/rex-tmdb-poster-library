#!/usr/bin/env python3
"""Split the default 5000-item library into smaller Rex subscriptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PARTS = [
    ("movies", "TMDB 最新热门电影海报库", 0, 2000),
    ("tv", "TMDB 最新热门电视剧海报库", 2000, 3500),
    ("anime", "TMDB 最新热门动漫海报库", 3500, 4500),
    ("variety", "TMDB 最新热门综艺海报库", 4500, 5000),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    source = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    icons = source.get("icons")
    if not isinstance(icons, list) or len(icons) != 5000:
        raise SystemExit("拆分要求总库恰好包含 5000 条，当前数量不符。")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for slug, name, start, end in PARTS:
        document = {
            "name": name,
            "description": (
                f"从 TMDB 最新热门影视海报总库拆分，共 {end - start} 个海报；"
                "按上映/首播日期由新到旧排列，中文名称优先。"
                "This product uses the TMDB API but is not endorsed or certified by TMDB."
            ),
            "icons": icons[start:end],
        }
        path = output_dir / f"rex-tmdb-{slug}.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"已写入 {path}：{end - start} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
