#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from topic_intelligence import apply_topic_intelligence, fetch_direct_hotspots, load_history_payload


TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_BODY_IMAGE_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
UPLOAD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
USER_AGENT = "zach-wechat-daily-publisher/0.1"
PREFERRED_TOPIC_WORDS = {
    "中老年",
    "老人",
    "老年",
    "父母",
    "家人",
    "健康",
    "睡眠",
    "饮食",
    "血压",
    "血糖",
    "防暑",
    "降温",
    "暴雨",
    "高温",
    "防骗",
    "诈骗",
    "认证",
    "预约",
    "医保",
    "社保",
    "养老金",
    "食品",
    "安全",
    "提醒",
}
HIGH_RISK_TOPIC_WORDS = {
    "股票",
    "基金",
    "投资",
    "贷款",
    "判刑",
    "诉讼",
    "确诊",
    "治疗",
    "药方",
    "偏方",
    "明星",
    "塌房",
    "演唱会",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_date(value: str) -> str:
    if value in {"", "today"}:
        return dt.datetime.now().astimezone().date().isoformat()
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def credential_paths(repo: Path) -> list[Path]:
    return [
        repo / ".baoyu-skills" / ".env",
        repo / ".env",
        Path.home() / ".baoyu-skills" / ".env",
    ]


def resolve_credentials(repo: Path) -> dict[str, str]:
    app_id = os.environ.get("WECHAT_APP_ID") or os.environ.get("WECHAT_APPID") or ""
    app_secret = os.environ.get("WECHAT_APP_SECRET") or os.environ.get("WECHAT_SECRET") or ""
    source = "env"
    if not app_id or not app_secret:
        for path in credential_paths(repo):
            values = parse_env_file(path)
            app_id = app_id or values.get("WECHAT_APP_ID") or values.get("WECHAT_APPID") or ""
            app_secret = app_secret or values.get("WECHAT_APP_SECRET") or values.get("WECHAT_SECRET") or ""
            if app_id and app_secret:
                source = str(path)
                break
    if not app_id or not app_secret:
        raise RuntimeError("missing WeChat credentials: set WECHAT_APP_ID and WECHAT_APP_SECRET")
    return {"app_id": app_id, "app_secret": app_secret, "source": source}


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    lines = text.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text
    frontmatter: dict[str, str] = {}
    for raw in lines[1:end_index]:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    body = "\n".join(lines[end_index + 1 :]).strip() + "\n"
    return frontmatter, body


def slug_from_article(article: Path) -> str:
    stem = article.stem
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", stem)
    return match.group(1) if match else stem


def normalize_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def find_daily_results(repo: Path, date_value: str) -> list[dict[str, Any]]:
    log_dir = repo / "publish_logs"
    if not log_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(log_dir.glob(f"{date_value}*.json")):
        status = ""
        title = ""
        try:
            payload = read_json(path)
            if isinstance(payload, dict):
                status = str(payload.get("status", ""))
                title = str(payload.get("title", ""))
        except Exception:
            status = "unreadable"
        results.append(
            {
                "path": str(path),
                "status": status,
                "title": title,
                "is_blocker": "blocker" in path.name or status == "blocked",
            }
        )
    return results


def cmd_preflight(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    date_value = resolve_date(args.date)
    results = find_daily_results(repo, date_value)
    payload = {
        "date": date_value,
        "repo": str(repo),
        "existing_results": results,
        "can_continue": not results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.fail_on_existing and results:
        return 2
    return 0


def article_date_from_path(path: Path) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})-", path.name)
    return match.group(1) if match else ""


def cmd_history_export(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    articles: list[dict[str, Any]] = []
    logs_by_date: dict[str, dict[str, Any]] = {}
    for log_path in sorted((repo / "publish_logs").glob("*.json")):
        try:
            payload = read_json(log_path)
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("date"):
            logs_by_date[str(payload["date"])] = payload

    for article_path in sorted((repo / "articles").glob("*.md")):
        frontmatter, body = parse_frontmatter(article_path)
        date_value = article_date_from_path(article_path)
        log = logs_by_date.get(date_value, {})
        title = frontmatter.get("title") or first_heading(body) or article_path.stem
        articles.append(
            {
                "title": title,
                "summary": frontmatter.get("summary") or frontmatter.get("description") or "",
                "published_at": log.get("timestamp") or log.get("published_at") or date_value,
                "date": date_value,
                "article_path": str(article_path),
                "coverImage": frontmatter.get("coverImage") or "",
                "media_id": log.get("media_id") or "",
                "status": log.get("status") or "",
                "topic_keywords": extract_keywords(title),
                "word_count": len(re.findall(r"[\w\u4e00-\u9fff]", body)),
            }
        )

    payload = {"generated_at": now_utc(), "repo": str(repo), "articles": articles}
    output = normalize_path(args.output, repo)
    write_json(output, payload)
    print(json.dumps({"output": str(output), "article_count": len(articles)}, ensure_ascii=False, indent=2))
    return 0


def estimate_topic(raw: dict[str, Any], rank: int, total: int) -> dict[str, Any]:
    title = str(raw.get("title", "")).strip()
    category = str(raw.get("category") or raw.get("source") or "")
    text = f"{title} {category}".lower()
    preferred_hits = sum(1 for word in PREFERRED_TOPIC_WORDS if word.lower() in text or word in title)
    risk_hits = sum(1 for word in HIGH_RISK_TOPIC_WORDS if word.lower() in text or word in title)
    freshness = max(0.2, 1.0 - ((rank - 1) / max(total, 1)))
    hot_raw = raw.get("hot_value") or raw.get("hot") or raw.get("heat") or 0
    try:
        hot_metric = float(hot_raw)
    except Exception:
        hot_metric = 0.0
    heat = min(1.0, hot_metric / 1000000.0) if hot_metric else freshness
    reader_relevance = min(1.0, 0.32 + 0.14 * preferred_hits)
    compliance_risk = min(0.9, 0.12 + 0.16 * risk_hits)
    explainability = 0.72 if preferred_hits else 0.48
    shareability = 0.72 if any(word in title for word in ("提醒", "家里", "父母", "老人", "别", "先")) else 0.5
    score = max(0.0, min(1.0, freshness * heat * reader_relevance * explainability * shareability * (1.0 - compliance_risk)))
    return {
        "source": raw.get("source") or category or "direct",
        "title": title,
        "url": raw.get("url") or "",
        "category": category,
        "freshness": round(freshness, 4),
        "heat": round(heat, 4),
        "reader_relevance": round(reader_relevance, 4),
        "shareability": round(shareability, 4),
        "compliance_risk": round(compliance_risk, 4),
        "score": round(score, 4),
        "score_breakdown": {
            "freshness": round(freshness, 4),
            "heat": round(heat, 4),
            "reader_relevance": round(reader_relevance, 4),
            "explainability": round(explainability, 4),
            "shareability": round(shareability, 4),
            "compliance_risk": round(compliance_risk, 4),
        },
        "angle_candidates": [
            f"把「{title}」落到中老年家庭今天能做的提醒",
            f"先讲谁受影响，再讲去哪核对「{title}」",
        ],
        "facts": [],
        "raw": raw,
    }


def cmd_discover_topics(args: argparse.Namespace) -> int:
    history = load_history_payload(args.history_file)
    direct = fetch_direct_hotspots(limit=max(args.limit * 20, args.per_source * 12, 120), timeout=min(args.timeout, 20))
    estimated = [
        estimate_topic(item, index, len(direct.get("items", [])) or 1)
        for index, item in enumerate(direct.get("items", []), start=1)
        if str(item.get("title", "")).strip()
    ]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for topic in estimated:
        by_source.setdefault(str(topic.get("source") or "direct"), []).append(topic)
    source_balanced: list[dict[str, Any]] = []
    for source_topics in by_source.values():
        source_balanced.extend(sorted(source_topics, key=lambda item: item["score"], reverse=True)[: args.per_source])
    kept = [
        topic
        for topic in source_balanced
        if (args.allow_high_risk or topic["compliance_risk"] < args.max_risk)
        and topic["reader_relevance"] >= args.min_reader_relevance
    ]
    deduped: dict[str, dict[str, Any]] = {}
    for topic in kept:
        key = re.sub(r"\s+", "", topic["title"]).lower()
        if key not in deduped or topic["score"] > deduped[key]["score"]:
            deduped[key] = topic
    no_network_seo = lambda _keyword: {"baidu": [], "so360": []}
    topics = [
        apply_topic_intelligence(
            topic,
            history_payload=history,
            window_days=args.history_window_days,
            seo_fetcher=None if args.enrich_seo else no_network_seo,
        )
        for topic in deduped.values()
    ]
    topics = sorted(topics, key=lambda item: item["score"], reverse=True)[: args.limit]
    fallback_candidates: list[dict[str, Any]] = []
    if not topics:
        fallback_candidates = sorted(estimated, key=lambda item: item["score"], reverse=True)[: args.limit]
    output = {
        "generated_at": now_utc(),
        "source_mode": "direct-api-only",
        "requested_source_mode": args.source_mode,
        "filters": {
            "allow_high_risk": args.allow_high_risk,
            "max_risk": args.max_risk,
            "min_reader_relevance": args.min_reader_relevance,
            "per_source": args.per_source,
        },
        "history": {
            "path": args.history_file or None,
            "window_days": args.history_window_days,
            "article_count": len(history.get("articles", [])),
        },
        "topics": topics,
        "fallback_candidates": fallback_candidates,
        "failures": direct.get("failures", []),
        "notes": (
            "Browser/OpenCLI sources are intentionally disabled; hybrid requests use direct public sources only. "
            "SEO enrichment is disabled by default to keep scheduled runs deterministic."
        ),
    }
    output_path = Path(args.output).resolve()
    write_json(output_path, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def first_heading(markdown_text: str) -> str:
    match = re.search(r"(?m)^#\s+(.+)$", markdown_text)
    return match.group(1).strip() if match else ""


def extract_keywords(text: str) -> list[str]:
    candidates = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9+-]{1,}", text)
    seen: set[str] = set()
    keywords: list[str] = []
    for candidate in candidates:
        value = candidate.strip()
        if value and value not in seen:
            seen.add(value)
            keywords.append(value)
        if len(keywords) >= 8:
            break
    return keywords


def validate_article(article: Path, expected_cover: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    frontmatter, body = parse_frontmatter(article)
    errors: list[str] = []
    title = frontmatter.get("title") or first_heading(body)
    summary = frontmatter.get("summary") or frontmatter.get("description") or ""
    cover = frontmatter.get("coverImage") or frontmatter.get("cover") or frontmatter.get("image") or ""
    if not title:
        errors.append("missing title in frontmatter or H1")
    if not summary:
        errors.append("missing summary")
    if not cover:
        errors.append("missing coverImage")
    cover_path = normalize_path(cover, article.parent) if cover else None
    if cover_path and not cover_path.exists():
        errors.append(f"coverImage does not exist: {cover_path}")
    if expected_cover and cover_path and cover_path.resolve() != expected_cover.resolve():
        errors.append(f"coverImage does not match expected cover: {expected_cover}")
    if cover_path and cover_path.name == "cover.png":
        errors.append("coverImage points to generic cover.png")
    if len(body.strip()) < 800:
        errors.append("body looks too short for a full article")
    if len(re.findall(r"(?m)^##\s+\S", body)) < 2:
        errors.append("body should include at least two H2 sections")
    return (
        {
            "article": str(article),
            "title": title,
            "summary": summary,
            "coverImage": str(cover_path) if cover_path else "",
            "author": frontmatter.get("author", ""),
            "body_chars": len(body),
            "h2_count": len(re.findall(r"(?m)^##\s+\S", body)),
        },
        errors,
    )


def cmd_validate_article(args: argparse.Namespace) -> int:
    article = Path(args.article).resolve()
    expected_cover = Path(args.cover).resolve() if args.cover else None
    metadata, errors = validate_article(article, expected_cover)
    payload = {"ok": not errors, "metadata": metadata, "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def short_cover_title(title: str) -> str:
    title = re.split(r"[：:，,。.!！?？]", title.strip())[0]
    return title[:10] if len(title) > 10 else title


def cmd_cover_prompt(args: argparse.Namespace) -> int:
    article = Path(args.article).resolve()
    frontmatter, body = parse_frontmatter(article)
    title = frontmatter.get("title") or first_heading(body) or article.stem
    summary = frontmatter.get("summary") or ""
    slug = args.slug or slug_from_article(article)
    work_dir = normalize_path(args.work_dir, Path.cwd()) if args.work_dir else article.parent / "cover-image" / slug
    prompts_dir = work_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    source_path = work_dir / f"source-{slug}.md"
    prompt_path = prompts_dir / f"01-cover-{slug}.md"
    cover_text = args.cover_title or short_cover_title(title)

    source_path.write_text(
        f"{title}\n\nSummary: {summary}\n\nAudience: Simplified Chinese WeChat readers, mainly middle-aged and older adults plus family caregivers.\n",
        encoding="utf-8",
    )
    prompt = f"""---
aspect_ratio: "{args.aspect}"
language: zh
text_level: title-only
references: []
---

Create a WeChat article cover image in Simplified Chinese.

Exact title text to include:
{cover_text}

Article title:
{title}

Article summary:
{summary}

Visual concept:
Create a calm, practical, trustworthy editorial cover for middle-aged and older Chinese readers and their family caregivers. Use a clean scene or conceptual metaphor that makes the topic immediately understandable. Keep the image warm but not sentimental, useful but not like a cheap health-product poster.

Style dimensions:
- Type: {args.cover_type}
- Palette: {args.palette}
- Rendering: {args.rendering}
- Text: title-only
- Mood: {args.mood}
- Font: clean, readable Chinese UI-style sans-serif
- Aspect: {args.aspect}

Composition:
- Use 40-60% breathing room.
- Put the main visual anchor slightly left of center.
- Put the title in open space on the right or upper-right.
- Keep people as simplified silhouettes; no realistic faces.
- No fake logos, no watermark, no medical panic, no miracle-cure ad style.

Quality requirements:
- High-resolution bitmap cover.
- Professional WeChat editorial style.
- Text must be legible and not cramped.
- Avoid pure gradients, heavy shadows, and clutter.
"""
    prompt_path.write_text(prompt, encoding="utf-8")
    payload = {
        "slug": slug,
        "work_dir": str(work_dir),
        "source_path": str(source_path),
        "prompt_path": str(prompt_path),
        "expected_cover_path": str(work_dir / "cover.png"),
        "cover_title": cover_text,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


class CitationState:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []
        self.index_by_url: dict[str, int] = {}

    def cite(self, label: str, url: str) -> str:
        if url not in self.index_by_url:
            self.index_by_url[url] = len(self.items) + 1
            self.items.append((label, url))
        index = self.index_by_url[url]
        return f'<sup style="font-size: 0.8em;">[{index}]</sup>'


def render_inline(text: str, citations: CitationState) -> str:
    escaped = html.escape(text)

    def image_repl(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1), quote=True)
        target = html.unescape(match.group(2))
        return f'<img src="{html.escape(target, quote=True)}" alt="{alt}" style="display:block;width:100%;height:auto;margin:18px auto;" />'

    def link_repl(match: re.Match[str]) -> str:
        label = html.unescape(match.group(1))
        target = html.unescape(match.group(2))
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme in {"http", "https"}:
            return html.escape(label) + citations.cite(label, target)
        return html.escape(label)

    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image_repl, escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def markdown_to_wechat_html(markdown_text: str) -> tuple[str, list[tuple[str, str]]]:
    citations = CitationState()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    list_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = "<br />".join(render_inline(line, citations) for line in paragraph)
            blocks.append(f'<p style="line-height:1.8;margin:0 0 16px;color:#1f2933;font-size:16px;">{text}</p>')
            paragraph = []

    def flush_list() -> None:
        nonlocal list_type, list_items
        if list_type and list_items:
            items = "".join(
                f'<li style="margin:0 0 8px;line-height:1.75;">{item}</li>' for item in list_items
            )
            blocks.append(f'<{list_type} style="padding-left:1.4em;margin:0 0 16px;color:#1f2933;font-size:16px;">{items}</{list_type}>')
        list_type = None
        list_items = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        quote = re.match(r"^>\s?(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            if level == 1:
                blocks.append(f'<h1 style="font-size:22px;line-height:1.45;margin:0 0 22px;color:#111827;font-weight:600;">{render_inline(heading.group(2), citations)}</h1>')
            else:
                blocks.append(f'<h2 style="font-size:19px;line-height:1.55;margin:28px 0 14px;color:#111827;font-weight:600;">{render_inline(heading.group(2), citations)}</h2>')
            continue
        if quote:
            flush_paragraph()
            flush_list()
            blocks.append(f'<blockquote style="border-left:3px solid #9fb3c8;padding:0 0 0 12px;margin:18px 0;color:#52606d;">{render_inline(quote.group(1), citations)}</blockquote>')
            continue
        if ordered:
            flush_paragraph()
            if list_type not in (None, "ol"):
                flush_list()
            list_type = "ol"
            list_items.append(render_inline(ordered.group(1), citations))
            continue
        if unordered:
            flush_paragraph()
            if list_type not in (None, "ul"):
                flush_list()
            list_type = "ul"
            list_items.append(render_inline(unordered.group(1), citations))
            continue
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    if citations.items:
        ref_items = "".join(
            f'<p style="font-size:13px;line-height:1.6;margin:0 0 8px;color:#52606d;">[{index}] {html.escape(label)}: {html.escape(url)}</p>'
            for index, (label, url) in enumerate(citations.items, start=1)
        )
        blocks.append('<hr style="border:none;border-top:1px solid #d9e2ec;margin:28px 0 16px;" />')
        blocks.append(f'<section style="margin-top:12px;">{ref_items}</section>')
    return "\n".join(blocks), citations.items


def render_article_to_path(article: Path, output: Path) -> dict[str, Any]:
    article = article.resolve()
    frontmatter, body = parse_frontmatter(article)
    title = frontmatter.get("title") or first_heading(body) or article.stem
    if not re.search(r"(?m)^#\s+", body):
        body = f"# {title}\n\n{body}"
    content_html, citations = markdown_to_wechat_html(body)
    output.write_text(content_html + "\n", encoding="utf-8")
    return {
        "html_path": str(output),
        "title": title,
        "summary": frontmatter.get("summary") or "",
        "citations": [{"label": label, "url": url} for label, url in citations],
        "inline_images": extract_image_sources(content_html),
    }


def cmd_render(args: argparse.Namespace) -> int:
    article = Path(args.article).resolve()
    output = Path(args.output).resolve() if args.output else article.with_suffix(".wechat.html")
    payload = render_article_to_path(article, output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def extract_image_sources(html_text: str) -> list[str]:
    return re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', html_text)


def http_json(url: str, *, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"http {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"url error: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON response: {raw[:500]}") from exc


def fetch_access_token(app_id: str, app_secret: str, timeout: int) -> str:
    query = urllib.parse.urlencode({"grant_type": "client_credential", "appid": app_id, "secret": app_secret})
    payload = http_json(f"{TOKEN_URL}?{query}", timeout=timeout)
    if payload.get("errcode"):
        raise RuntimeError(f"access token error {payload.get('errcode')}: {payload.get('errmsg')}")
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"access token missing in response: {payload}")
    return str(token)


def multipart_body(field_name: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----zach-wechat-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    data = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def upload_material_image(access_token: str, image_path: Path, timeout: int) -> dict[str, Any]:
    body, content_type = multipart_body("media", image_path)
    query = urllib.parse.urlencode({"access_token": access_token, "type": "image"})
    payload = http_json(
        f"{UPLOAD_MATERIAL_URL}?{query}",
        method="POST",
        data=body,
        headers={"Content-Type": content_type},
        timeout=timeout,
    )
    if payload.get("errcode"):
        raise RuntimeError(f"cover upload error {payload.get('errcode')}: {payload.get('errmsg')}")
    if not payload.get("media_id"):
        raise RuntimeError(f"cover upload missing media_id: {payload}")
    return payload


def upload_body_image(access_token: str, image_path: Path, timeout: int) -> str:
    body, content_type = multipart_body("media", image_path)
    query = urllib.parse.urlencode({"access_token": access_token})
    payload = http_json(
        f"{UPLOAD_BODY_IMAGE_URL}?{query}",
        method="POST",
        data=body,
        headers={"Content-Type": content_type},
        timeout=timeout,
    )
    if payload.get("errcode"):
        raise RuntimeError(f"body image upload error {payload.get('errcode')}: {payload.get('errmsg')}")
    url = payload.get("url")
    if not url:
        raise RuntimeError(f"body image upload missing url: {payload}")
    return str(url).replace("http://", "https://")


def upload_local_images_in_html(html_text: str, article_dir: Path, access_token: str, timeout: int) -> tuple[str, list[dict[str, str]]]:
    uploads: list[dict[str, str]] = []
    output = html_text
    for src in extract_image_sources(html_text):
        parsed = urllib.parse.urlparse(src)
        if parsed.scheme in {"http", "https"}:
            continue
        image_path = normalize_path(html.unescape(src), article_dir)
        if not image_path.exists():
            raise RuntimeError(f"inline image not found: {image_path}")
        wechat_url = upload_body_image(access_token, image_path, timeout)
        output = output.replace(f'src="{src}"', f'src="{html.escape(wechat_url, quote=True)}"')
        uploads.append({"local_path": str(image_path), "wechat_url": wechat_url})
    return output, uploads


def create_draft(
    access_token: str,
    *,
    title: str,
    author: str,
    digest: str,
    content: str,
    thumb_media_id: str,
    need_open_comment: int,
    only_fans_can_comment: int,
    timeout: int,
) -> dict[str, Any]:
    article = {
        "article_type": "news",
        "title": title,
        "author": author,
        "digest": digest[:120],
        "content": content,
        "thumb_media_id": thumb_media_id,
        "show_cover_pic": 0,
        "need_open_comment": need_open_comment,
        "only_fans_can_comment": only_fans_can_comment,
    }
    body = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    query = urllib.parse.urlencode({"access_token": access_token})
    payload = http_json(
        f"{DRAFT_URL}?{query}",
        method="POST",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout,
    )
    if payload.get("errcode"):
        raise RuntimeError(f"draft/add error {payload.get('errcode')}: {payload.get('errmsg')}")
    if not payload.get("media_id"):
        raise RuntimeError(f"draft/add missing media_id: {payload}")
    return payload


def cmd_publish_api(args: argparse.Namespace) -> int:
    article = Path(args.article).resolve()
    frontmatter, body = parse_frontmatter(article)
    title = args.title or frontmatter.get("title") or first_heading(body) or article.stem
    summary = args.summary or frontmatter.get("summary") or frontmatter.get("description") or ""
    author = args.author or frontmatter.get("author") or ""
    cover_value = args.cover or frontmatter.get("coverImage") or ""
    if not cover_value:
        raise RuntimeError("missing cover path")
    cover_path = normalize_path(cover_value, article.parent)
    if not cover_path.exists():
        raise RuntimeError(f"cover path does not exist: {cover_path}")
    repo = Path(args.repo).resolve() if args.repo else find_repo_from_article(article)
    html_path = Path(args.html).resolve() if args.html else article.with_suffix(".wechat.html")
    if not html_path.exists():
        render_article_to_path(article, html_path)
    content_html = html_path.read_text(encoding="utf-8")
    inline_sources = extract_image_sources(content_html)
    local_inline_images = [
        str(normalize_path(html.unescape(src), article.parent))
        for src in inline_sources
        if urllib.parse.urlparse(src).scheme not in {"http", "https"}
    ]
    if args.dry_run:
        credentials: dict[str, str] | None = None
        credential_error = ""
        try:
            credentials = resolve_credentials(repo)
        except Exception as exc:
            credential_error = str(exc)
        token_probe: dict[str, Any] = {"checked": False}
        if args.check_token:
            if credentials is None:
                raise RuntimeError(credential_error or "missing WeChat credentials")
            access_token = fetch_access_token(credentials["app_id"], credentials["app_secret"], args.timeout)
            token_probe = {"checked": True, "has_access_token": bool(access_token)}
        payload = {
            "status": "dry_run",
            "method": "wechat-api/draft-add",
            "would_create_draft": True,
            "title": title,
            "summary": summary,
            "author": author,
            "article_path": str(article),
            "html_path": str(html_path),
            "cover_path": str(cover_path),
            "cover_bytes": cover_path.stat().st_size,
            "content_html_bytes": len(content_html.encode("utf-8")),
            "inline_image_count": len(inline_sources),
            "local_inline_images": local_inline_images,
            "need_open_comment": args.need_open_comment,
            "only_fans_can_comment": args.only_fans_can_comment,
            "credential_source": credentials["source"] if credentials else None,
            "credential_error": credential_error,
            "token_probe": token_probe,
            "timestamp": now_utc(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    credentials = resolve_credentials(repo)
    access_token = fetch_access_token(credentials["app_id"], credentials["app_secret"], args.timeout)
    cover_upload = upload_material_image(access_token, cover_path, args.timeout)
    content_html, inline_uploads = upload_local_images_in_html(content_html, article.parent, access_token, args.timeout)
    draft = create_draft(
        access_token,
        title=title,
        author=author,
        digest=summary,
        content=content_html,
        thumb_media_id=str(cover_upload["media_id"]),
        need_open_comment=args.need_open_comment,
        only_fans_can_comment=args.only_fans_can_comment,
        timeout=args.timeout,
    )
    payload = {
        "status": "draft_created",
        "method": "wechat-api/draft-add",
        "title": title,
        "summary": summary,
        "author": author,
        "article_path": str(article),
        "html_path": str(html_path),
        "cover_path": str(cover_path),
        "cover_media_id": cover_upload.get("media_id"),
        "media_id": draft.get("media_id"),
        "inline_uploads": inline_uploads,
        "credential_source": credentials["source"],
        "timestamp": now_utc(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def find_repo_from_article(article: Path) -> Path:
    current = article.parent
    for parent in [current, *current.parents]:
        if (parent / "articles").exists() and (parent / "publish_logs").exists():
            return parent
    return Path.cwd().resolve()


def cmd_write_log(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    date_value = resolve_date(args.date)
    article = normalize_path(args.article, repo) if args.article else None
    frontmatter: dict[str, str] = {}
    body = ""
    if article and article.exists():
        frontmatter, body = parse_frontmatter(article)
    title = args.title or frontmatter.get("title") or first_heading(body)
    cover_image = args.cover_image or frontmatter.get("coverImage") or ""
    cover_status = {
        "status": args.cover_status,
        "method": args.cover_method,
        "source_path": args.cover_source,
        "prompt_path": args.cover_prompt,
        "final_path": cover_image,
        "reused_generic_cover": args.cover_status == "reused_generic_cover",
    }
    if args.status == "blocked":
        payload: dict[str, Any] = {
            "date": date_value,
            "status": "blocked",
            "blocked_at": args.timestamp or now_utc(),
            "local_timezone": args.local_timezone,
            "article_path": str(article) if article else "",
            "title": title,
            "method": args.method,
            "article_type": "news",
            "blocker_type": args.blocker_type,
            "error": args.error,
            "cover_status": cover_status,
            "frontmatter_coverImage": cover_image,
            "notes": args.notes,
        }
        output = repo / "publish_logs" / f"{date_value}-blocker.json"
    else:
        payload = {
            "date": date_value,
            "status": args.status,
            "timestamp": args.timestamp or now_utc(),
            "local_timezone": args.local_timezone,
            "article_path": str(article) if article else "",
            "title": title,
            "method": args.method,
            "article_type": "news",
            "media_id": args.media_id,
            "publish_url": args.publish_url,
            "cover_status": cover_status,
            "frontmatter_coverImage": cover_image,
            "notes": args.notes,
        }
        output = repo / "publish_logs" / f"{date_value}.json"
    write_json(output, payload)
    print(json.dumps({"log_path": str(output), "status": payload["status"]}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic operations for Zach WeChat Daily Publisher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Check whether a date already has a publish or blocker log")
    preflight.add_argument("--repo", required=True)
    preflight.add_argument("--date", default="today")
    preflight.add_argument("--fail-on-existing", action="store_true")
    preflight.set_defaults(handler=cmd_preflight)

    history = subparsers.add_parser("history-export", help="Export article and publish-log history")
    history.add_argument("--repo", required=True)
    history.add_argument("--output", default=".zach-wechat-daily-publisher/history.json")
    history.set_defaults(handler=cmd_history_export)

    discover = subparsers.add_parser("discover-topics", help="Discover topics from direct public sources only")
    discover.add_argument("--limit", type=int, default=8)
    discover.add_argument("--per-source", type=int, default=8)
    discover.add_argument("--output", default=".zach-wechat-daily-publisher/topics.json")
    discover.add_argument("--source-mode", choices=("auto", "hybrid", "direct"), default="hybrid")
    discover.add_argument("--history-file", default=".zach-wechat-daily-publisher/history.json")
    discover.add_argument("--history-window-days", type=int, default=7)
    discover.add_argument("--allow-high-risk", action="store_true")
    discover.add_argument("--max-risk", type=float, default=0.35)
    discover.add_argument("--min-reader-relevance", "--min-ai-relevance", dest="min_reader_relevance", type=float, default=0.46)
    discover.add_argument("--enrich-seo", action="store_true")
    discover.add_argument("--timeout", type=int, default=35)
    discover.set_defaults(handler=cmd_discover_topics)

    validate = subparsers.add_parser("validate-article", help="Validate publishable article frontmatter and cover")
    validate.add_argument("--article", required=True)
    validate.add_argument("--cover", default="")
    validate.set_defaults(handler=cmd_validate_article)

    cover = subparsers.add_parser("cover-prompt", help="Write cover source and prompt artifacts")
    cover.add_argument("--article", required=True)
    cover.add_argument("--work-dir", default="")
    cover.add_argument("--slug", default="")
    cover.add_argument("--cover-title", default="")
    cover.add_argument("--aspect", default="2.35:1")
    cover.add_argument("--cover-type", default="scene")
    cover.add_argument("--palette", default="warm with fresh teal and muted yellow accents")
    cover.add_argument("--rendering", default="flat-vector")
    cover.add_argument("--mood", default="balanced")
    cover.set_defaults(handler=cmd_cover_prompt)

    render = subparsers.add_parser("render", help="Render Markdown article to WeChat-ready HTML")
    render.add_argument("--article", required=True)
    render.add_argument("--output", default="")
    render.set_defaults(handler=cmd_render)

    publish = subparsers.add_parser("publish-api", help="Create a WeChat draft through API only")
    publish.add_argument("--article", required=True)
    publish.add_argument("--repo", default="")
    publish.add_argument("--cover", default="")
    publish.add_argument("--html", default="")
    publish.add_argument("--title", default="")
    publish.add_argument("--summary", default="")
    publish.add_argument("--author", default="")
    publish.add_argument("--need-open-comment", type=int, default=1)
    publish.add_argument("--only-fans-can-comment", type=int, default=0)
    publish.add_argument("--dry-run", action="store_true")
    publish.add_argument("--check-token", action="store_true")
    publish.add_argument("--timeout", type=int, default=30)
    publish.set_defaults(handler=cmd_publish_api)

    log = subparsers.add_parser("write-log", help="Write success or blocker publish log")
    log.add_argument("--repo", required=True)
    log.add_argument("--date", default="today")
    log.add_argument("--status", default="draft_created")
    log.add_argument("--article", default="")
    log.add_argument("--title", default="")
    log.add_argument("--method", default="wechat-api/draft-add")
    log.add_argument("--media-id", default="")
    log.add_argument("--publish-url", default="")
    log.add_argument("--blocker-type", default="")
    log.add_argument("--error", default="")
    log.add_argument("--notes", default="")
    log.add_argument("--timestamp", default="")
    log.add_argument("--local-timezone", default="Asia/Shanghai")
    log.add_argument("--cover-image", default="")
    log.add_argument("--cover-status", default="newly_generated")
    log.add_argument("--cover-method", default="")
    log.add_argument("--cover-source", default="")
    log.add_argument("--cover-prompt", default="")
    log.set_defaults(handler=cmd_write_log)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
