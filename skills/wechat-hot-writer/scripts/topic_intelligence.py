from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

WELLNESS_KEYWORDS = {
    "健康",
    "养生",
    "睡眠",
    "失眠",
    "饮食",
    "走路",
    "关节",
    "血糖",
    "消化",
    "肠胃",
    "季节",
    "春天",
    "夏天",
    "秋天",
    "冬天",
    "花粉过敏",
    "过敏",
}

FAMILY_KEYWORDS = {
    "家庭",
    "父母",
    "爸妈",
    "老人",
    "长辈",
    "退休",
    "照护",
    "防骗",
    "骗局",
    "提醒",
}

GENERIC_EDITORIAL_KEYWORDS = {
    "中老年",
    "银发",
    "生活",
    "家庭",
    "提醒",
}

LOW_SIGNAL_CONTEXT_KEYWORDS = {
    "中老年",
    "健康提醒",
    "家庭照护",
    "家庭提醒",
    "父母",
    "家庭",
    "提醒",
    "生活",
}

UNSAFE_SUGGESTION_PATTERNS = (
    "乱伦",
    "视频",
    "免费",
    "成人",
    "色情",
    "偷拍",
    "小处",
    "老孰",
    "笔趣阁",
    "摄像头",
    "母子",
)


SeoFetcher = Callable[[str], dict[str, list[str]]]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def fetch_json(url: str, params: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    query = urllib.parse.urlencode(params or {})
    target = f"{url}?{query}" if query else url
    request = urllib.request.Request(
        target,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://weibo.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8", "ignore")
    return json.loads(payload)


def fetch_direct_hotspots(limit: int = 20, timeout: int = 10) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    sources = (
        ("weibo", _fetch_weibo_hotspots),
        ("toutiao", _fetch_toutiao_hotspots),
        ("baidu", _fetch_baidu_hotspots),
    )
    for source_name, fetcher in sources:
        try:
            items.extend(fetcher(timeout=timeout))
        except Exception as exc:
            failures.append({"source": source_name, "error": str(exc)})

    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = re.sub(r"\s+", "", str(item.get("title", "")).strip()).lower()
        if not key:
            continue
        existing = deduped.get(key)
        if existing is None or int(item.get("hot_value", 0) or 0) > int(existing.get("hot_value", 0) or 0):
            deduped[key] = item

    ordered = sorted(deduped.values(), key=lambda entry: int(entry.get("hot_value", 0) or 0), reverse=True)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "items": ordered[:limit],
        "failures": failures,
    }


def _fetch_weibo_hotspots(timeout: int = 10) -> list[dict[str, Any]]:
    data = fetch_json("https://weibo.com/ajax/side/hotSearch", timeout=timeout)
    items: list[dict[str, Any]] = []
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for entry in data.get("data", {}).get("realtime", []):
        title = str(entry.get("note", "")).strip()
        if not title:
            continue
        items.append(
            {
                "title": title,
                "url": f"https://s.weibo.com/weibo?q=%23{urllib.parse.quote(title)}%23",
                "source": "weibo-direct",
                "category": entry.get("label_name") or "微博热搜",
                "hot_value": int(entry.get("num", 0) or 0),
                "date": now_iso,
                "raw": entry,
            }
        )
    return items


def _fetch_toutiao_hotspots(timeout: int = 10) -> list[dict[str, Any]]:
    data = fetch_json(
        "https://www.toutiao.com/hot-event/hot-board/",
        params={"origin": "toutiao_pc"},
        timeout=timeout,
    )
    items: list[dict[str, Any]] = []
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for entry in data.get("data", []):
        title = str(entry.get("Title", "")).strip()
        if not title:
            continue
        items.append(
            {
                "title": title,
                "url": str(entry.get("Url", "")).strip(),
                "source": "toutiao-direct",
                "category": entry.get("Label") or "头条热榜",
                "hot_value": int(entry.get("HotValue", 0) or 0),
                "date": now_iso,
                "raw": entry,
            }
        )
    return items


def _fetch_baidu_hotspots(timeout: int = 10) -> list[dict[str, Any]]:
    data = fetch_json(
        "https://top.baidu.com/api/board",
        params={"platform": "wise", "tab": "realtime"},
        timeout=timeout,
    )
    items: list[dict[str, Any]] = []
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for card in data.get("data", {}).get("cards", []):
        top_content = card.get("content", [])
        if not top_content:
            continue
        entries = top_content[0].get("content", []) if isinstance(top_content[0], dict) else top_content
        for entry in entries:
            title = str(entry.get("word", "")).strip()
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "url": str(entry.get("url", "")).strip(),
                    "source": "baidu-direct",
                    "category": "百度热搜",
                    "hot_value": int(entry.get("hotScore", 0) or 0),
                    "date": now_iso,
                    "raw": entry,
                }
            )
    return items


def extract_seo_keywords(title: str, category: str = "", max_keywords: int = 4) -> list[str]:
    seeds: list[str] = []
    title = title.strip()
    category = category.strip()
    if title:
        seeds.append(title)

    keyword_sources = []
    matched_keywords = [
        keyword
        for keyword in sorted(WELLNESS_KEYWORDS | FAMILY_KEYWORDS)
        if keyword in title
    ]
    keyword_sources.extend(matched_keywords[:3])

    short_phrases = re.findall(r"[\u4e00-\u9fff]{2,8}", title)
    keyword_sources.extend(short_phrases[:3])
    if category and len(seeds) + len(keyword_sources) < max_keywords:
        keyword_sources.append(category)

    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in seeds + keyword_sources:
        normalized = keyword.strip()
        if normalized and normalized not in seen:
            deduped.append(normalized)
            seen.add(normalized)
    if len(deduped) < max_keywords:
        for keyword in sorted(LOW_SIGNAL_CONTEXT_KEYWORDS):
            if keyword not in seen:
                deduped.append(keyword)
                seen.add(keyword)
            if len(deduped) >= max_keywords:
                break
    return deduped[:max_keywords]


def filter_safe_suggestions(suggestions: list[str]) -> list[str]:
    kept: list[str] = []
    for suggestion in suggestions:
        normalized = str(suggestion).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if any(pattern in normalized or pattern in lowered for pattern in UNSAFE_SUGGESTION_PATTERNS):
            continue
        kept.append(normalized)
    return kept


def fetch_baidu_suggestions(keyword: str, timeout: int = 10) -> list[str]:
    try:
        data = fetch_json(
            "https://suggestion.baidu.com/su",
            params={"wd": keyword, "action": "opensearch", "ie": "utf-8"},
            timeout=timeout,
        )
    except Exception:
        return []
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        return [str(item).strip() for item in data[1] if str(item).strip()]
    return []


def fetch_so360_suggestions(keyword: str, timeout: int = 10) -> list[str]:
    try:
        data = fetch_json(
            "https://sug.so.360.cn/suggest",
            params={"word": keyword, "encodein": "utf-8", "encodeout": "utf-8", "format": "json"},
            timeout=timeout,
        )
    except Exception:
        return []
    return [str(item.get("word", "")).strip() for item in data.get("result", []) if str(item.get("word", "")).strip()]


def default_seo_fetcher(keyword: str) -> dict[str, list[str]]:
    return {
        "baidu": fetch_baidu_suggestions(keyword),
        "so360": fetch_so360_suggestions(keyword),
    }


def build_topic_seo(title: str, category: str = "", fetcher: SeoFetcher | None = None) -> dict[str, Any]:
    fetch = fetcher or default_seo_fetcher
    keywords = extract_seo_keywords(title, category)
    details: list[dict[str, Any]] = []
    related_keywords: list[str] = []
    best_score = 0.0

    for keyword in keywords:
        try:
            response = fetch(keyword)
        except Exception:
            response = {"baidu": [], "so360": []}
        baidu = filter_safe_suggestions([item for item in response.get("baidu", []) if str(item).strip()])
        so360 = filter_safe_suggestions([item for item in response.get("so360", []) if str(item).strip()])
        score_10 = round((min(len(baidu), 10) + min(len(so360), 10)) / 2, 1)
        best_score = max(best_score, score_10 / 10.0)
        detail = {
            "keyword": keyword,
            "score": round(score_10 / 10.0, 4),
            "score_10": score_10,
            "baidu": baidu[:5],
            "so360": so360[:5],
        }
        details.append(detail)
        for item in baidu + so360:
            if item not in related_keywords:
                related_keywords.append(item)

    return {
        "keywords": keywords,
        "score": round(best_score, 4),
        "related_keywords": related_keywords[:10],
        "details": details,
    }


def load_history_payload(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"articles": []}
    history_path = Path(path)
    if not history_path.exists():
        return {"articles": []}
    raw = history_path.read_text(encoding="utf-8").strip()
    if not raw:
        return {"articles": []}
    payload = json.loads(raw)
    if isinstance(payload, list):
        return {"articles": payload}
    if isinstance(payload, dict):
        payload.setdefault("articles", [])
        return payload
    return {"articles": []}


def save_history_payload(path: str | Path, payload: dict[str, Any]) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_history_payload(payload)
    history_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_history_payload(payload: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"articles": payload}
    if not isinstance(payload, dict):
        return {"articles": []}
    articles = payload.get("articles")
    if not isinstance(articles, list):
        payload = dict(payload)
        payload["articles"] = []
    return payload  # type: ignore[return-value]


def parse_history_datetime(value: str | None) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except Exception:
        return None


def build_history_penalty(
    title: str,
    category: str,
    history_payload: dict[str, Any] | list[Any] | None,
    window_days: int = 7,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    payload = normalize_history_payload(history_payload)
    articles = payload.get("articles", [])
    now_value = now or dt.datetime.now(dt.timezone.utc)
    if now_value.tzinfo is None:
        now_value = now_value.replace(tzinfo=dt.timezone.utc)

    match_keywords = set(extract_seo_keywords(title, category, max_keywords=6))
    overlap_keywords: set[str] = set()
    matched_titles: list[str] = []
    most_recent_days: float | None = None

    for article in articles:
        if not isinstance(article, dict):
            continue
        published_at = parse_history_datetime(article.get("published_at") or article.get("date"))
        if published_at is None:
            continue
        age_days = (now_value.astimezone(dt.timezone.utc) - published_at.astimezone(dt.timezone.utc)).total_seconds() / 86400.0
        if age_days < 0 or age_days > float(window_days):
            continue

        article_keywords = {str(item).strip() for item in article.get("topic_keywords", []) if str(item).strip()}
        article_keywords.update(extract_seo_keywords(str(article.get("title", "")), "", max_keywords=4))
        current_overlap = {keyword for keyword in article_keywords if keyword and any(keyword in candidate or candidate in keyword for candidate in match_keywords)}
        if not current_overlap:
            continue

        overlap_keywords.update(current_overlap)
        matched_titles.append(str(article.get("title", "")).strip())
        if most_recent_days is None or age_days < most_recent_days:
            most_recent_days = age_days

    penalty = clamp(0.12 * len(overlap_keywords), 0.0, 0.42)
    return {
        "penalty": round(penalty, 4),
        "window_days": window_days,
        "overlap_keywords": sorted(overlap_keywords),
        "matched_titles": matched_titles[:3],
        "most_recent_days": round(most_recent_days, 2) if most_recent_days is not None else None,
    }


def append_history_entry(history_payload: dict[str, Any] | list[Any] | None, entry: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_history_payload(history_payload)
    articles = list(payload.get("articles", []))
    new_entry = dict(entry)

    match_index: int | None = None
    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            continue
        if new_entry.get("media_id") and article.get("media_id") == new_entry.get("media_id"):
            match_index = index
            break
        if article.get("title") == new_entry.get("title") and article.get("published_at") == new_entry.get("published_at"):
            match_index = index
            break

    if match_index is None:
        articles.append(new_entry)
    else:
        articles[match_index] = {**articles[match_index], **new_entry}

    payload["articles"] = articles
    return payload


def merge_stats_into_history(history_payload: dict[str, Any] | list[Any] | None, stats_list: list[dict[str, Any]]) -> dict[str, Any]:
    payload = normalize_history_payload(history_payload)
    articles = list(payload.get("articles", []))
    title_to_index = {
        str(article.get("title", "")).strip(): index
        for index, article in enumerate(articles)
        if isinstance(article, dict)
    }

    for stat in stats_list:
        title = str(stat.get("title", "")).strip()
        if not title or title not in title_to_index:
            continue
        article = dict(articles[title_to_index[title]])
        target_user = max(int(stat.get("target_user", 1) or 1), 1)
        article["stats"] = {
            "read_count": int(stat.get("int_page_read_count", 0) or 0),
            "share_count": int(stat.get("share_count", 0) or 0),
            "like_count": int(stat.get("old_like_count", 0) or 0) + int(stat.get("like_count", 0) or 0),
            "read_rate": round(int(stat.get("int_page_read_count", 0) or 0) / target_user * 100, 1),
        }
        articles[title_to_index[title]] = article

    payload["articles"] = articles
    return payload


def apply_topic_intelligence(
    topic: dict[str, Any],
    history_payload: dict[str, Any] | list[Any] | None,
    window_days: int = 7,
    seo_fetcher: SeoFetcher | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    enriched = dict(topic)
    score_breakdown = dict(enriched.get("score_breakdown", {}))
    base_score = float(enriched.get("score", 0.0) or 0.0)

    seo = build_topic_seo(
        title=str(enriched.get("title", "")),
        category=str(enriched.get("category", "")),
        fetcher=seo_fetcher,
    )
    history = build_history_penalty(
        title=str(enriched.get("title", "")),
        category=str(enriched.get("category", "")),
        history_payload=history_payload,
        window_days=window_days,
        now=now,
    )

    seo_multiplier = 0.82 + (0.18 * float(seo["score"]))
    history_multiplier = 1.0 - float(history["penalty"])
    adjusted_score = clamp(base_score * seo_multiplier * history_multiplier)

    enriched["seo"] = seo
    enriched["history"] = history
    enriched["topic_keywords"] = seo["keywords"]
    score_breakdown["seo"] = round(float(seo["score"]), 4)
    score_breakdown["history_penalty"] = round(float(history["penalty"]), 4)
    enriched["score_breakdown"] = score_breakdown
    enriched["score"] = round(adjusted_score, 4)
    return enriched


def get_wechat_access_token(appid: str, secret: str, timeout: int = 20) -> str:
    try:
        payload = fetch_json(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": appid, "secret": secret},
            timeout=timeout,
        )
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"failed to fetch WeChat token: {exc}") from exc
    if "access_token" not in payload:
        raise RuntimeError(f"WeChat token error: {payload}")
    return str(payload["access_token"])


def fetch_wechat_article_summary(access_token: str, begin_date: str, end_date: str, timeout: int = 20) -> list[dict[str, Any]]:
    body = json.dumps({"begin_date": begin_date, "end_date": end_date}, ensure_ascii=False).encode("utf-8")
    query = urllib.parse.urlencode({"access_token": access_token})
    request = urllib.request.Request(
        f"https://api.weixin.qq.com/datacube/getarticlesummary?{query}",
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "ignore"))
    except HTTPError as exc:
        raise RuntimeError(f"getarticlesummary http error: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"getarticlesummary url error: {exc.reason}") from exc
    if "list" in payload:
        return [item for item in payload.get("list", []) if isinstance(item, dict)]
    if payload.get("errcode") == 61500:
        return []
    raise RuntimeError(f"getarticlesummary error: {payload}")
