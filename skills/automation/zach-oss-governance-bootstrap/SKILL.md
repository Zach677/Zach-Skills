---
name: zach-oss-governance-bootstrap
description: >
  Use when bootstrapping a GitHub open-source repo with Ghostty-style
  contribution docs, discussion-first triage, Vouch contributor trust
  automation, and main-branch ruleset protection.
metadata:
  author: zach
  version: "0.1.0"
---

# zach-oss-governance-bootstrap

Bootstrap a GitHub repository into Zach's preferred Ghostty-style
open-source governance shape: human-accountable contribution docs,
discussion-first issue intake, first-time contributor vouching, GitHub
App-backed automation, and a protected default branch that still allows
the vouch app and Zach to bypass rules when appropriate.

## When to use

Use this for a public or soon-to-be-public GitHub repository where Zach
wants a durable open-source contribution workflow, not just issue
templates. This is especially useful for template projects or repos that
may receive AI-generated low-quality contributions.

Do not use this for private throwaway repos, repos without GitHub
Discussions enabled, or projects where all external contribution should
remain disabled.

## Inputs

- Repository owner and name, for example `Zach677/Modern.UIKit`.
- Project display name.
- Default branch name, usually `main`.
- Whether translation guidance applies. Template projects usually keep it
  commented out.
- Whether a CODEOWNERS/subsystem maintainer model exists. If not, do not
  require Code Owner review.
- GitHub App slug/name for Vouch, for example `modern-vouch`.
- Zach's GitHub login for ruleset bypass, usually `Zach677`.
- Runner label for GitHub Actions workflows, usually `ubuntu-latest`
  unless the repo uses custom runners.
- Action refs for `actions/create-github-app-token`, `actions/checkout`,
  and `mitchellh/vouch/action`. Prefer pinned tags or SHAs.

## Files provided

- `scripts/create-main-branch-ruleset.sh` creates or updates the main
  branch ruleset with Vouch app and Zach bypass.
- `references/vouch-app-permissions.md` lists the private GitHub App
  permissions and secret names.
- `references/vouch-app-manifest.template.json` is a manifest starting
  point for browser-based GitHub App creation.
- `templates/docs/` contains reusable `CONTRIBUTING.md`,
  `AI_POLICY.md`, `HACKING.md`, and `AGENTS.md` templates.
- `templates/github/` contains reusable Vouch discussion, vouch list,
  message, and workflow templates for `.github/`.

## Workflow

```text
[1] Inspect repo and benchmark fit
[2] Add Ghostty-style contribution files
[3] Add Vouch repository files and workflows
[4] Configure GitHub repo settings
[5] Create and install the Vouch GitHub App
[6] Create the default-branch ruleset
[7] Test with a second GitHub account
```

## [1] Inspect repo and benchmark fit

Confirm the remote repo with `gh repo view --json nameWithOwner,url` and
fetch the current default branch. If the project already has contribution
docs, diff them first and preserve project-specific rules that are still
valid.

If using Ghostty as the benchmark, refresh the local reference checkout
before comparing:

```bash
git -C /Users/star/Developer/other-repo/ghostty fetch origin main
git -C /Users/star/Developer/other-repo/ghostty rev-parse HEAD origin/main
```

## [2] Add Ghostty-style contribution files

Copy and adapt the provided templates instead of recreating these files from
scratch:

- `templates/docs/CONTRIBUTING.md` -> `CONTRIBUTING.md`: critical rule,
  AI usage, first-time contributor
  Vouch Request, denouncement system, quick guide, discussion-first
  issue pattern, PRs implement accepted issues.
- `templates/docs/AI_POLICY.md` -> `AI_POLICY.md`: keep the
  human-accountable AI policy shape unless Zach explicitly asks for a
  stricter or looser policy.
- `templates/docs/HACKING.md` -> `HACKING.md`: keep as a skeletal
  placeholder when project-specific development instructions are not ready.
- `templates/docs/AGENTS.md` -> `AGENTS.md`: include the contribution
  workflow section that keeps `CONTRIBUTING.md`, `AI_POLICY.md`,
  `HACKING.md`, and `.github/` aligned.

Replace placeholders such as `{{PROJECT_NAME}}`, `{{OWNER}}`, `{{REPO}}`,
`{{DEFAULT_BRANCH}}`, and discussion category slugs before committing.

For template repos, comment out translation-specific guidance rather
than deleting the idea entirely.

## [3] Add Vouch repository files and workflows

Copy and adapt the provided Vouch templates:

- `templates/github/DISCUSSION_TEMPLATE/vouch-request.yml` ->
  `.github/DISCUSSION_TEMPLATE/vouch-request.yml`
- `templates/github/VOUCHED.td` -> `.github/VOUCHED.td`
- `templates/github/issue-unvouched-message` ->
  `.github/issue-unvouched-message`
- `templates/github/workflows/vouch-check-issue.yml` ->
  `.github/workflows/vouch-check-issue.yml`
- `templates/github/workflows/vouch-check-pr.yml` ->
  `.github/workflows/vouch-check-pr.yml`
- `templates/github/workflows/vouch-manage-by-discussion.yml` ->
  `.github/workflows/vouch-manage-by-discussion.yml`
- `templates/github/workflows/vouch-manage-by-issue.yml` ->
  `.github/workflows/vouch-manage-by-issue.yml`

Use `actions/create-github-app-token`, not default `GITHUB_TOKEN`, for
all Vouch actions. Keep repo Actions default workflow permissions
read-only; write access comes from the app installation token.

Replace placeholders such as `{{RUNNER_LABEL}}`,
`{{CREATE_GITHUB_APP_TOKEN_REF}}`, `{{CHECKOUT_ACTION_REF}}`, and
`{{VOUCH_ACTION_REF}}`. Do not leave template placeholders in the target
repo.

Do not add `vouch-sync-codeowners.yml` unless the repo actually has a
CODEOWNERS/subsystem maintainer model. If it is added later, document it as
optional and explain which CODEOWNERS entries it manages.

## [4] Configure GitHub repo settings

Use `gh` for stable settings:

```bash
gh label create "contributor friendly" \
  --repo OWNER/REPO \
  --color 0E8A16 \
  --description "Extra friendly to new contributors" \
  --force
```

Create Discussion categories in GitHub UI if the API is awkward. The
`Vouch Request` category should use **Question / Answer** format so the
maintainer approval thread has an answerable shape.

Recommended category slugs used by the contribution guide:

- `vouch-request`
- `issue-triage`
- `feature-requests-ideas`
- `q-a`

## [5] Create and install the Vouch GitHub App

Vouch does not require a public hosted GitHub App. Create a private app
for Zach or the owning org. Use the permissions in
`references/vouch-app-permissions.md`, install it only on the target
repo, then write:

```bash
gh secret set VOUCH_APP_ID --repo OWNER/REPO
gh secret set VOUCH_APP_PRIVATE_KEY --repo OWNER/REPO
```

Keep the private key out of the repo and avoid printing it in terminal
logs. If using GitHub App manifest creation, start from
`references/vouch-app-manifest.template.json` and replace placeholders.

## [6] Create the default-branch ruleset

Use the helper after the app is installed and secrets are set:

```bash
bash scripts/create-main-branch-ruleset.sh OWNER REPO VOUCH_APP_ID Zach677
```

The helper configures Zach's Ghostty-inspired default:

- active ruleset named `Main Branch`
- target `~DEFAULT_BRANCH`
- block deletion
- block non-fast-forward pushes
- require pull requests
- require 1 approval
- require last-push approval
- do not require Code Owner review
- do not require status checks yet
- bypass Vouch GitHub App
- bypass Zach

Only add required checks after the repo has stable CI checks with names
that will not churn.

## [7] Test with a second GitHub account

Run tests in this order:

1. Open an issue as the second account. It should be commented on,
   closed, and locked by the Vouch app.
2. Open a PR as the second account before vouching. It should be closed.
3. Open a `Vouch Request` discussion as the second account.
4. Comment `!vouch` as Zach. The Vouch app should update
   `.github/VOUCHED.td`, open a PR, and merge it immediately.
5. Open a second PR as the vouched account. It should remain open.

Do not test `!denounce` with an account Zach wants to keep using.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Creating branch protection before pushing workflow files | Push or merge the governance commit first, then create the ruleset. |
| Using default `GITHUB_TOKEN` for Vouch management | Use a private GitHub App token from `actions/create-github-app-token`. |
| Turning repo workflow permissions to write | Keep default workflow permissions read-only; the app token owns writes. |
| Assuming Ghostty's CODEOWNERS setup applies everywhere | Skip Code Owner review unless the repo has a real CODEOWNERS model. |
| Adding `vouch-sync-codeowners.yml` without CODEOWNERS | Do not add the sync workflow until CODEOWNERS has project value. |
| Forgetting the Vouch app bypass | `merge-immediately: true` can fail under rulesets unless the app bypasses. |
| Adding Zach only through admin assumptions | Add Zach explicitly as a `User` bypass actor when requested. |
| Querying `/repos/<repo>/installation` with a normal `gh` token | That endpoint can return JWT errors; verify installation through workflow behavior or app settings. |
| Choosing Open-ended Discussion for Vouch Request | Use Question / Answer. It matches request approval better. |
| Treating repo-local skills as installed runtime skills | Verify runtime symlinks separately if the skill must be immediately discoverable. |

## Rules

- Preserve Ghostty wording where Zach explicitly wants Ghostty shape.
- Change project names, links, category slugs, and non-applicable
  sections deliberately; do not invent extra process.
- Prefer GitHub Rulesets over legacy branch protection for new repos.
- Do not hardcode private keys, app private material, or one-off tokens.
- Keep docs, workflows, labels, Discussion categories, app secrets, and
  ruleset settings in sync before calling the setup complete.

## Verification

- [ ] `gh repo view --json nameWithOwner,url` matches the target repo.
- [ ] `.github` YAML parses.
- [ ] `CONTRIBUTING.md`, `AI_POLICY.md`, `HACKING.md`, and `AGENTS.md`
      agree on the contribution flow.
- [ ] No `{{PLACEHOLDER}}` values remain in copied templates.
- [ ] `contributor friendly` label exists.
- [ ] `Vouch Request` Discussion category exists and is answerable.
- [ ] `VOUCH_APP_ID` and `VOUCH_APP_PRIVATE_KEY` secrets exist.
- [ ] Vouch GitHub App is installed on the target repo.
- [ ] Default branch is protected by a `Main Branch` ruleset.
- [ ] Ruleset bypass actors include the Vouch app and Zach when desired.
- [ ] No required status checks are configured until stable CI exists.
- [ ] Second-account issue, PR, vouch, and vouched PR tests match
      expected behavior.
