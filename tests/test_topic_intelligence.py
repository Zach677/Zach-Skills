from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "wechat-hot-writer" / "scripts"
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


if __name__ == "__main__":
    unittest.main()
