# Article Writing

Write in Simplified Chinese for middle-aged and older readers and their family
caregivers. Prefer useful, low-risk, easy-to-forward articles.

The target repo enforces a deterministic anti-AI style lint
(`scripts/daily_wechat_publisher.py style-lint`), and `publish-issue` blocks on
lint failures. Write to pass it on the first try.

## Banned Patterns (lint-enforced)

Never use these in the title, summary, or body:

- 「不是……而是……」对比句式
- 「换句话说」「值得注意的是」「需要指出的是」「有一点很重要」
- 「综上所述」「整体而言」「由此可见」
- 段落以「这说明」「可以看出」开头
- 「首先……其次……」排比骨架
- 第一人称亲历叙事（「我妈」「我爸」「我同事」等）。账号是编辑号，
  作者没有这些经历，写出来等同于造假。用公共场景替代：
  「最近不少家庭群里都出现过这样的链接」。

Use sparingly (lint warns): 「也就是说」、句首的「从而」「进而」。

## Repetition Limits (lint-enforced)

- Section headings must not repeat any heading used in the last 14 days,
  including today's sibling articles.
- The 「……上了热搜/热榜」 and 「这两天……」 openings fail the lint once they
  were already used twice in the last 7 days. Rotate opening moves daily.
- The 「今天就……」 closing fails the lint if any article in the last 7 days
  already used it.
- The first sentence must not share its shape with any recent article.

Before writing, read the recent openings, headings, and closings from the
exported history and treat them as an exclusion list. After writing, run the
lint locally and rewrite every `fail` finding.

## Good Shapes

- one concrete reader concern
- practical daily action
- official or credible source backing
- short paragraphs
- section titles that say something specific to this topic, not category labels
- real Markdown lists only where the reader will actually check items off
- one or two standalone bold reminder lines at most
- an ending that leaves one concrete action, phrased differently each day

Vary the skeleton between articles and between days. Some topics want five
sections and a checklist; others read better as one continuous argument with a
single list, or two long sections. Three articles in one issue must not share
one skeleton.

## Self-check Before Publishing

- The opening is concrete, not a generic "recently the weather is changing"
  line, and uses a move not seen in recent history.
- The article avoids miracle cures, diagnosis language, fake urgency, and
  exaggerated claims.
- Health content is general information and says when to seek professional help.
- Service or policy content says who it applies to, when, where to verify, and
  what not to misunderstand.
- Rumor/fake-notice content says what the original claim is, what the official
  source says, and what not to forward.
- The main point can be retold in one sentence in a family group chat.
- The final action section is scan-friendly, and the closing move differs from
  the last 7 days.
- `## 参考资料` is present when current facts are sourced, and links are written
  as Markdown links so the renderer can make a clean source section.
- `style-lint` reports no `fail` findings for all three articles.

## WeWrite Ideas To Reuse

- use a clear framework, but do not expose the framework labels
- add enough specific detail that each section is actionable
- include two or three natural "editorial anchors" where Zach can later add a
  personal line if desired
- vary title shapes instead of repeating one template
