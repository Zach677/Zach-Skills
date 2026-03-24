#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from functools import lru_cache
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from pathlib import Path
from typing import Any


AI_KEYWORDS = {
    "ai",
    "人工智能",
    "大模型",
    "模型",
    "llm",
    "openai",
    "chatgpt",
    "gpt",
    "claude",
    "gemini",
    "copilot",
    "cursor",
    "agent",
    "智能体",
    "机器学习",
    "robot",
    "机器人",
    "科技",
    "tech",
    "开发者",
    "开发",
    "编程",
    "代码",
    "芯片",
    "算力",
    "软件",
    "产品",
    "平台",
    "应用",
}

SAFE_LANE_KEYWORDS = {
    "产品",
    "工具",
    "效率",
    "工作流",
    "开发者",
    "开源",
    "应用",
    "模型",
    "agent",
    "编程",
    "软件",
    "手机",
    "电脑",
    "芯片",
    "机器人",
}

RISK_KEYWORDS = {
    "财经",
    "金融",
    "投资",
    "证券",
    "股票",
    "基金",
    "保险",
    "银行",
    "医疗",
    "医生",
    "医院",
    "疾病",
    "药",
    "法律",
    "律师",
    "法院",
    "教育",
    "高考",
    "升学",
    "培训",
    "认证",
    "时政",
    "政治",
    "外交",
    "冲突",
    "战争",
    "公安",
}

RISK_CATEGORIES = {
    "国内时政",
    "海外新闻",
    "民生新闻",
    "财经",
    "金融",
    "医疗",
    "教育",
    "法律",
}

REQUIRED_SECTIONS = [
    "热点钩子",
    "事实拆解",
    "为什么现在重要",
    "工具或案例",
    "可执行建议",
    "结尾观点",
]

BAOYU_SKILL_SCRIPT_MAP = {
    "baoyu-markdown-to-html": "scripts/main.ts",
    "baoyu-post-to-wechat-article": "scripts/wechat-article.ts",
    "baoyu-post-to-wechat-check": "scripts/check-permissions.ts",
    "baoyu-post-to-wechat-api": "scripts/wechat-api.ts",
    "baoyu-image-gen": "scripts/main.ts",
    "baoyu-article-illustrator-batch": "scripts/build-batch.ts",
}

IMAGE_PROVIDER_DEFAULTS = {
    "google": {
        "env_any_keys": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "model_env": "GOOGLE_IMAGE_MODEL",
        "default_model": "gemini-3.1-flash-image-preview",
    },
    "openai": {
        "env_all_keys": ("OPENAI_API_KEY",),
        "model_env": "OPENAI_IMAGE_MODEL",
        "default_model": "gpt-image-1.5",
    },
    "openrouter": {
        "env_all_keys": ("OPENROUTER_API_KEY",),
        "model_env": "OPENROUTER_IMAGE_MODEL",
        "default_model": "google/gemini-3.1-flash-image-preview",
    },
    "dashscope": {
        "env_all_keys": ("DASHSCOPE_API_KEY",),
        "model_env": "DASHSCOPE_IMAGE_MODEL",
        "default_model": "qwen-image-2.0-pro",
    },
    "seedream": {
        "env_all_keys": ("ARK_API_KEY",),
        "model_env": "SEEDREAM_IMAGE_MODEL",
        "default_model": "doubao-seedream-5-0-260128",
    },
    "jimeng": {
        "env_all_keys": ("JIMENG_ACCESS_KEY_ID", "JIMENG_SECRET_ACCESS_KEY"),
        "model_env": "JIMENG_IMAGE_MODEL",
        "default_model": "jimeng_t2i_v40",
    },
    "replicate": {
        "env_all_keys": ("REPLICATE_API_TOKEN",),
        "model_env": "REPLICATE_IMAGE_MODEL",
        "default_model": "google/nano-banana-pro",
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ensure_opencli() -> str:
    opencli = shutil.which("opencli")
    if not opencli:
        raise SystemExit("opencli not found in PATH")
    return opencli


def has_bun() -> bool:
    return shutil.which("bun") is not None


def configured_env_file_paths() -> tuple[Path, ...]:
    return (
        Path.cwd() / ".baoyu-skills" / ".env",
        Path.home() / ".baoyu-skills" / ".env",
    )


def configured_baoyu_skill_roots() -> tuple[Path, ...]:
    roots: list[Path] = []

    explicit_root = os.environ.get("BAOYU_SKILLS_ROOT", "").strip()
    if explicit_root:
        roots.append(Path(explicit_root).expanduser())

    explicit_roots = os.environ.get("BAOYU_SKILLS_DIRS", "").strip()
    if explicit_roots:
        for raw in explicit_roots.split(os.pathsep):
            raw = raw.strip()
            if raw:
                roots.append(Path(raw).expanduser())

    codex_home = os.environ.get("CODEX_HOME", "").strip()
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")

    roots.extend(
        [
            Path.home() / ".agents" / "skills",
            Path.home() / ".codex" / "skills",
        ]
    )

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = str(root.expanduser())
        if resolved not in seen and root.exists():
            deduped.append(root)
            seen.add(resolved)
    return tuple(deduped)


@lru_cache(maxsize=None)
def find_baoyu_skill_dir(skill_name: str) -> Path | None:
    for root in configured_baoyu_skill_roots():
        direct = root / skill_name
        if (direct / "SKILL.md").exists():
            return direct
        for candidate in root.glob(f"**/{skill_name}/SKILL.md"):
            return candidate.parent
    return None


@lru_cache(maxsize=None)
def resolve_baoyu_script(script_key: str) -> Path | None:
    if script_key.startswith("baoyu-post-to-wechat"):
        skill_dir = find_baoyu_skill_dir("baoyu-post-to-wechat")
    elif script_key.startswith("baoyu-article-illustrator"):
        skill_dir = find_baoyu_skill_dir("baoyu-article-illustrator")
    elif script_key == "baoyu-markdown-to-html":
        skill_dir = find_baoyu_skill_dir("baoyu-markdown-to-html")
    elif script_key == "baoyu-image-gen":
        skill_dir = find_baoyu_skill_dir("baoyu-image-gen")
    else:
        skill_dir = None

    relative = BAOYU_SKILL_SCRIPT_MAP.get(script_key)
    if not skill_dir or not relative:
        return None
    path = skill_dir / relative
    return path if path.exists() else None


def resolve_runtime_env_value(key: str) -> str:
    direct = os.environ.get(key, "").strip()
    if direct:
        return direct
    for path in configured_env_file_paths():
        values = parse_env_file(path)
        value = values.get(key, "").strip()
        if value:
            return value
    return ""


def detect_image_provider_and_model(provider_arg: str, model_arg: str) -> tuple[str, str, bool]:
    normalized_provider = provider_arg.strip().lower() if provider_arg else "auto"
    normalized_model = model_arg.strip() if model_arg else "auto"

    if normalized_provider and normalized_provider != "auto":
        config = IMAGE_PROVIDER_DEFAULTS.get(normalized_provider, {})
        model = normalized_model if normalized_model and normalized_model != "auto" else resolve_runtime_env_value(config.get("model_env", "")) or config.get("default_model", "")
        all_keys = tuple(config.get("env_all_keys", ()))
        any_keys = tuple(config.get("env_any_keys", ()))
        credentials_present = (
            all(resolve_runtime_env_value(key) for key in all_keys) if all_keys else False
        ) or (
            any(resolve_runtime_env_value(key) for key in any_keys) if any_keys else False
        )
        return normalized_provider, model, bool(credentials_present)

    for provider in ("google", "openai", "openrouter", "dashscope", "seedream", "jimeng", "replicate"):
        config = IMAGE_PROVIDER_DEFAULTS[provider]
        all_keys = tuple(config.get("env_all_keys", ()))
        any_keys = tuple(config.get("env_any_keys", ()))
        provider_ready = (
            all(resolve_runtime_env_value(key) for key in all_keys) if all_keys else False
        ) or (
            any(resolve_runtime_env_value(key) for key in any_keys) if any_keys else False
        )
        if provider_ready:
            model = normalized_model if normalized_model and normalized_model != "auto" else resolve_runtime_env_value(config["model_env"]) or config["default_model"]
            return provider, model, True

    fallback_provider = "google"
    fallback_config = IMAGE_PROVIDER_DEFAULTS[fallback_provider]
    fallback_model = normalized_model if normalized_model and normalized_model != "auto" else resolve_runtime_env_value(fallback_config["model_env"]) or fallback_config["default_model"]
    return fallback_provider, fallback_model, False


def baoyu_markdown_available() -> bool:
    return has_bun() and resolve_baoyu_script("baoyu-markdown-to-html") is not None


def baoyu_wechat_available() -> bool:
    return (
        has_bun()
        and resolve_baoyu_script("baoyu-post-to-wechat-article") is not None
        and resolve_baoyu_script("baoyu-post-to-wechat-check") is not None
        and resolve_baoyu_script("baoyu-post-to-wechat-api") is not None
    )


def baoyu_image_gen_available() -> bool:
    return has_bun() and resolve_baoyu_script("baoyu-image-gen") is not None


def baoyu_illustrator_available() -> bool:
    return has_bun() and resolve_baoyu_script("baoyu-article-illustrator-batch") is not None


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_wechat_credentials() -> dict[str, str] | None:
    direct_app_id = os.environ.get("WECHAT_APP_ID", "").strip()
    direct_secret = os.environ.get("WECHAT_APP_SECRET", "").strip()
    if direct_app_id and direct_secret:
        return {
            "source": "process.env",
            "app_id": direct_app_id,
            "app_secret": direct_secret,
        }

    for path in configured_env_file_paths():
        values = parse_env_file(path)
        app_id = values.get("WECHAT_APP_ID", "").strip()
        app_secret = values.get("WECHAT_APP_SECRET", "").strip()
        if app_id and app_secret:
            return {
                "source": str(path),
                "app_id": app_id,
                "app_secret": app_secret,
            }
    return None


def probe_wechat_access_token(credentials: dict[str, str]) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "grant_type": "client_credential",
            "appid": credentials["app_id"],
            "secret": credentials["app_secret"],
        }
    )
    url = f"https://api.weixin.qq.com/cgi-bin/token?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", "ignore"))
    except HTTPError as exc:
        return {"status": "error", "reason": f"http_error:{exc.code}"}
    except URLError as exc:
        return {"status": "error", "reason": f"url_error:{exc.reason}"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}

    if payload.get("access_token"):
        return {
            "status": "ok",
            "source": credentials["source"],
            "expires_in": payload.get("expires_in"),
        }
    return {
        "status": "error",
        "source": credentials["source"],
        "errcode": payload.get("errcode"),
        "errmsg": payload.get("errmsg"),
    }


def run_command(args: list[str], timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def run_opencli_json(parts: list[str], timeout: int = 35) -> Any:
    ensure_opencli()
    cmd = ["opencli", *parts, "-f", "json"]
    result = run_command(cmd, timeout=timeout, check=True)
    output = result.stdout.strip()
    if not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"failed to parse JSON from {' '.join(cmd)}\n{output}") from exc


def parse_metric(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text.upper() == "N/A":
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return 0.0
    number = float(match.group(1))
    if "亿" in text:
        number *= 100000000
    elif "万" in text:
        number *= 10000
    elif re.search(r"\bk\b", text.lower()):
        number *= 1000
    elif re.search(r"\bm\b", text.lower()):
        number *= 1000000
    return number


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def normalize_rank(rank: Any, limit: int) -> float:
    try:
        rank_value = float(rank)
    except (TypeError, ValueError):
        return 0.5
    if limit <= 1:
        return 1.0
    normalized = 1.0 - ((rank_value - 1.0) / float(limit - 1))
    return clamp(max(normalized, 0.15))


def normalize_freshness(raw: dict[str, Any], limit: int) -> float:
    date_value = raw.get("date")
    if date_value:
        try:
            published = parsedate_to_datetime(str(date_value))
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
            age = dt.datetime.now(dt.timezone.utc) - published.astimezone(dt.timezone.utc)
            age_days = max(age.total_seconds() / 86400.0, 0.0)
            if age_days <= 1:
                return 1.0
            if age_days <= 7:
                return 0.85
            if age_days <= 30:
                return 0.65
            if age_days <= 180:
                return 0.35
            return 0.15
        except Exception:
            pass
    return normalize_rank(raw.get("rank"), limit)


def keyword_hits(text: str, keywords: set[str]) -> int:
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in text_lower)


def estimate_ai_relevance(title: str, category: str) -> float:
    combined = f"{title} {category}".strip()
    hits = keyword_hits(combined, AI_KEYWORDS)
    safe_hits = keyword_hits(combined, SAFE_LANE_KEYWORDS)
    base = 0.05 + min(hits, 5) * 0.17 + min(safe_hits, 3) * 0.07
    if any(keyword in title for keyword in ("发布", "更新", "开源", "上线", "模型", "工具")):
        base += 0.08
    return clamp(base)


def estimate_explainability(title: str, category: str) -> float:
    base = 0.42
    if re.search(r"\d", title):
        base += 0.08
    if re.search(r"[A-Za-z]{3,}", title):
        base += 0.12
    if 8 <= len(title) <= 36:
        base += 0.12
    if keyword_hits(title, AI_KEYWORDS) > 0:
        base += 0.16
    if category and category not in RISK_CATEGORIES:
        base += 0.06
    if any(word in title for word in ["直播", "热议", "怒了", "曝", "塌房"]):
        base -= 0.12
    return clamp(base)


def estimate_compliance_risk(title: str, category: str) -> float:
    combined = f"{title} {category}".strip()
    risk_hits = keyword_hits(combined, RISK_KEYWORDS)
    base = 0.08 + min(risk_hits, 4) * 0.16
    if category in RISK_CATEGORIES:
        base += 0.18
    if keyword_hits(combined, AI_KEYWORDS) > 0:
        base -= 0.08
    return clamp(base)


def build_angle_candidates(title: str) -> list[str]:
    candidates = [
        "不要停留在事件表面，直接解释它对 AI 工具链和工作流的实际影响",
        "从真实产品动作和协作方式切入，而不是重复趋势口号",
        "把这件事整理成接下来 30 天值得观察的变量和判断",
    ]
    title_lower = title.lower()
    if any(keyword in title_lower for keyword in ["openai", "gpt", "claude", "gemini", "agent"]):
        candidates[0] = "把这次模型或产品变化，拆成真实用户和开发者的直接影响"
    if any(keyword in title for keyword in ["开源", "发布", "上线", "更新"]):
        candidates[1] = "从发布本身退一步，看它会改变哪些工具和协作习惯"
    if any(keyword in title for keyword in ["芯片", "算力", "机器人"]):
        candidates[2] = "别停在新闻面，直接判断产业链和应用侧会先变哪里"
    return candidates


def build_facts(source: str, title: str, url: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
    facts = [
        {
            "claim": title,
            "source_url": url,
            "source_name": source,
            "status": "reported",
        }
    ]
    interesting = []
    for key in ("category", "hot_value", "heat", "tweets", "play", "answers", "date"):
        value = raw.get(key)
        if value:
            interesting.append((key, value))
    for key, value in interesting[:2]:
        facts.append(
            {
                "claim": f"{source} metadata: {key}={value}",
                "source_url": url,
                "source_name": source,
                "status": "reported",
            }
        )
    return facts


def normalize_topic(source: str, raw: dict[str, Any], limit: int) -> dict[str, Any]:
    title = (
        raw.get("title")
        or raw.get("word")
        or raw.get("topic")
        or raw.get("snippet")
        or ""
    ).strip()
    url = raw.get("url") or ""
    category = raw.get("category") or raw.get("source") or ""
    freshness = normalize_freshness(raw, limit)
    heat_metric = max(
        parse_metric(raw.get("hot_value")),
        parse_metric(raw.get("heat")),
        parse_metric(raw.get("tweets")),
        parse_metric(raw.get("play")),
        parse_metric(raw.get("answers")),
    )
    heat = clamp((heat_metric / 1000000.0) if heat_metric else freshness)
    ai_relevance = estimate_ai_relevance(title, category)
    explainability = estimate_explainability(title, category)
    compliance_risk = estimate_compliance_risk(title, category)
    final_score = clamp(
        freshness
        * ai_relevance
        * explainability
        * (1.0 - compliance_risk)
        * (0.6 + 0.4 * heat),
        0.0,
        1.0,
    )
    return {
        "source": source,
        "title": title,
        "url": url,
        "freshness": round(freshness, 4),
        "heat": round(heat, 4),
        "ai_relevance": round(ai_relevance, 4),
        "compliance_risk": round(compliance_risk, 4),
        "angle_candidates": build_angle_candidates(title),
        "facts": build_facts(source, title, url, raw),
        "score": round(final_score, 4),
        "score_breakdown": {
            "freshness": round(freshness, 4),
            "heat": round(heat, 4),
            "ai_relevance": round(ai_relevance, 4),
            "explainability": round(explainability, 4),
            "compliance_risk": round(compliance_risk, 4),
        },
        "category": category,
        "raw": raw,
    }


def discover_topics(args: argparse.Namespace) -> int:
    ensure_opencli()
    doctor = run_command(["opencli", "doctor"], timeout=20, check=False)
    if doctor.returncode != 0:
        raise RuntimeError(f"opencli doctor failed\n{doctor.stdout}\n{doctor.stderr}")

    sources = [
        ("weibo", ["weibo", "hot", "--limit", str(args.per_source)]),
        ("twitter", ["twitter", "trending", "--limit", str(args.per_source)]),
        ("zhihu", ["zhihu", "hot", "--limit", str(args.per_source)]),
        ("bilibili", ["bilibili", "hot", "--limit", str(args.per_source)]),
    ]

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for source, command in sources:
        try:
            payload = run_opencli_json(command, timeout=args.timeout)
            for item in payload:
                topic = normalize_topic(source, item, args.per_source)
                results.append(topic)
        except Exception as exc:
            failures.append({"source": source, "error": str(exc)})

    kept = [
        topic
        for topic in results
        if args.allow_high_risk or topic["compliance_risk"] < args.max_risk
    ]
    kept = [topic for topic in kept if topic["ai_relevance"] >= args.min_ai_relevance]

    strong_topics = [topic for topic in kept if topic["ai_relevance"] >= max(args.min_ai_relevance, 0.45)]

    if len(strong_topics) < args.limit:
        fallback_query = args.fallback_query or "AI 人工智能 OpenAI 大模型 Agent 科技"
        try:
            payload = run_opencli_json(
                [
                    "google",
                    "news",
                    fallback_query,
                    "--limit",
                    str(max(args.limit, args.per_source)),
                    "--lang",
                    "zh",
                    "--region",
                    "CN",
                ],
                timeout=args.timeout,
            )
            for item in payload:
                topic = normalize_topic("google-news", item, max(args.limit, args.per_source))
                if args.allow_high_risk or topic["compliance_risk"] < args.max_risk:
                    kept.append(topic)
        except Exception as exc:
            failures.append({"source": "google-news", "error": str(exc)})

    deduped: dict[str, dict[str, Any]] = {}
    for topic in kept:
        key = re.sub(r"\s+", "", topic["title"]).lower()
        existing = deduped.get(key)
        if existing is None or topic["score"] > existing["score"]:
            deduped[key] = topic

    topics = sorted(deduped.values(), key=lambda item: item["score"], reverse=True)[: args.limit]
    output = {
        "generated_at": now_iso(),
        "lane": "泛科技AI",
        "filters": {
            "allow_high_risk": args.allow_high_risk,
            "max_risk": args.max_risk,
            "min_ai_relevance": args.min_ai_relevance,
        },
        "topics": topics,
        "failures": failures,
    }
    write_json(args.output, output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path | None, payload: Any) -> None:
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_topic(payload: Any, topic_index: int) -> dict[str, Any]:
    if isinstance(payload, dict) and "topics" in payload:
        topics = payload["topics"]
    elif isinstance(payload, list):
        topics = payload
    else:
        topics = [payload]
    if not topics:
        raise ValueError("no topics found in input")
    try:
        return topics[topic_index]
    except IndexError as exc:
        raise ValueError(f"topic index {topic_index} out of range") from exc


def suggest_titles(topic: dict[str, Any]) -> list[str]:
    title = topic["title"]
    return [
        f"{title}之外，更值得关注的是 Agent 如何进入真实工作流",
        f"从{title}看模型竞争下一阶段的落点",
        f"围绕{title}，真正变化的不是分数，而是交付方式",
    ]


def scaffold_article(topic: dict[str, Any], benchmark_url: str | None) -> dict[str, Any]:
    summary_hint = f"用 2 到 3 句概括「{topic['title']}」的事实背景、核心判断和现实意义。语气克制，避免热搜体表达。"
    outline = [
        {"heading": section, "goal": goal}
        for section, goal in zip(
            REQUIRED_SECTIONS,
            [
                "用事件切入，但不要写成情绪复述。",
                "列出可验证事实，挂到来源上。",
                "解释现在发生的原因，以及为什么这次不是旧闻重写。",
                "给出具体工具、产品、案例或真实工作流。",
                "给出可操作的试点路径，而不是空泛建议。",
                "收束成一个明确判断，不要喊口号。",
            ],
        )
    ]
    body_lines = []
    for section in REQUIRED_SECTIONS:
        body_lines.append(f"## {section}")
        body_lines.append(f"[补这一节内容，主题：{topic['title']}]")
        body_lines.append("")
    return {
        "topic": topic,
        "titles": suggest_titles(topic),
        "summary": summary_hint,
        "outline": outline,
        "body_markdown": "\n".join(body_lines).strip(),
        "sources": [
            {
                "title": topic["title"],
                "url": topic["url"],
                "why_it_matters": "这是当前选题的起点来源，正文里的事实要继续补强。",
            }
        ],
        "cover_prompt": f"给微信公众号封面图，主题是：{topic['title']}。风格简洁、科技感、中文排版、不要廉价 AI 海报感。",
        "image_prompts": [
            f"为文章配一张科技感插图，主题：{topic['title']}，风格克制、信息密度高、适合公众号正文。",
        ],
        "keywords": [topic["title"], "AI", "科技", "工具", "工作流"],
        "fact_checklist": copy.deepcopy(topic["facts"]),
        "benchmark_article_url": benchmark_url,
        "style_notes": [
            "语气克制，避免互联网口头感。",
            "删空话，但也别写成硬邦邦的报告。",
            "先交代具体事件、人物或公司，再展开判断。",
            "把判断挂到具体产品、公司、用户动作上。",
            "不要写成热点复述稿。",
            "少用“打起来了”“值钱”“热闹”这类词。",
        ],
    }


def validate_article_draft(draft: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    titles = draft.get("titles", [])
    if not isinstance(titles, list) or len(titles) != 3 or any(not str(item).strip() for item in titles):
        errors.append("titles must be a non-empty list of exactly 3 items")
    if not str(draft.get("summary", "")).strip():
        errors.append("summary is required")
    if not isinstance(draft.get("outline"), list) or len(draft["outline"]) < len(REQUIRED_SECTIONS):
        errors.append("outline must include the required section skeleton")
    body_markdown = str(draft.get("body_markdown", "")).strip()
    if not body_markdown:
        errors.append("body_markdown is required")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in body_markdown:
            errors.append(f"body_markdown must contain section heading: ## {section}")
    sources = draft.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("sources must contain at least one source")
    keywords = draft.get("keywords", [])
    if not isinstance(keywords, list) or len([item for item in keywords if str(item).strip()]) < 3:
        errors.append("keywords must contain at least 3 non-empty items")
    facts = draft.get("fact_checklist", [])
    if not isinstance(facts, list) or len(facts) < 1:
        errors.append("fact_checklist must contain at least one item")
    return errors


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: render_image(m.group(1), m.group(2)), escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: render_link(m.group(1), m.group(2)),
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def render_link(label: str, target: str) -> str:
    target_unescaped = html.unescape(target)
    parsed = urllib.parse.urlparse(target_unescaped)
    if parsed.scheme in ("http", "https"):
        safe_target = html.escape(target_unescaped, quote=True)
        safe_label = html.escape(label)
        return f'<a href="{safe_target}">{safe_label}</a>'
    return html.escape(label)


def render_image(alt: str, target: str) -> str:
    target_unescaped = html.unescape(target)
    safe_alt = html.escape(alt, quote=True)
    safe_target = html.escape(target_unescaped, quote=True)
    return f'<img src="{safe_target}" alt="{safe_alt}" />'


def markdown_to_weixin_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    blocks: list[str] = []
    current_list_type: str | None = None
    current_list_items: list[str] = []

    def flush_list() -> None:
        nonlocal current_list_type, current_list_items
        if current_list_type and current_list_items:
            items = "".join(f"<li>{item}</li>" for item in current_list_items)
            blocks.append(f"<{current_list_type}>{items}</{current_list_type}>")
        current_list_type = None
        current_list_items = []

    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            joined = "<br />".join(inline_markdown(line) for line in paragraph_buffer)
            blocks.append(f"<p>{joined}</p>")
        paragraph_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        ordered_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        unordered_match = re.match(r"^[-*]\s+(.*)$", stripped)
        blockquote_match = re.match(r"^>\s?(.*)$", stripped)

        if heading_match:
            flush_paragraph()
            flush_list()
            level = min(len(heading_match.group(1)), 4)
            blocks.append(f"<h{level}>{inline_markdown(heading_match.group(2))}</h{level}>")
            continue

        if blockquote_match:
            flush_paragraph()
            flush_list()
            blocks.append(f"<blockquote><p>{inline_markdown(blockquote_match.group(1))}</p></blockquote>")
            continue

        if ordered_match:
            flush_paragraph()
            if current_list_type not in (None, "ol"):
                flush_list()
            current_list_type = "ol"
            current_list_items.append(inline_markdown(ordered_match.group(1)))
            continue

        if unordered_match:
            flush_paragraph()
            if current_list_type not in (None, "ul"):
                flush_list()
            current_list_type = "ul"
            current_list_items.append(inline_markdown(unordered_match.group(1)))
            continue

        paragraph_buffer.append(stripped)

    flush_paragraph()
    flush_list()
    return "\n".join(blocks)


def write_article(args: argparse.Namespace) -> int:
    topic_payload = load_json(args.topic)
    topic = pick_topic(topic_payload, args.topic_index)

    if args.scaffold:
        scaffold = scaffold_article(topic, args.benchmark_url)
        write_json(args.scaffold, scaffold)
        print(json.dumps(scaffold, ensure_ascii=False, indent=2))
        return 0

    if not args.draft or not args.output:
        raise SystemExit("--draft and --output are required when not using --scaffold")

    draft = load_json(args.draft)
    errors = validate_article_draft(draft)
    if errors:
        raise SystemExit("invalid draft:\n- " + "\n- ".join(errors))

    package = copy.deepcopy(draft)
    package["topic"] = topic
    package["body_html"] = markdown_to_weixin_html(package["body_markdown"])
    package["word_count"] = len(re.findall(r"\S+", package["body_markdown"]))
    package["generated_at"] = now_iso()
    package["validation"] = {
        "required_sections": REQUIRED_SECTIONS,
        "errors": [],
        "html_safe": True,
    }
    package["renderers"] = build_renderer_artifacts(package, Path(args.output))
    write_json(args.output, package)
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


def build_renderer_artifacts(package: dict[str, Any], output_path: Path) -> dict[str, Any]:
    artifacts: dict[str, Any] = {
        "internal": {
            "status": "ok",
            "html_inline": True,
        }
    }
    markdown_script = resolve_baoyu_script("baoyu-markdown-to-html")
    if not markdown_script:
        artifacts["baoyu"] = {
            "status": "unavailable",
            "reason": "bun or baoyu-markdown-to-html script not found",
        }
        return artifacts

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{output_path.stem}.weixin.md"
    title = str(package["titles"][0]).strip()
    markdown_payload = f"# {title}\n\n{package['body_markdown'].strip()}\n"
    md_path.write_text(markdown_payload, encoding="utf-8")

    try:
        result = run_command(
            [
                "bun",
                str(markdown_script),
                str(md_path),
                "--theme",
                "modern",
                "--color",
                "orange",
                "--title",
                title,
            ],
            timeout=60,
            check=True,
        )
        data = json.loads(result.stdout.strip())
        artifacts["baoyu"] = {
            "status": "ok",
            "markdown_path": str(md_path),
            "html_path": data.get("htmlPath"),
            "backup_path": data.get("backupPath"),
        }
    except Exception as exc:
        artifacts["baoyu"] = {
            "status": "error",
            "markdown_path": str(md_path),
            "reason": str(exc),
        }
    return artifacts


def slugify(value: str, max_words: int = 5) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\s-]", " ", value, flags=re.UNICODE)
    tokens = [token for token in re.split(r"[\s_-]+", cleaned) if token]
    if not tokens:
        return "asset"
    shortened = tokens[:max_words]
    ascii_tokens = []
    for token in shortened:
        if re.fullmatch(r"[A-Za-z0-9]+", token):
            ascii_tokens.append(token.lower())
        else:
            ascii_tokens.append(token)
    return "-".join(ascii_tokens)


def detect_visual_lane(package: dict[str, Any]) -> str:
    title = " ".join(package.get("titles", []))
    body = str(package.get("body_markdown", ""))
    text = f"{title}\n{body}"
    if any(word in text for word in ["架构", "系统", "模块", "组件"]):
        return "system-design"
    if any(word in text for word in ["流程", "工作流", "步骤", "试点"]):
        return "process-flow"
    return "tech-explainer"


def choose_cover_style(package: dict[str, Any]) -> dict[str, str]:
    title = str(package.get("titles", [""])[0])
    text = f"{title}\n{package.get('summary', '')}"
    style = "blueprint"
    cover_type = "conceptual"
    if any(word in text for word in ["观点", "竞争", "交锋", "判断"]):
        style = "editorial-infographic"
    if any(word in text for word in ["系统", "架构", "工作流", "Agent"]):
        cover_type = "conceptual"
    return {
        "type": cover_type,
        "style": style,
        "aspect": "16:9",
    }


def build_illustration_entries(package: dict[str, Any]) -> list[dict[str, str]]:
    entries = [
        {
            "section": "事实拆解",
            "type": "comparison",
            "purpose": "把模型竞争的关注点从回答能力转到任务执行与交付能力。",
            "visual_content": "左右对比图：左侧是传统模型比较维度，右侧是新一轮 Agent 比较维度。包含上下文处理、工具调用、任务稳定性、交付方式等标签。",
            "filename": "01-comparison-model-vs-agent.png",
        },
        {
            "section": "为什么现在重要",
            "type": "framework",
            "purpose": "解释“模型能力”与“交付能力”之间的关系。",
            "visual_content": "一个三层框架图：底层模型能力，中层工作流编排，上层业务交付与组织效率。强调真正的差距发生在中上层。",
            "filename": "02-framework-delivery-stack.png",
        },
        {
            "section": "可执行建议",
            "type": "flowchart",
            "purpose": "把团队或个人试点 Agent 的最小路径讲清楚。",
            "visual_content": "流程图：选择高频低风险任务 -> 定义输入模板 -> 定义输出格式 -> 设定验收标准 -> 人工复核 -> 复盘优化。",
            "filename": "03-flowchart-agent-pilot.png",
        },
    ]
    lane = detect_visual_lane(package)
    if lane == "system-design":
        entries[0]["type"] = "framework"
        entries[0]["visual_content"] = "系统框架图：模型、工具层、任务层、业务层之间的依赖关系。"
    return entries


def render_outline(entries: list[dict[str, str]], preset: str, density: str, style: str) -> str:
    lines = [
        "---",
        f"preset: {preset}",
        f"density: {density}",
        f"style: {style}",
        f"image_count: {len(entries)}",
        "---",
        "",
    ]
    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"## Illustration {index}",
                f"**Position**: after section `{entry['section']}`",
                f"**Purpose**: {entry['purpose']}",
                f"**Visual Content**: {entry['visual_content']}",
                f"**Filename**: {entry['filename']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_prompt(package: dict[str, Any], entry: dict[str, str], index: int, style: str) -> str:
    title = str(package.get("titles", [""])[0]).strip()
    summary = str(package.get("summary", "")).strip()
    return textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        illustration_index: {index}
        type: "{entry['type']}"
        style: "{style}"
        section: "{entry['section']}"
        ---

        Create an explanatory article illustration for a Chinese AI commentary article.

        SECTION
        {entry['section']}

        PURPOSE
        {entry['purpose']}

        VISUAL CONTENT
        {entry['visual_content']}

        ARTICLE CONTEXT
        {summary}

        STYLE
        Clean, editorial, information-first. Avoid generic AI art, glowing brains, random robots, and decorative filler.

        LABELS
        Use concise Chinese labels where the diagram benefits from text. Keep wording precise and publication-ready.

        OUTPUT
        16:9 PNG, suitable for WeChat article insertion.
        """
    )


def prepare_visuals(args: argparse.Namespace) -> int:
    package_path = Path(args.package).resolve()
    package = load_json(package_path)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    title = str(package.get("titles", [""])[0]).strip()
    lane = detect_visual_lane(package)
    cover = choose_cover_style(package)
    preset = "tech-explainer" if lane != "process-flow" else "process-flow"
    entries = build_illustration_entries(package)
    provider, model, credentials_present = detect_image_provider_and_model(args.provider, args.model)

    cover_dir = output_dir / "cover"
    illustrations_dir = output_dir / "illustrations"
    prompts_dir = illustrations_dir / "prompts"
    images_dir = illustrations_dir / "images"
    cover_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    article_markdown = output_dir / "article.weixin.md"
    article_markdown.write_text(
        f"# {title}\n\n{str(package.get('body_markdown', '')).strip()}\n",
        encoding="utf-8",
    )

    cover_brief = textwrap.dedent(
        f"""\
        # Cover Brief

        标题：{title}

        摘要：
        {package.get('summary', '')}

        推荐 Baoyu 封面参数：
        - type: {cover['type']}
        - style: {cover['style']}
        - aspect: {cover['aspect']}

        建议方向：
        - 用“交付阶段”“工作流”“Agent 系统”这样的概念做视觉中心
        - 少做戏剧化冲突，多做结构化表达
        - 保持科技感，但不要廉价 AI 海报风

        推荐命令：
        /baoyu-cover-image {article_markdown} --quick --type {cover['type']} --style {cover['style']} --aspect {cover['aspect']}
        """
    )
    (cover_dir / "cover-brief.md").write_text(cover_brief, encoding="utf-8")

    outline_text = render_outline(entries, preset=preset, density="balanced", style="blueprint")
    outline_path = illustrations_dir / "outline.md"
    outline_path.write_text(outline_text, encoding="utf-8")

    prompt_paths: list[str] = []
    for index, entry in enumerate(entries, start=1):
        prompt_path = prompts_dir / f"{index:02d}-{entry['type']}-{slugify(entry['section'])}.md"
        prompt_path.write_text(render_prompt(package, entry, index, style="blueprint"), encoding="utf-8")
        prompt_paths.append(str(prompt_path))

    batch_path = illustrations_dir / "batch.json"
    build_batch_result: dict[str, Any]
    batch_builder = resolve_baoyu_script("baoyu-article-illustrator-batch")
    if batch_builder:
        result = run_command(
            [
                "bun",
                str(batch_builder),
                "--outline",
                str(outline_path),
                "--prompts",
                str(prompts_dir),
                "--output",
                str(batch_path),
                "--images-dir",
                str(images_dir),
                "--provider",
                provider,
                "--model",
                model,
                "--ar",
                args.aspect_ratio,
                "--quality",
                args.quality,
            ],
            timeout=60,
            check=True,
        )
        build_batch_result = {
            "status": "ok",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    else:
        tasks = []
        for index, entry in enumerate(entries, start=1):
            tasks.append(
                {
                    "id": f"illustration-{index:02d}",
                    "promptFiles": [prompt_paths[index - 1]],
                    "image": str(images_dir / entry["filename"]),
                    "provider": provider,
                    "model": model,
                    "ar": args.aspect_ratio,
                    "quality": args.quality,
                }
            )
        batch_path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        build_batch_result = {
            "status": "fallback",
            "reason": "baoyu-article-illustrator build-batch script unavailable",
        }

    commands = {
        "cover_skill": f"/baoyu-cover-image {article_markdown} --quick --type {cover['type']} --style {cover['style']} --aspect {cover['aspect']}",
        "illustrator_skill": f"/baoyu-article-illustrator {article_markdown} --preset {preset} --density balanced",
        "image_batch": (
            f"bun {resolve_baoyu_script('baoyu-image-gen')} --batchfile {batch_path}"
            if baoyu_image_gen_available() and resolve_baoyu_script("baoyu-image-gen") is not None
            else None
        ),
    }
    write_json(output_dir / "commands.json", commands)

    manifest = {
        "generated_at": now_iso(),
        "package_path": str(package_path),
        "article_markdown": str(article_markdown),
        "visual_lane": lane,
        "cover": {
            "brief_path": str(cover_dir / "cover-brief.md"),
            "type": cover["type"],
            "style": cover["style"],
            "aspect": cover["aspect"],
        },
        "image_backend": {
            "provider": provider,
            "model": model,
            "credentials_present": credentials_present,
        },
        "illustrations": {
            "preset": preset,
            "outline_path": str(outline_path),
            "prompts_dir": str(prompts_dir),
            "images_dir": str(images_dir),
            "entries": entries,
            "batch_path": str(batch_path),
            "build_batch_result": build_batch_result,
        },
        "commands": commands,
        "baoyu_support": {
            "cover_skill_available": find_baoyu_skill_dir("baoyu-cover-image") is not None,
            "illustrator_skill_available": find_baoyu_skill_dir("baoyu-article-illustrator") is not None,
            "image_gen_available": baoyu_image_gen_available(),
        },
    }
    write_json(output_dir / "visual-brief.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def extract_image_sources(html_text: str) -> list[str]:
    return re.findall(r'<img\b[^>]*src="([^"]+)"', html_text)


def is_remote_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https")


def download_image(url: str, destination: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        guessed_ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
        original_name = Path(urllib.parse.urlparse(url).path).name
        suffix = Path(original_name).suffix or guessed_ext or ".img"
        final_path = destination.with_suffix(suffix)
        final_path.write_bytes(response.read())
        return final_path


def stage_images(html_text: str, package_path: Path, staging_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    image_dir = staging_dir / "body-images"
    image_dir.mkdir(parents=True, exist_ok=True)
    replacements: list[dict[str, Any]] = []
    output_html = html_text

    for index, src in enumerate(extract_image_sources(html_text), start=1):
        placeholder = f"__WX_IMAGE_{index}__"
        target_file = image_dir / f"image-{index}"
        if is_remote_url(src):
            local_path = download_image(src, target_file)
        else:
            raw_path = Path(src)
            if not raw_path.is_absolute():
                raw_path = (package_path.parent / raw_path).resolve()
            if not raw_path.exists():
                raise FileNotFoundError(f"image path not found: {raw_path}")
            local_path = image_dir / raw_path.name
            shutil.copy2(raw_path, local_path)
        replacements.append(
            {
                "placeholder": placeholder,
                "original_src": src,
                "local_path": str(local_path),
            }
        )
        output_html = output_html.replace(f'src="{src}"', f'src="{placeholder}"')
    return output_html, replacements


def deliver_weixin(args: argparse.Namespace) -> int:
    ensure_opencli()
    package_path = Path(args.package).resolve()
    package = load_json(package_path)
    staging_dir = Path(args.staging_dir).resolve()
    staging_dir.mkdir(parents=True, exist_ok=True)

    doctor = run_command(["opencli", "doctor"], timeout=20, check=False)
    doctor_ok = doctor.returncode == 0

    body_html = str(package.get("body_html", "")).strip()
    if not body_html:
        raise SystemExit("package is missing body_html")

    staged_html, images = stage_images(body_html, package_path, staging_dir)
    html_path = staging_dir / "body.weixin.html"
    html_path.write_text(staged_html + "\n", encoding="utf-8")

    opencli_steps = [
        "opencli doctor",
        'opencli explore https://mp.weixin.qq.com --goal "understand draft editor flow for article creation"',
        "确保 Chrome 已打开，且公众号后台已经登录",
        "打开新建图文页，上传 body-images 里的图片，按 placeholder 顺序替换正文图片",
        "填入标题、摘要、关键词、正文，停在草稿或待发布页",
        "不要点击最终发布，交给人工过稿",
    ]

    if args.prepare_session:
        try:
            session_probe = run_command(
                [
                    "opencli",
                    "explore",
                    "https://mp.weixin.qq.com",
                    "--goal",
                    "understand draft editor flow for article creation",
                ],
                timeout=args.timeout,
                check=False,
            )
            opencli_probe = {
                "returncode": session_probe.returncode,
                "stdout": session_probe.stdout.strip(),
                "stderr": session_probe.stderr.strip(),
            }
        except Exception as exc:
            opencli_probe = {"error": str(exc)}
    else:
        opencli_probe = {"skipped": True}

    baoyu_info = build_baoyu_delivery_info(package, staging_dir)

    manifest = {
        "generated_at": now_iso(),
        "package_path": str(package_path),
        "doctor_ok": doctor_ok,
        "dry_run": args.dry_run,
        "title": package["titles"][0],
        "all_titles": package["titles"],
        "summary": package["summary"],
        "keywords": package["keywords"],
        "sources": package["sources"],
        "fact_checklist": package["fact_checklist"],
        "cover_prompt": package.get("cover_prompt", ""),
        "image_prompts": package.get("image_prompts", []),
        "body_html_path": str(html_path),
        "body_html_with_placeholders": staged_html,
        "images": images,
        "opencli_steps": opencli_steps,
        "manual_gate": "Human review required before publish.",
        "opencli_probe": opencli_probe,
        "baoyu_integration": baoyu_info,
    }
    write_json(staging_dir / "delivery-manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def build_baoyu_delivery_info(package: dict[str, Any], staging_dir: Path) -> dict[str, Any]:
    if not baoyu_wechat_available():
        return {
            "status": "unavailable",
            "reason": "bun or baoyu-post-to-wechat scripts not found",
        }

    markdown_path = None
    baoyu_renderer = package.get("renderers", {}).get("baoyu", {})
    if baoyu_renderer.get("status") == "ok":
        markdown_path = baoyu_renderer.get("markdown_path")

    if not markdown_path:
        markdown_path = str(staging_dir / "article.weixin.md")
        body_md = str(package.get("body_markdown", "")).strip()
        title = str(package["titles"][0]).strip()
        Path(markdown_path).write_text(f"# {title}\n\n{body_md}\n", encoding="utf-8")

    check_script = resolve_baoyu_script("baoyu-post-to-wechat-check")
    article_script = resolve_baoyu_script("baoyu-post-to-wechat-article")
    api_script = resolve_baoyu_script("baoyu-post-to-wechat-api")
    if not check_script or not article_script or not api_script:
        return {
            "status": "unavailable",
            "reason": "bun or baoyu-post-to-wechat scripts not found",
        }

    check = run_command(["bun", str(check_script)], timeout=60, check=False)
    credentials = resolve_wechat_credentials()
    token_probe = probe_wechat_access_token(credentials) if credentials else {"status": "unavailable"}
    draft_command = [
        "bun",
        str(article_script),
        "--markdown",
        str(markdown_path),
        "--theme",
        "modern",
        "--color",
        "orange",
        "--summary",
        str(package.get("summary", "")),
        "--submit",
    ]
    api_dry_run_command = [
        "bun",
        str(api_script),
        str(markdown_path),
        "--dry-run",
    ]
    api_publish_command = [
        "bun",
        str(api_script),
        str(markdown_path),
    ]
    preferred_method = "api" if credentials and token_probe.get("status") == "ok" else "browser"
    return {
        "status": "available",
        "preferred": True,
        "recommended_method": preferred_method,
        "check_permissions": {
            "returncode": check.returncode,
            "stdout": check.stdout.strip(),
            "stderr": check.stderr.strip(),
        },
        "credentials_detected": bool(credentials),
        "credential_source": credentials["source"] if credentials else None,
        "token_probe": token_probe,
        "browser_draft_command": " ".join(shlex_quote(part) for part in draft_command),
        "api_dry_run_command": " ".join(shlex_quote(part) for part in api_dry_run_command),
        "api_publish_command": " ".join(shlex_quote(part) for part in api_publish_command),
        "notes": [
            "browser method writes into the WeChat article editor and saves a draft",
            "api method requires AppID/AppSecret and writes to draft/add",
            "final publish is still a separate step in the WeChat backend",
        ],
    }


def shlex_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=+-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WeChat hot-writer helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover-topics", help="Aggregate hot topics and score them")
    discover.add_argument("--limit", type=int, default=8)
    discover.add_argument("--per-source", type=int, default=8)
    discover.add_argument("--output", default="out/topics.json")
    discover.add_argument("--fallback-query", default="")
    discover.add_argument("--allow-high-risk", action="store_true")
    discover.add_argument("--max-risk", type=float, default=0.45)
    discover.add_argument("--min-ai-relevance", type=float, default=0.35)
    discover.add_argument("--timeout", type=int, default=35)
    discover.set_defaults(handler=discover_topics)

    write = subparsers.add_parser("write-article", help="Scaffold or package an article")
    write.add_argument("--topic", required=True, help="Path to a topic JSON or discover-topics output")
    write.add_argument("--topic-index", type=int, default=0)
    write.add_argument("--scaffold", help="Write a draft scaffold JSON to this path")
    write.add_argument("--draft", help="Path to a completed draft JSON")
    write.add_argument("--output", help="Path for the packaged article JSON")
    write.add_argument("--benchmark-url", default="")
    write.set_defaults(handler=write_article)

    visuals = subparsers.add_parser("prepare-visuals", help="Prepare Baoyu-friendly cover and illustration assets")
    visuals.add_argument("--package", required=True, help="Path to the packaged article JSON")
    visuals.add_argument("--output-dir", default="out/visuals")
    visuals.add_argument("--provider", default="auto")
    visuals.add_argument("--model", default="auto")
    visuals.add_argument("--aspect-ratio", default="16:9")
    visuals.add_argument("--quality", default="2k")
    visuals.set_defaults(handler=prepare_visuals)

    deliver = subparsers.add_parser("deliver-weixin", help="Stage WeChat delivery assets")
    deliver.add_argument("--package", required=True, help="Path to the packaged article JSON")
    deliver.add_argument("--staging-dir", default="out/weixin")
    deliver.add_argument("--dry-run", action="store_true")
    deliver.add_argument("--prepare-session", action="store_true")
    deliver.add_argument("--timeout", type=int, default=40)
    deliver.set_defaults(handler=deliver_weixin)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
