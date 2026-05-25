import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publisher_ops.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("publisher_ops", SCRIPT_PATH)
publisher_ops = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(publisher_ops)


def render_article(markdown: str) -> tuple[str, dict]:
    with tempfile.TemporaryDirectory() as tmpdir:
        article = Path(tmpdir) / "article.md"
        output = Path(tmpdir) / "article.wechat.html"
        article.write_text(markdown, encoding="utf-8")
        payload = publisher_ops.render_article_to_path(article, output)
        return output.read_text(encoding="utf-8"), payload


class WechatRendererTests(unittest.TestCase):
    def test_render_article_uses_baoyu_and_removes_matching_leading_h1(self) -> None:
        html, payload = render_article(
            """---
title: 测试标题
summary: 摘要
coverImage: /tmp/cover.png
author: zachaics
---
# 测试标题

第一段正文。

## 第一节

**重要提醒。**
"""
        )

        self.assertEqual(payload["renderer"], "baoyu-md")
        self.assertEqual(payload["title"], "测试标题")
        self.assertNotIn("<h1", html)
        self.assertIn("第一节", html)
        self.assertIn("重要提醒", html)

    def test_render_article_preserves_first_h2_when_body_has_no_h1(self) -> None:
        html, _payload = render_article(
            """---
title: 无 H1 测试
summary: 摘要
coverImage: /tmp/cover.png
author: zachaics
---
开头段落。

## 不能被误删的小标题

正文。
"""
        )

        self.assertIn("不能被误删的小标题", html)

    def test_reference_section_links_do_not_create_duplicate_bottom_citations(self) -> None:
        html, payload = render_article(
            """---
title: 参考测试
summary: 摘要
coverImage: /tmp/cover.png
author: zachaics
---
正文里没有外链。

## 参考资料

- [官方来源](https://example.com/source)
"""
        )

        self.assertEqual(payload["citations"], [])
        self.assertIn("https://example.com/source", html)
        self.assertNotIn("<sup", html)

    def test_inline_links_still_become_bottom_sources(self) -> None:
        html, payload = render_article(
            """---
title: 外链测试
summary: 摘要
coverImage: /tmp/cover.png
author: zachaics
---
正文引用[官方提醒](https://example.com/notice)。
"""
        )

        self.assertEqual(payload["citations"], [{"label": "官方提醒", "url": "https://example.com/notice"}])
        self.assertIn("<sup", html)
        self.assertIn("资料来源", html)
        self.assertIn("https://example.com/notice", html)


if __name__ == "__main__":
    unittest.main()
