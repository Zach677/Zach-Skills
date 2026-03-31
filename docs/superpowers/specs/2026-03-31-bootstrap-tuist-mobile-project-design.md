# Bootstrap Tuist Mobile Project Design

**Date:** 2026-03-31

**Goal:** Create a reusable Codex skill that interviews the user, then scaffolds and initializes a new Tuist mobile project from a public template with the right local scripts, Codex actions, Tuist Cloud wiring, and cache setup.

**Why this exists:** The same Tuist bootstrap work now repeats across multiple repos:

- `mitori` for macOS-first local Tuist workflows
- `SubPanda` for iOS plus Mac Catalyst
- `Kigen` for pure iOS

That repeated work already includes the same categories of setup:

- `mise` task wiring
- Tuist binary cache and Xcode cache setup
- Codex local actions
- `.gitignore` hygiene for `.cache/` and `.xcodebuild/`
- `AGENTS.md` workflow guidance
- script entrypoints for run, build, test, cache warming, and preview sharing

Doing that by hand every time is wasteful and easy to get subtly wrong.

## Problem

The desired product needs to support multiple creation modes while staying explicit and safe:

- local-only creation
- local plus GitHub repo creation
- local plus GitHub plus Tuist Cloud and Xcode cache setup

It also needs to support multiple project shapes:

- pure iOS
- iOS plus Mac Catalyst

The flow must not silently downgrade, skip, or "helpfully" choose for the user when required capabilities are missing. Any meaningful action involving GitHub, Tuist Cloud, repo visibility, cache setup, or initial push must be user-confirmed.

Finally, the product must be open-source friendly. Template sources should be public and reusable by others, while the orchestration logic can live in `Zach-Skills`.

## Users

- Primary: a solo developer who repeatedly creates new Tuist-based mobile projects
- Secondary: anyone who wants the same CLI plus template bootstrap flow

## Non-Goals

- Supporting non-Tuist project systems
- Generating Android, backend, or web stacks
- Guessing missing repo names, bundle IDs, or Cloud settings without user confirmation
- Silent fallback from GitHub-backed creation to local-only
- Silent fallback from Tuist Cloud plus cache setup to local-only cache behavior
- Solving post-bootstrap product implementation

## Product Shape

The solution has three parts:

1. Two public template repositories:
   - `tuist-ios-starter`
   - `tuist-ios-catalyst-starter`

2. One CLI inside `Zach-Skills`:
   - `bin/zach-mobile-init`

3. One orchestration skill inside `Zach-Skills`:
   - `bootstrap-tuist-mobile-project`

The skill is the interactive layer. The CLI is the deterministic initializer. The templates are the source skeletons.

## Core Decisions

### Templates live in separate public repos

GitHub template repos are the cleanest way to make the result reusable both internally and externally. A public template repo is easier to discover, clone, and version than embedding raw templates only inside `Zach-Skills`.

### The skill does the interviewing

The user should talk to Codex, not to a shell script full of flags. The skill is responsible for:

- capability detection
- explaining available modes
- asking questions
- surfacing blocked options
- getting explicit confirmation

### The CLI does the deterministic file work

The CLI should not ask interactive questions. It should accept one structured config payload and perform:

- template materialization
- placeholder replacement
- file and directory renames
- script permission normalization
- validation

This keeps the behavior testable and repeatable.

### No silent downgrade rule

If the user asks for GitHub creation but `gh auth` is not available, the skill must say so and ask what to do next. It may not quietly switch to local-only creation.

The same rule applies to:

- repo visibility
- initial push
- Tuist Cloud project creation
- Xcode cache setup
- preview sharing support

### One template family, two shapes

The differences between pure iOS and iOS plus Mac Catalyst are important enough to justify separate public template repos. Trying to squeeze both into one template with lots of conditional content would make both harder to reason about.

## Supported Modes

The skill must present these as explicit user choices:

- `local-only`
- `github-backed`
- `github-and-tuist-cloud`

Descriptions:

- `local-only`: create and initialize the project directory only
- `github-backed`: create a GitHub repo and link the local project to it
- `github-and-tuist-cloud`: create the GitHub repo, create the Tuist Cloud project, enable Xcode cache, and run setup

If a chosen mode is not currently available, the skill must explain why and ask the user how they want to proceed.

## Capability Detection

Before asking creation questions, the skill must detect these capabilities:

- `git`
- `gh`
- `gh auth status`
- `mise`
- `tuist`
- `tuist auth whoami`

The skill should summarize the results in plain language before asking for the creation mode.

Example summary:

- GitHub CLI: installed and logged in
- Tuist Cloud: logged in
- `mise`: available
- `tuist`: available

or

- GitHub CLI: installed but not logged in
- Tuist Cloud: not logged in

This summary provides the context for the next choice. It must not automatically alter the user's options.

## User Interview Flow

The skill should ask these questions in order:

1. Creation mode
   - local-only
   - local plus GitHub
   - local plus GitHub plus Tuist Cloud/cache

2. Template type
   - pure iOS
   - iOS plus Mac Catalyst

3. Project name
   - e.g. `Kigen`

4. GitHub owner
   - only when the chosen mode includes GitHub

5. GitHub repo name
   - default can be derived from project name, but the skill must ask for confirmation

6. GitHub repo visibility
   - `private` or `public`
   - always explicit, never implied

7. Bundle identifier
   - e.g. `com.zach.kigen`

8. Default iOS simulator device
   - e.g. `iPhone 16`

9. Whether to enable Tuist Cloud project creation and Xcode cache setup
   - only when supported by the chosen mode and current capability state

10. Whether to create and push the initial commit
    - always explicit

Every action with external side effects must be confirmed before execution.

## Explicit Confirmation Rules

The skill must explicitly confirm before:

- creating a GitHub repo
- choosing the repo visibility
- creating a Tuist Cloud project
- running `tuist setup cache`
- creating the initial commit
- pushing the initial commit
- re-asking after a capability mismatch

The skill must never:

- silently switch `github-backed` to `local-only`
- silently skip Tuist Cloud setup
- silently skip Xcode cache setup
- silently change visibility
- silently suppress push

## CLI Contract

The CLI should accept a structured config. JSON is the cleanest first version.

Example:

```json
{
  "mode": "github-and-tuist-cloud",
  "template": "ios-catalyst",
  "project_name": "SubPanda",
  "repo_name": "subpanda",
  "owner": "Zach677",
  "bundle_id": "org.zaxh.SubPanda",
  "full_handle": "zach/subpanda",
  "visibility": "private",
  "ios_simulator_device": "iPhone 16",
  "create_initial_commit": true,
  "push_after_init": true,
  "setup_tuist_cache": true
}
```

The skill owns user interaction. The CLI only validates and executes.

## CLI Responsibilities

`zach-mobile-init` should handle:

1. validating required fields
2. validating the destination path
3. materializing template files
4. renaming project/workspace/scheme paths
5. replacing placeholders across text files
6. normalizing executable permissions on scripts
7. doing local consistency checks
8. returning machine-readable status

It should be safe to re-run on an uncommitted failed bootstrap, or at least fail clearly when re-run is not safe.

## Template Placeholder Standard

The templates should use a small, stable placeholder vocabulary:

- `__PROJECT_NAME__`
- `__PROJECT_NAME_LOWER__`
- `__REPO_NAME__`
- `__BUNDLE_ID__`
- `__FULL_HANDLE__`
- `__IOS_SIMULATOR_DEVICE__`
- `__APP_SCHEME__`
- `__TEST_SCHEME__`
- `__CACHE_SERVICE_SLUG__`

These should cover:

- `Project.swift`
- `Tuist.swift`
- `Workspace.swift`
- `mise.toml`
- `.codex/environments/environment.toml`
- `AGENTS.md`
- `README.md`
- `scripts/*.sh`
- `*.xcscheme`
- project and workspace filenames when needed

The templates must not ship with a real app name or real GitHub handle still embedded in user-facing locations.

## Template Contents

Both templates should include:

- `Project.swift`
- `Tuist.swift`
- `mise.toml`
- `.codex/environments/environment.toml`
- `.gitignore`
- `AGENTS.md`
- `README.md`
- `scripts/tuist-common.sh`
- `scripts/run-ios-sim.sh`
- `scripts/build-ios-sim.sh`
- `scripts/test-ios.sh`
- `scripts/share-ios-preview.sh`
- `scripts/warm-external-cache.sh`

The Catalyst template should additionally include:

- `scripts/run-macos.sh`
- `scripts/test-macos.sh`

## Skill Responsibilities

`bootstrap-tuist-mobile-project` should:

1. detect environment capabilities
2. explain available and unavailable paths
3. ask the interview questions
4. request confirmation before side effects
5. create the GitHub repo when requested
6. materialize the template in the local destination
7. call `zach-mobile-init`
8. create the Tuist Cloud project when requested
9. run `tuist setup cache` when requested
10. run the first warm/generate flow
11. create and push the initial commit when requested
12. present the resulting project path, repo URL, and available commands

## Tooling Sequence

The skill's execution sequence should be:

1. detect capabilities
2. collect user choices
3. confirm side effects
4. if GitHub mode:
   - `gh repo create ...`
5. clone or create the local target directory
6. run `zach-mobile-init --config ...`
7. if Tuist Cloud requested:
   - `tuist project create <fullHandle>` when needed
8. if Xcode cache requested:
   - `tuist setup cache`
9. run:
   - `mise run warm-external-cache`
10. if initial commit requested:
   - `git add`
   - `git commit`
11. if push requested:
   - `git push`

Every external action after step 2 must be consistent with the user's confirmed selections.

## Failure Handling

The skill should fail closed:

- if `gh` is missing and the user selected a GitHub-backed mode, stop and ask whether they want to switch modes or fix auth first
- if `tuist auth` is missing and the user selected Tuist Cloud setup, stop and ask whether they want to log in first or continue without Cloud setup
- if the target directory already exists, stop and ask whether to reuse, replace, or abort
- if the GitHub repo name is already taken, ask whether to choose another name
- if the requested `fullHandle` already exists, ask whether to bind to it or choose another handle

No implicit downgrade is allowed.

## Testing Strategy

The first version should have automated tests around the CLI, not the interactive skill body.

Test the CLI for:

- placeholder replacement
- directory rename behavior
- project/workspace/scheme rename behavior
- generated Codex action correctness
- generated `mise` task correctness
- failure on missing required config
- failure on unresolved placeholders

The skill itself should be validated with one real dry run per mode:

- local-only
- github-backed
- github-and-tuist-cloud

## Repo Layout In Zach-Skills

Recommended structure:

```text
Zach-Skills/
├── README.md
├── docs/superpowers/specs/
├── skills/
│   └── bootstrap-tuist-mobile-project/
│       ├── SKILL.md
│       ├── README.md
│       ├── references/
│       │   └── flow.md
│       ├── scripts/
│       │   └── bootstrap_tuist_mobile_project.py
│       └── agents/
│           └── openai.yaml
└── bin/
    └── zach-mobile-init
```

The public templates live in separate repositories and are referenced by URL or repo slug in the skill and CLI config.

## Recommended Public Template Repositories

- `tuist-ios-starter`
- `tuist-ios-catalyst-starter`

Both should be public and marked as GitHub template repositories.

## Security And Trust Boundaries

The skill must treat these values as sensitive and user-controlled:

- GitHub visibility
- repo owner
- repo name
- bundle id
- fullHandle
- whether to push

It should never infer or mutate those without asking.

The CLI should never create remote resources by itself. Remote creation remains the skill's job so the user interaction boundary stays clean.

## Recommended Next Step

After this spec is approved, the implementation plan should proceed in this order:

1. create the two public template repos
2. define the exact placeholder set and replacement rules
3. implement `zach-mobile-init`
4. scaffold `bootstrap-tuist-mobile-project`
5. wire the skill to the CLI and template repos
6. validate all three creation modes end-to-end
