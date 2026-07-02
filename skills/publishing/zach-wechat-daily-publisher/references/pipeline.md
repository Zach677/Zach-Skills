# Pipeline

This skill is an agent-led publishing workflow, not a fully scripted writer.

## Ownership Split

Agent-owned:

- choose the topic
- research and verify facts
- write and revise the article
- decide title, summary, and cover wording
- create the visual plan: cover source concept, prompt artifact, article
  illustration outline, prompt artifacts, backend choice, raster outputs, and
  manifest
- judge whether the article is safe to publish

Script-owned:

- daily publish/blocker guard
- history export
- periodic trend snapshot capture
- trend-aware topic candidate scoring
- article frontmatter validation
- cover composition, square-preview generation, and cover QA artifacts
- TypeScript visual artifact QA before publish
- Markdown to WeChat-ready HTML rendering
- WeChat API calls
- success/blocker logs

## Required End States

Each run ends in exactly one of:

- API draft created and `publish_logs/YYYY-MM-DD.json` written
- local draft saved and `publish_logs/YYYY-MM-DD-blocker.json` written

Never silently fail and never publish twice on the same date.

## No Browser Branch

There is no browser fallback. If the API path fails, log it and stop.
