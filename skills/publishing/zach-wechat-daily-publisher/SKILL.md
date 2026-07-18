---
name: zach-wechat-daily-publisher
description: "Use when Zach asks to run, inspect, or recover the daily WeChat Official Account workflow. Route the work into the target Wechat-post repository, whose AGENTS.md and repo-local Bun scripts own the publishing contract, rendering, API behavior, and logs."
metadata:
  author: zach
  version: "0.1.0"
---

# Zach WeChat Daily Publisher

Route the request into the target publishing repository. This skill is only an
entry point; it provides no runtime scripts, templates, or duplicate workflow
contract.

## Outcome Contract

- Read the target repo's `AGENTS.md` and `README.md` before acting.
- Use its repo-local command surface and dependencies.
- End a daily run with the repo-defined success log or canonical blocker log.
- Leave an existing same-day terminal state untouched unless Zach explicitly
  requests a supported recovery.

## Entry

1. Resolve the target `Wechat-post` repository from Zach's message or the
   current workspace. Ask for its path only when it cannot be identified.
2. Read the repository instructions and treat them as the source of truth for
   commands, article schema, rendering, visual QA, API calls, and handoff.
3. Check the repo's daily status before research, writing, generation, or API
   work.
4. Follow the repo-defined daily or recovery path without recreating its
   workflow in this skill.

## Stable Boundaries

- Publish through the WeChat API only. Do not use browser, QR-login, captcha,
  editor, Chrome, CDP, OpenCLI, or Playwright automation.
- Produce at most one daily issue containing exactly the repo-defined three
  article roles.
- Verify current medical, legal, financial, policy, weather, and consumer
  claims with credible public sources and use conservative wording.
- Attempt `draft/add` once. Treat timeout or ambiguous response as a possible
  success, write the canonical blocker, and require manual reconciliation.
- Keep credentials and local runtime state out of Git.

## Handoff

Report the repo's terminal status, log path, created artifacts, and any manual
reconciliation required. Run the repository's verification command after
changing its scripts or contract.
