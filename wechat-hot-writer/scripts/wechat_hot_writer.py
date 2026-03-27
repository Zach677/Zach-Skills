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

from topic_intelligence import (
    append_history_entry,
    apply_topic_intelligence,
    fetch_direct_hotspots,
    fetch_wechat_article_summary,
    get_wechat_access_token,
    load_history_payload,
    merge_stats_into_history,
    save_history_payload,
)


AI_TOPIC_KEYWORDS = {
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

WELLNESS_KEYWORDS = {
    "健康",
    "养生",
    "睡眠",
    "失眠",
    "饮食",
    "吃饭",
    "吃法",
    "走路",
    "散步",
    "关节",
    "腰腿",
    "血糖",
    "血压",
    "血脂",
    "消化",
    "肠胃",
    "胃",
    "心脏",
    "体重",
    "季节",
    "春天",
    "夏天",
    "秋天",
    "冬天",
    "保健",
}

SILVER_LIFE_KEYWORDS = {
    "中老年",
    "老人",
    "老年",
    "银发",
    "退休",
    "养老",
    "社区",
    "父母",
    "爸妈",
    "妈妈",
    "爸爸",
    "家人",
    "长辈",
}

FAMILY_KEYWORDS = {
    "家庭",
    "家里",
    "子女",
    "父母",
    "爸妈",
    "老人",
    "长辈",
    "照护",
    "陪伴",
    "退休",
    "亲戚",
}

PUBLIC_INTEREST_KEYWORDS = {
    "防骗",
    "被骗",
    "骗局",
    "提醒",
    "注意",
    "误区",
    "很多人",
    "小心",
    "风险",
    "故事",
    "人物",
    "情感",
    "社会",
    "食品",
    "买菜",
    "消费",
    "回收",
    "价格",
    "旧手机",
    "清明",
    "扫墓",
    "祭扫",
    "日常",
    "生活",
    "小龙虾",
}

READER_PRIORITY_KEYWORDS = WELLNESS_KEYWORDS | SILVER_LIFE_KEYWORDS | FAMILY_KEYWORDS | PUBLIC_INTEREST_KEYWORDS

SHAREABLE_KEYWORDS = {
    "很多人",
    "提醒",
    "注意",
    "别",
    "小心",
    "误区",
    "家里",
    "父母",
    "老人",
    "中老年",
    "退休",
    "被骗",
    "故事",
    "终于",
    "原来",
    "日常",
}

GENERAL_RISK_KEYWORDS = {
    "财经",
    "金融",
    "投资",
    "证券",
    "股票",
    "基金",
    "保险",
    "银行",
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

MEDICAL_RISK_KEYWORDS = {
    "医疗",
    "医生",
    "医院",
    "疾病",
    "诊断",
    "治疗",
    "药",
    "药品",
    "处方",
    "手术",
    "癌",
    "肿瘤",
}

MIRACLE_CLAIM_KEYWORDS = {
    "神药",
    "包治",
    "根治",
    "治好",
    "逆转",
    "偏方",
    "秘方",
    "速效",
}

RISK_CATEGORIES = {
    "国内时政",
    "海外新闻",
    "财经",
    "金融",
    "医疗",
    "教育",
    "法律",
}

REQUIRED_SECTIONS = [
    "热点钩子",
    "这事和谁最相关",
    "关键事实",
    "常见误区或案例",
    "日常怎么做",
    "最后提醒",
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
        published = None
        try:
            published = dt.datetime.fromisoformat(str(date_value))
        except Exception:
            try:
                published = parsedate_to_datetime(str(date_value))
            except Exception:
                published = None
        if published is not None:
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
    return normalize_rank(raw.get("rank"), limit)


def keyword_hits(text: str, keywords: set[str]) -> int:
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in text_lower)


def estimate_reader_relevance(title: str, category: str) -> float:
    combined = f"{title} {category}".strip()
    priority_hits = keyword_hits(combined, READER_PRIORITY_KEYWORDS)
    wellness_hits = keyword_hits(combined, WELLNESS_KEYWORDS)
    family_hits = keyword_hits(combined, FAMILY_KEYWORDS)
    public_hits = keyword_hits(combined, PUBLIC_INTEREST_KEYWORDS)
    ai_hits = keyword_hits(combined, AI_TOPIC_KEYWORDS)
    base = 0.12
    base += min(priority_hits, 6) * 0.1
    base += min(wellness_hits, 3) * 0.05
    base += min(family_hits, 3) * 0.06
    base += min(public_hits, 3) * 0.05
    if re.search(r"\d", title):
        base += 0.05
    if any(keyword in title for keyword in ("提醒", "注意", "误区", "很多人", "家里", "父母", "老人")):
        base += 0.08
    if any(keyword in title for keyword in ("回收", "价格", "清明", "扫墓", "祭扫")):
        base += 0.08
    if ai_hits > 0 and priority_hits == 0 and public_hits == 0:
        base -= 0.38
    elif ai_hits > 0:
        base -= 0.04
    return clamp(base)


def estimate_explainability(title: str, category: str) -> float:
    base = 0.42
    if re.search(r"\d", title):
        base += 0.08
    if 8 <= len(title) <= 36:
        base += 0.12
    if keyword_hits(title, READER_PRIORITY_KEYWORDS) > 0:
        base += 0.14
    if category and category not in RISK_CATEGORIES:
        base += 0.06
    if any(word in title for word in ["直播", "怒了", "曝", "塌房", "热议"]):
        base -= 0.12
    return clamp(base)


def estimate_shareability(title: str, category: str) -> float:
    combined = f"{title} {category}".strip()
    base = 0.34
    base += min(keyword_hits(combined, SHAREABLE_KEYWORDS), 4) * 0.1
    base += min(keyword_hits(combined, FAMILY_KEYWORDS), 2) * 0.06
    if re.search(r"\d", title):
        base += 0.05
    if any(word in title for word in ["提醒", "注意", "小心", "误区", "很多人", "原来", "终于"]):
        base += 0.1
    if any(word in title for word in ["价格", "回收", "清明", "扫墓", "家里"]):
        base += 0.06
    if keyword_hits(combined, AI_TOPIC_KEYWORDS) > 0 and keyword_hits(combined, READER_PRIORITY_KEYWORDS) == 0:
        base -= 0.16
    return clamp(base)


def estimate_compliance_risk(title: str, category: str) -> float:
    combined = f"{title} {category}".strip()
    risk_hits = keyword_hits(combined, GENERAL_RISK_KEYWORDS | MEDICAL_RISK_KEYWORDS)
    base = 0.08 + min(risk_hits, 4) * 0.16
    if category in RISK_CATEGORIES:
        base += 0.18
    if keyword_hits(combined, MIRACLE_CLAIM_KEYWORDS) > 0:
        base += 0.22
    if keyword_hits(combined, WELLNESS_KEYWORDS) > 0 and keyword_hits(combined, MEDICAL_RISK_KEYWORDS) == 0:
        base -= 0.04
    return clamp(base)


def build_angle_candidates(title: str) -> list[str]:
    candidates = [
        "别停在热点表面，先讲清这件事和哪类人最相关",
        "把容易被带偏的误区拆开，再说真正该注意的点",
        "最后落到普通家庭今天就能执行的动作，不空喊口号",
    ]
    title_lower = title.lower()
    if any(keyword in title for keyword in WELLNESS_KEYWORDS):
        candidates[0] = "先分清这件事属于日常提醒、习惯调整，还是已经超出自我管理边界"
        candidates[1] = "把常见误区、过度焦虑、和真正靠谱的做法分开说"
        candidates[2] = "结尾要交代哪些情况别硬扛，应该尽快求助专业人士"
    elif any(keyword in title for keyword in FAMILY_KEYWORDS | {"被骗", "防骗", "骗局"}):
        candidates[0] = "先说这事在家庭场景里最容易发生在哪里"
        candidates[1] = "把最容易忽视的预警信号讲清楚，别写成纯情绪文"
        candidates[2] = "给出一份家里人今天就能照着做的提醒清单"
    elif any(keyword in title_lower for keyword in ["openai", "gpt", "claude", "gemini", "agent", "ai"]):
        candidates[0] = "只有当它和普通人的消费、食品、民生或家庭场景有明确关系时才保留"
        candidates[1] = "把技术热点翻译成大众能直接感知的生活影响"
        candidates[2] = "别写圈内黑话，直接说对普通家庭到底有没有用"
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
    reader_relevance = estimate_reader_relevance(title, category)
    explainability = estimate_explainability(title, category)
    shareability = estimate_shareability(title, category)
    compliance_risk = estimate_compliance_risk(title, category)
    final_score = clamp(
        freshness
        * reader_relevance
        * explainability
        * shareability
        * (1.0 - compliance_risk)
        * (0.55 + 0.45 * heat),
        0.0,
        1.0,
    )
    return {
        "source": source,
        "title": title,
        "url": url,
        "freshness": round(freshness, 4),
        "heat": round(heat, 4),
        "reader_relevance": round(reader_relevance, 4),
        "shareability": round(shareability, 4),
        "compliance_risk": round(compliance_risk, 4),
        "angle_candidates": build_angle_candidates(title),
        "facts": build_facts(source, title, url, raw),
        "score": round(final_score, 4),
        "score_breakdown": {
            "freshness": round(freshness, 4),
            "heat": round(heat, 4),
            "reader_relevance": round(reader_relevance, 4),
            "explainability": round(explainability, 4),
            "shareability": round(shareability, 4),
            "compliance_risk": round(compliance_risk, 4),
        },
        "category": category,
        "raw": raw,
    }


def discover_topics(args: argparse.Namespace) -> int:
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    history_payload = load_history_payload(args.history_file)
    source_mode = "hybrid" if args.source_mode == "auto" else args.source_mode

    opencli_ready = False
    if source_mode in {"hybrid", "opencli"}:
        if shutil.which("opencli") is None:
            failures.append({"source": "opencli", "error": "opencli not found in PATH"})
        else:
            if args.skip_doctor:
                opencli_ready = True
            else:
                doctor = run_command(["opencli", "doctor"], timeout=20, check=False)
                opencli_ready = doctor.returncode == 0
                if not opencli_ready:
                    failures.append(
                        {
                            "source": "opencli-doctor",
                            "error": (doctor.stderr.strip() or doctor.stdout.strip() or "opencli doctor failed"),
                        }
                    )

        if source_mode == "opencli" and not opencli_ready:
            raise RuntimeError("opencli mode requested, but opencli is unavailable or unhealthy")

    if opencli_ready:
        sources = [
            ("weibo", ["weibo", "hot", "--limit", str(args.per_source)]),
            ("zhihu", ["zhihu", "hot", "--limit", str(args.per_source)]),
            ("bilibili", ["bilibili", "hot", "--limit", str(args.per_source)]),
        ]
        for source, command in sources:
            try:
                payload = run_opencli_json(command, timeout=args.timeout)
                for item in payload:
                    topic = normalize_topic(source, item, args.per_source)
                    results.append(topic)
            except Exception as exc:
                failures.append({"source": source, "error": str(exc)})

    if source_mode in {"hybrid", "direct"}:
        direct_payload = fetch_direct_hotspots(
            limit=max(args.limit * 8, args.per_source * 8, 30),
            timeout=min(args.timeout, 20),
        )
        for item in direct_payload["items"]:
            topic = normalize_topic(item["source"], item, max(args.limit, args.per_source))
            results.append(topic)
        failures.extend(direct_payload["failures"])

    kept = [
        topic
        for topic in results
        if args.allow_high_risk or topic["compliance_risk"] < args.max_risk
    ]
    kept = [topic for topic in kept if topic["reader_relevance"] >= args.min_reader_relevance]

    strong_topics = [topic for topic in kept if topic["reader_relevance"] >= max(args.min_reader_relevance, 0.48)]

    if len(strong_topics) < args.limit and opencli_ready:
        fallback_query = args.fallback_query or "中老年 健康 养生 银发 睡眠 饮食 走路 家庭 防骗"
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

    enriched_topics = [
        apply_topic_intelligence(
            topic=topic,
            history_payload=history_payload,
            window_days=args.history_window_days,
        )
        for topic in deduped.values()
    ]
    topics = sorted(enriched_topics, key=lambda item: item["score"], reverse=True)[: args.limit]
    output = {
        "generated_at": now_iso(),
        "lane": "中老年健康与银发生活",
        "source_mode": source_mode,
        "filters": {
            "allow_high_risk": args.allow_high_risk,
            "max_risk": args.max_risk,
            "min_reader_relevance": args.min_reader_relevance,
        },
        "history": {
            "path": args.history_file or None,
            "window_days": args.history_window_days,
            "article_count": len(history_payload.get("articles", [])),
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
        f"从「{title}」说起，很多家庭都容易忽视这件事",
        f"看到「{title}」，更该提醒家里人的是这几个细节",
        f"别只盯着「{title}」，真正要紧的是后面这一步",
    ]


def suggest_keywords_for_topic(topic: dict[str, Any]) -> list[str]:
    existing = topic.get("topic_keywords") or topic.get("seo", {}).get("keywords")
    if isinstance(existing, list) and len([item for item in existing if str(item).strip()]) >= 3:
        return [str(item).strip() for item in existing if str(item).strip()][:5]

    title = str(topic.get("title", "")).strip()
    category = str(topic.get("category", "")).strip()
    combined = f"{title} {category}"
    keywords = [title]
    if keyword_hits(combined, WELLNESS_KEYWORDS) > 0:
        keywords.extend(["中老年", "健康", "日常提醒", "家庭"])
    elif keyword_hits(combined, FAMILY_KEYWORDS) > 0:
        keywords.extend(["家庭", "父母", "提醒", "生活"])
    else:
        keywords.extend(["中老年", "生活", "提醒", "公共话题"])
    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        if keyword and keyword not in seen:
            deduped.append(keyword)
            seen.add(keyword)
    return deduped[:5]


def scaffold_article(topic: dict[str, Any], benchmark_url: str | None) -> dict[str, Any]:
    summary_hint = f"用 2 到 3 句概括「{topic['title']}」的事实背景、核心判断和现实意义。语气克制，避免热搜体表达。"
    outline = [
        {"heading": section, "goal": goal}
        for section, goal in zip(
            REQUIRED_SECTIONS,
            [
                "用事件或场景切入，但不要写成情绪复述。",
                "先点明最需要看这篇的人是谁。",
                "列出可验证事实，别混进空泛结论。",
                "把误区、案例、或容易踩坑的地方讲清楚。",
                "给出普通家庭今天就能执行的做法。",
                "收束成边界清晰的提醒，不要喊口号。",
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
        "cover_prompt": f"给微信公众号封面图，主题是：{topic['title']}。风格干净、可信、生活化、中文排版，适合中老年和家庭读者，不要廉价保健品海报感。",
        "image_prompts": [
            f"为文章配一张信息图或提醒图，主题：{topic['title']}，风格克制、好懂、适合公众号正文，不要装饰性空图。",
        ],
        "keywords": suggest_keywords_for_topic(topic),
        "seo_snapshot": topic.get("seo", {}),
        "history_snapshot": topic.get("history", {}),
        "fact_checklist": copy.deepcopy(topic["facts"]),
        "benchmark_article_url": benchmark_url,
        "style_notes": [
            "语气稳，像把一件事认真讲给家里人听。",
            "删空话，但也别写成硬邦邦的报告。",
            "先交代具体场景、人群或事件，再展开判断。",
            "少讲大词，多讲普通人今天能做什么。",
            "不要写成热点复述稿，也不要写成吓人的伪养生文。",
            "健康内容别写成诊断、治疗方案、神药推荐。",
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
    if any(word in text for word in WELLNESS_KEYWORDS):
        return "health-explainer"
    if any(word in text for word in ["流程", "步骤", "清单", "怎么做", "提醒"]):
        return "checklist"
    if any(word in text for word in FAMILY_KEYWORDS | {"被骗", "防骗", "骗局", "社区"}):
        return "family-guide"
    return "lifestyle-explainer"


def choose_cover_style(package: dict[str, Any]) -> dict[str, str]:
    title = str(package.get("titles", [""])[0])
    text = f"{title}\n{package.get('summary', '')}"
    style = "editorial-infographic"
    cover_type = "conceptual"
    if any(word in text for word in WELLNESS_KEYWORDS):
        style = "magazine"
    if any(word in text for word in ["提醒", "误区", "清单", "怎么做"]):
        style = "editorial-infographic"
    return {
        "type": cover_type,
        "style": style,
        "aspect": "16:9",
    }


def build_illustration_entries(package: dict[str, Any]) -> list[dict[str, str]]:
    entries = [
        {
            "section": "关键事实",
            "type": "comparison",
            "purpose": "把最关键的事实和边界条件讲清楚。",
            "visual_content": "左右对比图：左侧是常见误区或错误说法，右侧是更稳妥的事实理解或提醒。",
            "filename": "01-comparison-myth-vs-fact.png",
        },
        {
            "section": "常见误区或案例",
            "type": "framework",
            "purpose": "把读者最容易踩坑的场景画出来。",
            "visual_content": "一个场景化示意图：展示典型生活场景，并标出最容易忽视的风险点、误区、或判断边界。",
            "filename": "02-framework-scene-risk-map.png",
        },
        {
            "section": "日常怎么做",
            "type": "flowchart",
            "purpose": "把普通人今天就能执行的动作整理清楚。",
            "visual_content": "流程图：先观察信号 -> 分清误区 -> 做基础调整 -> 记录变化 -> 必要时求助专业人士。",
            "filename": "03-flowchart-daily-checklist.png",
        },
    ]
    lane = detect_visual_lane(package)
    if lane == "health-explainer":
        entries[1]["type"] = "comparison"
        entries[1]["visual_content"] = "对照图：左侧是常见但不稳妥的做法，右侧是更保守、更靠谱的日常处理方式。"
        entries[2]["visual_content"] = "决策树：出现哪些信号先做基础调整，出现哪些信号不要拖，应尽快咨询专业人士。"
    elif lane == "family-guide":
        entries[1]["visual_content"] = "家庭场景图：家里最容易忽视的沟通、消费、或防骗风险点分布。"
        entries[2]["visual_content"] = "提醒清单流程：先核实 -> 再沟通 -> 留证据 -> 找可信渠道确认 -> 必要时求助。"
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

        Create an explanatory article illustration for a Chinese WeChat article aimed at middle-aged and older readers and their families.

        SECTION
        {entry['section']}

        PURPOSE
        {entry['purpose']}

        VISUAL CONTENT
        {entry['visual_content']}

        ARTICLE CONTEXT
        {summary}

        STYLE
        Clean, editorial, information-first. Avoid decorative filler, miracle-cure ad vibes, and cheap stock-poster aesthetics.

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
    preset = "process-flow" if lane == "checklist" else "editorial-infographic"
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
        - 先让人一眼看懂是“提醒类”“家庭类”还是“健康类”
        - 少做戏剧化冲突，多做结构化表达
        - 看起来可信、克制、好懂，不要廉价保健品海报风

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


def record_history(args: argparse.Namespace) -> int:
    package = load_json(args.package)
    history_payload = load_history_payload(args.history_file)
    topic = package.get("topic", {}) if isinstance(package, dict) else {}

    titles = package.get("titles", []) if isinstance(package, dict) else []
    default_title = str(titles[0]).strip() if isinstance(titles, list) and titles else str(topic.get("title", "")).strip()
    title = args.title or default_title
    keywords = package.get("topic_keywords") or package.get("keywords") or topic.get("topic_keywords") or topic.get("seo", {}).get("keywords") or []
    normalized_keywords = [str(item).strip() for item in keywords if str(item).strip()][:6]

    entry = {
        "title": title,
        "published_at": args.published_at or now_iso(),
        "topic_source": args.topic_source or ("benchmark" if args.benchmark_url else "skill"),
        "topic_keywords": normalized_keywords,
        "topic_url": topic.get("url") or args.topic_url or "",
        "word_count": package.get("word_count"),
        "media_id": args.media_id or "",
        "summary": package.get("summary", ""),
        "framework": args.framework or topic.get("category") or "",
        "stats": None,
    }
    if args.notes:
        entry["notes"] = args.notes

    updated = append_history_entry(history_payload, entry)
    save_history_payload(args.history_file, updated)

    result = {
        "history_file": args.history_file,
        "entry": entry,
        "article_count": len(updated.get("articles", [])),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def sync_history_stats(args: argparse.Namespace) -> int:
    credentials = None
    if args.app_id and args.app_secret:
        credentials = {"app_id": args.app_id, "app_secret": args.app_secret, "source": "cli"}
    else:
        credentials = resolve_wechat_credentials()
    if not credentials:
        raise SystemExit("missing WeChat credentials; set WECHAT_APP_ID and WECHAT_APP_SECRET or pass --app-id/--app-secret")

    history_payload = load_history_payload(args.history_file)
    access_token = get_wechat_access_token(credentials["app_id"], credentials["app_secret"], timeout=args.timeout)
    now_value = dt.datetime.now().astimezone()
    stats_list: list[dict[str, Any]] = []

    for offset in range(args.days):
        target_date = (now_value - dt.timedelta(days=offset + 1)).date().isoformat()
        daily_stats = fetch_wechat_article_summary(access_token, target_date, target_date, timeout=args.timeout)
        stats_list.extend(daily_stats)

    updated = merge_stats_into_history(history_payload, stats_list)
    save_history_payload(args.history_file, updated)

    result = {
        "history_file": args.history_file,
        "credential_source": credentials["source"],
        "days": args.days,
        "stats_count": len(stats_list),
        "articles": updated.get("articles", []),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
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
    discover.add_argument("--source-mode", choices=("auto", "hybrid", "opencli", "direct"), default="hybrid")
    discover.add_argument("--history-file", default="")
    discover.add_argument("--history-window-days", type=int, default=7)
    discover.add_argument("--fallback-query", default="")
    discover.add_argument("--allow-high-risk", action="store_true")
    discover.add_argument("--max-risk", type=float, default=0.45)
    discover.add_argument("--min-reader-relevance", "--min-ai-relevance", dest="min_reader_relevance", type=float, default=0.38)
    discover.add_argument("--skip-doctor", action="store_true")
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

    history = subparsers.add_parser("record-history", help="Append or update article history after draft creation or publish")
    history.add_argument("--package", required=True, help="Path to the packaged article JSON")
    history.add_argument("--history-file", required=True, help="Path to the history JSON file")
    history.add_argument("--media-id", default="")
    history.add_argument("--published-at", default="")
    history.add_argument("--title", default="")
    history.add_argument("--topic-source", default="")
    history.add_argument("--topic-url", default="")
    history.add_argument("--framework", default="")
    history.add_argument("--benchmark-url", default="")
    history.add_argument("--notes", default="")
    history.set_defaults(handler=record_history)

    sync_stats = subparsers.add_parser("sync-history-stats", help="Pull WeChat article stats into the history file")
    sync_stats.add_argument("--history-file", required=True, help="Path to the history JSON file")
    sync_stats.add_argument("--days", type=int, default=3)
    sync_stats.add_argument("--app-id", default="")
    sync_stats.add_argument("--app-secret", default="")
    sync_stats.add_argument("--timeout", type=int, default=20)
    sync_stats.set_defaults(handler=sync_history_stats)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
