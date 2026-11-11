#!/usr/bin/env python3
"""Generate a Rex poster icon library from authenticated TMDB API data."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
USER_AGENT = "rex-tmdb-poster-library/1.0"
MAX_PAGE = 500


@dataclass(frozen=True)
class Bucket:
    key: str
    label: str
    media_type: str
    target: int
    params: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="rex-tmdb-posters.json")
    parser.add_argument("--image-size", default="w500")
    parser.add_argument("--movie-count", type=int, default=2000)
    parser.add_argument("--tv-count", type=int, default=1500)
    parser.add_argument("--anime-count", type=int, default=1000)
    parser.add_argument("--variety-count", type=int, default=500)
    parser.add_argument("--request-delay", type=float, default=0.08)
    parser.add_argument("--allow-partial", action="store_true")
    return parser.parse_args()


class TmdbClient:
    def __init__(self, delay: float) -> None:
        self.bearer = os.getenv("TMDB_BEARER_TOKEN", "").strip()
        self.api_key = os.getenv("TMDB_API_KEY", "").strip()
        if not self.bearer and not self.api_key:
            raise SystemExit(
                "缺少 TMDB 凭据：请设置 TMDB_BEARER_TOKEN（推荐）或 TMDB_API_KEY。"
            )
        self.delay = max(0.0, delay)

    def get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = dict(params)
        if self.api_key and not self.bearer:
            query["api_key"] = self.api_key
        url = f"{API_BASE}{path}?{urllib.parse.urlencode(query)}"
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"

        for attempt in range(6):
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers=headers), timeout=30
                ) as response:
                    payload = json.load(response)
                if self.delay:
                    time.sleep(self.delay)
                return payload
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 5:
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                    raise RuntimeError(f"TMDB 请求失败 HTTP {exc.code}: {detail}") from exc
                retry_after = float(exc.headers.get("Retry-After", 0) or 0)
                time.sleep(max(retry_after, 2**attempt))
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 5:
                    raise RuntimeError(f"TMDB 网络请求失败: {exc}") from exc
                time.sleep(2**attempt)
        raise AssertionError("unreachable")


def buckets(args: argparse.Namespace) -> list[Bucket]:
    common = {"include_adult": "false"}
    today = datetime.now(timezone.utc).date().isoformat()
    return [
        Bucket(
            "movie",
            "电影",
            "movie",
            args.movie_count,
            {
                **common,
                "sort_by": "primary_release_date.desc",
                "primary_release_date.lte": today,
                "vote_count.gte": "100",
            },
        ),
        Bucket(
            "tv",
            "电视剧",
            "tv",
            args.tv_count,
            {
                **common,
                "sort_by": "first_air_date.desc",
                "first_air_date.lte": today,
                "vote_count.gte": "30",
                "without_genres": "16,10764,10767",
                "include_null_first_air_dates": "false",
            },
        ),
        Bucket(
            "anime",
            "动漫",
            "tv",
            args.anime_count,
            {
                **common,
                "sort_by": "first_air_date.desc",
                "first_air_date.lte": today,
                "vote_count.gte": "30",
                "with_genres": "16",
                "include_null_first_air_dates": "false",
            },
        ),
        Bucket(
            "variety",
            "综艺",
            "tv",
            args.variety_count,
            {
                **common,
                "sort_by": "first_air_date.desc",
                "first_air_date.lte": today,
                "vote_count.gte": "10",
                "with_genres": "10764|10767",
                "without_genres": "16",
                "include_null_first_air_dates": "false",
            },
        ),
    ]


def normalized_title(item: dict[str, Any], media_type: str) -> str:
    candidates = (
        (item.get("title"), item.get("original_title"))
        if media_type == "movie"
        else (item.get("name"), item.get("original_name"))
    )
    for title in candidates:
        if isinstance(title, str) and title.strip():
            return " ".join(title.split())
    return ""


def year_of(item: dict[str, Any], media_type: str) -> str:
    field = "release_date" if media_type == "movie" else "first_air_date"
    value = item.get(field)
    return value[:4] if isinstance(value, str) and len(value) >= 4 else ""


def collect_bucket(
    client: TmdbClient,
    bucket: Bucket,
    image_size: str,
    used_media: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    if bucket.target <= 0:
        return []
    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < bucket.target and page <= MAX_PAGE:
        params: dict[str, Any] = {
            **bucket.params,
            "language": "zh-CN",
            "page": page,
        }
        payload = client.get(f"/discover/{bucket.media_type}", params)
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            break
        for item in results:
            media_id = item.get("id")
            poster_path = item.get("poster_path")
            title = normalized_title(item, bucket.media_type)
            identity = (bucket.media_type, media_id)
            genres = set(item.get("genre_ids") or [])
            category_matches = (
                bucket.key != "tv" or not genres.intersection({16, 10764, 10767})
            ) and (
                bucket.key != "anime" or 16 in genres
            ) and (
                bucket.key != "variety"
                or (bool(genres.intersection({10764, 10767})) and 16 not in genres)
            )
            if (
                not isinstance(media_id, int)
                or identity in used_media
                or not title
                or not category_matches
                or not isinstance(poster_path, str)
                or not poster_path.startswith("/")
            ):
                continue
            used_media.add(identity)
            records.append(
                {
                    "title": title,
                    "year": year_of(item, bucket.media_type),
                    "category": bucket.label,
                    "url": f"{IMAGE_BASE}/{image_size}{poster_path}",
                }
            )
            if len(records) >= bucket.target:
                break
        total_pages = min(int(payload.get("total_pages") or 1), MAX_PAGE)
        if page >= total_pages:
            break
        page += 1
        print(
            f"\r{bucket.label}: {len(records)}/{bucket.target}（第 {page - 1} 页）",
            end="",
            flush=True,
        )
    print(f"\r{bucket.label}: {len(records)}/{bucket.target}" + " " * 20)
    return records


def disambiguate_names(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    counts = Counter(record["title"] for record in records)
    seen: Counter[str] = Counter()
    icons: list[dict[str, str]] = []
    for record in records:
        title = record["title"]
        name = title
        if counts[title] > 1:
            suffix = " · ".join(
                value for value in (record["year"], record["category"]) if value
            )
            name = f"{title}（{suffix}）" if suffix else title
            seen[name] += 1
            if seen[name] > 1:
                name = f"{name} {seen[name]}"
        icons.append({"name": name, "url": record["url"]})
    return icons


def main() -> int:
    args = parse_args()
    if any(value < 0 for value in (
        args.movie_count, args.tv_count, args.anime_count, args.variety_count
    )):
        raise SystemExit("各分类数量不能为负数。")
    client = TmdbClient(args.request_delay)
    used_media: set[tuple[str, int]] = set()
    all_records: list[dict[str, Any]] = []
    shortages: list[str] = []
    distribution: list[str] = []

    for bucket in buckets(args):
        records = collect_bucket(client, bucket, args.image_size, used_media)
        all_records.extend(records)
        distribution.append(f"{bucket.label}{len(records)}部")
        if len(records) < bucket.target:
            shortages.append(f"{bucket.label}仅 {len(records)}/{bucket.target}")

    if shortages and not args.allow_partial:
        raise SystemExit(
            "未生成文件：真实有效数据不足（" + "；".join(shortages) +
            "）。可调整分类数量/筛选条件，或明确使用 --allow-partial。"
        )

    icons = disambiguate_names(all_records)
    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    document = {
        "name": "TMDB 最新热门影视海报库",
        "description": (
            f"由 TMDB 数据自动生成，共 {len(icons)} 个海报（{'、'.join(distribution)}）；"
            f"按上映/首播日期由新到旧排列，中文名称优先；更新日期 {generated}。"
            "This product uses the TMDB API but is not "
            "endorsed or certified by TMDB."
        ),
        "icons": icons,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    print(f"已写入 {output}：{len(icons)} 条")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        raise SystemExit(130)
