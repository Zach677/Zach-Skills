from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "wechat-hot-writer" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import topic_intelligence  # type: ignore  # noqa: E402
import wechat_hot_writer  # type: ignore  # noqa: E402


class BuildTopicSeoTests(unittest.TestCase):
    def test_build_topic_seo_aggregates_scores_and_related_keywords(self) -> None:
        def fake_fetcher(keyword: str) -> dict[str, list[str]]:
            data = {
                "花粉过敏": {
                    "baidu": ["花粉过敏有哪些症状", "花粉过敏怎么缓解"],
                    "so360": ["花粉过敏怎么治疗"],
                },
                "中老年": {
                    "baidu": ["中老年花粉过敏怎么办"],
                    "so360": [],
                },
            }
            return data[keyword]

        seo = topic_intelligence.build_topic_seo(
            title="花粉过敏高发季，家里老人总打喷嚏怎么办",
            category="健康",
            fetcher=fake_fetcher,
        )

        self.assertGreater(seo["score"], 0.0)
        self.assertIn("花粉过敏", seo["keywords"])
        self.assertIn("花粉过敏有哪些症状", seo["related_keywords"])

    def test_build_topic_seo_filters_unsafe_related_keywords(self) -> None:
        def fake_fetcher(keyword: str) -> dict[str, list[str]]:
            if keyword == "花粉过敏":
                return {
                    "baidu": ["花粉过敏有哪些症状"],
                    "so360": ["花粉过敏怎么缓解"],
                }
            return {
                "baidu": ["家庭luan伦母子视频"],
                "so360": ["老人玩小处雌女视频在线看"],
            }

        seo = topic_intelligence.build_topic_seo(
            title="花粉过敏高发季，家里老人总打喷嚏怎么办",
            category="健康",
            fetcher=fake_fetcher,
        )

        self.assertNotIn("家庭luan伦母子视频", seo["related_keywords"])
        self.assertNotIn("老人玩小处雌女视频在线看", seo["related_keywords"])


class HistoryPenaltyTests(unittest.TestCase):
    def test_build_history_penalty_flags_recent_overlap(self) -> None:
        history = {
            "articles": [
                {
                    "title": "春天花粉过敏别硬扛",
                    "published_at": "2026-03-25T08:00:00+08:00",
                    "topic_keywords": ["花粉过敏", "春天"],
                }
            ]
        }

        penalty = topic_intelligence.build_history_penalty(
            title="花粉过敏高发季，家里老人总打喷嚏怎么办",
            category="健康",
            history_payload=history,
            window_days=7,
            now=dt.datetime(2026, 3, 27, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=8))),
        )

        self.assertGreater(penalty["penalty"], 0.0)
        self.assertIn("花粉过敏", penalty["overlap_keywords"])


class HistoryUpdateTests(unittest.TestCase):
    def test_append_history_entry_keeps_articles_array(self) -> None:
        payload = {"articles": []}

        updated = topic_intelligence.append_history_entry(
            history_payload=payload,
            entry={
                "title": "春天睡得浅，别只盯着睡多久",
                "published_at": "2026-03-27T07:00:00+08:00",
                "topic_keywords": ["睡眠", "春天"],
                "media_id": "abc123",
            },
        )

        self.assertEqual(len(updated["articles"]), 1)
        self.assertEqual(updated["articles"][0]["media_id"], "abc123")

    def test_merge_stats_updates_matching_article_by_title(self) -> None:
        payload = {
            "articles": [
                {
                    "title": "春天睡得浅，别只盯着睡多久",
                    "published_at": "2026-03-27T07:00:00+08:00",
                    "topic_keywords": ["睡眠", "春天"],
                    "media_id": "abc123",
                    "stats": None,
                }
            ]
        }

        updated = topic_intelligence.merge_stats_into_history(
            history_payload=payload,
            stats_list=[
                {
                    "title": "春天睡得浅，别只盯着睡多久",
                    "int_page_read_count": 1200,
                    "share_count": 36,
                    "old_like_count": 10,
                    "like_count": 5,
                    "target_user": 3000,
                }
            ],
        )

        article = updated["articles"][0]
        self.assertEqual(article["stats"]["read_count"], 1200)
        self.assertEqual(article["stats"]["share_count"], 36)
        self.assertEqual(article["stats"]["like_count"], 15)
        self.assertEqual(article["stats"]["read_rate"], 40.0)


class TopicEnrichmentTests(unittest.TestCase):
    def test_apply_topic_intelligence_adds_seo_and_history_adjustments(self) -> None:
        topic = {
            "title": "花粉过敏高发季，家里老人总打喷嚏怎么办",
            "category": "健康",
            "score": 0.6,
            "score_breakdown": {
                "freshness": 0.9,
                "heat": 0.7,
                "reader_relevance": 0.8,
                "explainability": 0.7,
                "shareability": 0.75,
                "compliance_risk": 0.1,
            },
        }
        history = {
            "articles": [
                {
                    "title": "春天花粉过敏别硬扛",
                    "published_at": "2026-03-25T08:00:00+08:00",
                    "topic_keywords": ["花粉过敏", "春天"],
                }
            ]
        }

        enriched = topic_intelligence.apply_topic_intelligence(
            topic=topic,
            history_payload=history,
            window_days=7,
            seo_fetcher=lambda keyword: {
                "baidu": ["花粉过敏有哪些症状"] if "花粉过敏" in keyword else [],
                "so360": ["花粉过敏怎么缓解"] if "花粉过敏" in keyword else [],
            },
            now=dt.datetime(2026, 3, 27, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=8))),
        )

        self.assertIn("seo", enriched)
        self.assertIn("history", enriched)
        self.assertLess(enriched["score"], 0.6)
        self.assertGreater(enriched["score_breakdown"]["seo"], 0.0)
        self.assertGreater(enriched["score_breakdown"]["history_penalty"], 0.0)


class FreshnessParsingTests(unittest.TestCase):
    def test_normalize_freshness_accepts_iso_datetime(self) -> None:
        freshness = wechat_hot_writer.normalize_freshness(
            {"date": "2026-03-27T13:30:00+08:00"},
            limit=10,
        )

        self.assertEqual(freshness, 1.0)


class ExtendConfigTests(unittest.TestCase):
    def test_configured_extend_file_paths_follow_project_xdg_user_order(self) -> None:
        project_dir = Path("/tmp/project-root")
        xdg_dir = Path("/tmp/xdg-home")
        user_dir = Path("/tmp/user-home")

        with mock.patch.object(wechat_hot_writer.Path, "cwd", return_value=project_dir):
            with mock.patch.object(wechat_hot_writer.Path, "home", return_value=user_dir):
                with mock.patch.dict(wechat_hot_writer.os.environ, {"XDG_CONFIG_HOME": str(xdg_dir)}, clear=False):
                    paths = wechat_hot_writer.configured_extend_file_paths("wechat-hot-writer")

        self.assertEqual(
            paths,
            (
                project_dir / ".baoyu-skills" / "wechat-hot-writer" / "EXTEND.md",
                xdg_dir / "baoyu-skills" / "wechat-hot-writer" / "EXTEND.md",
                user_dir / ".baoyu-skills" / "wechat-hot-writer" / "EXTEND.md",
            ),
        )

    def test_parse_extend_file_supports_scalars_and_lists(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "EXTEND.md"
            path.write_text(
                "\n".join(
                    [
                        "# Preferences",
                        "",
                        "lane: 通用家庭与公共话题",
                        "fallback_query: 民生 家庭 健康 防骗",
                        "min_reader_relevance: 0.52",
                        "max_risk: 0.3",
                        "title_templates:",
                        "- 从「{title}」说起，真正值得注意的是这几点",
                        "- 看到「{title}」，更该关心的是背后的现实问题",
                        "style_notes:",
                        "- 先说人话，再说判断。",
                        "- 别写圈内黑话。",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = wechat_hot_writer.parse_extend_file(path)

        self.assertEqual(payload["lane"], "通用家庭与公共话题")
        self.assertEqual(payload["fallback_query"], "民生 家庭 健康 防骗")
        self.assertEqual(payload["min_reader_relevance"], 0.52)
        self.assertEqual(payload["max_risk"], 0.3)
        self.assertEqual(
            payload["title_templates"],
            [
                "从「{title}」说起，真正值得注意的是这几点",
                "看到「{title}」，更该关心的是背后的现实问题",
            ],
        )
        self.assertEqual(payload["style_notes"], ["先说人话，再说判断。", "别写圈内黑话。"])

    def test_load_extend_settings_prefers_project_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_path = root / "project" / ".baoyu-skills" / "wechat-hot-writer" / "EXTEND.md"
            xdg_path = root / "xdg" / "baoyu-skills" / "wechat-hot-writer" / "EXTEND.md"
            user_path = root / "home" / ".baoyu-skills" / "wechat-hot-writer" / "EXTEND.md"
            project_path.parent.mkdir(parents=True, exist_ok=True)
            xdg_path.parent.mkdir(parents=True, exist_ok=True)
            user_path.parent.mkdir(parents=True, exist_ok=True)
            project_path.write_text("lane: 项目配置\n", encoding="utf-8")
            xdg_path.write_text("lane: XDG 配置\n", encoding="utf-8")
            user_path.write_text("lane: 用户配置\n", encoding="utf-8")

            with mock.patch.object(wechat_hot_writer.Path, "cwd", return_value=root / "project"):
                with mock.patch.object(wechat_hot_writer.Path, "home", return_value=root / "home"):
                    with mock.patch.dict(wechat_hot_writer.os.environ, {"XDG_CONFIG_HOME": str(root / "xdg")}, clear=False):
                        payload = wechat_hot_writer.load_extend_settings("wechat-hot-writer")

        self.assertEqual(payload["lane"], "项目配置")

    def test_suggest_titles_uses_extend_templates_when_provided(self) -> None:
        topic = {"title": "旧手机回收又起风波"}
        preferences = {
            "title_templates": [
                "看到「{title}」，普通家庭最该先核对这件事",
                "别被「{title}」带偏，先把这一步看明白",
            ]
        }

        titles = wechat_hot_writer.suggest_titles(topic, preferences)

        self.assertEqual(
            titles,
            [
                "看到「旧手机回收又起风波」，普通家庭最该先核对这件事",
                "别被「旧手机回收又起风波」带偏，先把这一步看明白",
                "从「旧手机回收又起风波」说起，很多家庭都容易忽视这件事",
            ],
        )


if __name__ == "__main__":
    unittest.main()
