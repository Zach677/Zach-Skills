# Agent Development Guide

A file for guiding coding agents working on {{PROJECT_NAME}}.

## Commands

- **Setup:** `{{SETUP_COMMAND}}`
- **Build:** `{{BUILD_COMMAND}}`
- **Test:** `{{TEST_COMMAND}}`
- **Format:** `{{FORMAT_COMMAND}}`

## Contribution Workflow

- Keep `CONTRIBUTING.md`, `AI_POLICY.md`, `HACKING.md`, `AGENTS.md`, and
  `.github/` automation aligned when changing contribution policy.
- Preserve the discussion-first intake model: bugs and feature ideas start in
  GitHub Discussions, and issues should represent accepted actionable work.
- Preserve the first-time contributor vouch flow. New contributors should use
  the Vouch Request discussion category before opening pull requests.
- Pull requests should implement accepted issues. Do not use pull requests as
  the place to design broad feature changes.
- AI-assisted work must follow `AI_POLICY.md`. Contributors must disclose AI
  usage and understand the submitted work.
- Vouch automation should use the Vouch GitHub App token, not the default
  `GITHUB_TOKEN`, for write operations.
- Repository default workflow permissions should stay read-only; workflows
  that need writes should receive them through the GitHub App token.

## Project Notes

- Default branch: `{{DEFAULT_BRANCH}}`
- Repository: `{{OWNER}}/{{REPO}}`
- Vouch app slug: `{{VOUCH_APP_SLUG}}`
