# Tuist PR Upgrader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `tuist-pr-upgrader` skill for `Zach-Skills` that scans configured Tuist repos, upgrades their pinned `mise` Tuist version one repo at a time, verifies each repo, and opens one PR per successful repo upgrade.

**Architecture:** The skill is a thin documentation layer over one Python CLI. The CLI reads a fenced `toml` block from `EXTEND.md` using `tomllib`, discovers candidate repos by file shape, computes a per-repo upgrade plan, and executes guarded git / gh steps only when the repo is explicitly configured and verification passes. Markdown docs explain the workflow; the script owns the deterministic behavior.

**Tech Stack:** Python 3 stdlib (`argparse`, `dataclasses`, `pathlib`, `re`, `subprocess`, `tempfile`, `tomllib`, `unittest`), Git, GitHub CLI, `mise`

---

### Task 1: Scaffold The Skill Shell

**Files:**
- Create: `skills/tuist-pr-upgrader/SKILL.md`
- Create: `skills/tuist-pr-upgrader/README.md`
- Create: `skills/tuist-pr-upgrader/EXTEND.example.md`
- Create: `skills/tuist-pr-upgrader/references/README.md`
- Create: `skills/tuist-pr-upgrader/scripts/README.md`
- Modify: `README.md`

- [ ] **Step 1: Scaffold the new skill directory**

Run:

```bash
python3 scripts/new_skill.py "Tuist PR Upgrader" \
  --description "Use when scanning multiple Tuist repos, upgrading their pinned Tuist version, and opening one PR per repo." \
  --with-extend
```

Expected: `skills/tuist-pr-upgrader/` exists with the default scaffold files.

- [ ] **Step 2: Verify the scaffolded files exist before rewriting them**

Run:

```bash
find skills/tuist-pr-upgrader -maxdepth 2 -type f | sort
```

Expected: the directory contains `SKILL.md`, `README.md`, `EXTEND.example.md`, `references/README.md`, and `scripts/README.md`.

- [ ] **Step 3: Rewrite the new skill shell to match the agreed shape**

Replace placeholder content with minimal real placeholders only:

- `SKILL.md`: trigger cases, workflow outline, guardrails, on-demand references
- `README.md`: setup/runbook shell
- `EXTEND.example.md`: comment header plus an empty fenced `toml` block
- root `README.md`: add a new row for `tuist-pr-upgrader`

Use this `EXTEND.example.md` starter shape:

````md
# Tuist PR Upgrader Preferences
#
# Copy this file to one of:
# - .zach-skills/tuist-pr-upgrader/EXTEND.md
# - ${XDG_CONFIG_HOME:-$HOME/.config}/zach-skills/tuist-pr-upgrader/EXTEND.md
# - ~/.zach-skills/tuist-pr-upgrader/EXTEND.md
#
# Non-secret settings only.

```toml
scan_roots = ["/path/to/repos"]
include_repos = []
exclude_repos = []
allow_push = false
allow_pr = false
```
````

- [ ] **Step 4: Re-read the scaffolded docs for placeholder leaks**

Run:

```bash
rg -n "Replace this|placeholder|my-new-skill|Lean Skill" skills/tuist-pr-upgrader README.md
```

Expected: no placeholder text remains in the new skill files.

- [ ] **Step 5: Commit the scaffold-only slice**

Run:

```bash
git add README.md skills/tuist-pr-upgrader
git commit -m "feat: scaffold tuist pr upgrader skill"
```

Expected: one commit containing only the new skill shell and root README index update.

### Task 2: Implement Config Loading And Candidate Detection

**Files:**
- Create: `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`
- Create: `tests/test_tuist_pr_upgrader.py`
- Modify: `skills/tuist-pr-upgrader/EXTEND.example.md`
- Create: `skills/tuist-pr-upgrader/references/config-schema.md`

- [ ] **Step 1: Write the failing parser and discovery tests**

Add tests for:

- extracting the first fenced `toml` block from `EXTEND.md`
- parsing top-level config values with `tomllib`
- resolving `EXTEND.md` lookup paths in this order:
  - `.zach-skills/tuist-pr-upgrader/EXTEND.md` under the current working directory
  - `${XDG_CONFIG_HOME:-$HOME/.config}/zach-skills/tuist-pr-upgrader/EXTEND.md`
  - `~/.zach-skills/tuist-pr-upgrader/EXTEND.md`
- treating a repo as a Tuist candidate only when `Project.swift`, `Tuist.swift`, and `mise.toml` are all present

Use a fixture like:

```python
sample_extend = """
# Config

```toml
scan_roots = ["/tmp/repos"]
allow_push = false
allow_pr = false

[repos.mitori]
path = "/tmp/repos/mitori"
verify_commands = ["mise run test-macos"]
```
"""
```

- [ ] **Step 2: Run the new test file and confirm it fails**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: FAIL with import or attribute errors because `tuist_pr_upgrader.py` does not exist yet.

- [ ] **Step 3: Implement the minimal parser and discovery layer**

Add these core pieces to `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`:

```python
@dataclass
class RepoConfig:
    name: str
    path: Path
    verify_commands: list[str]
    base_branch: str | None = None


@dataclass
class ExtendConfig:
    scan_roots: list[Path]
    include_repos: list[str]
    exclude_repos: list[str]
    allow_push: bool
    allow_pr: bool
    repos: dict[str, RepoConfig]
```

Implement:

- `configured_extend_file_paths()`
- `extract_toml_block(markdown: str) -> str`
- `load_extend_config(path: Path) -> ExtendConfig`
- `is_tuist_candidate(path: Path) -> bool`
- `discover_candidate_repos(scan_roots: list[Path]) -> list[Path]`

- [ ] **Step 4: Re-run the targeted tests and make them pass**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: PASS for the parser and discovery cases.

- [ ] **Step 5: Commit the parser / discovery slice**

Run:

```bash
git add skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py \
  skills/tuist-pr-upgrader/EXTEND.example.md \
  skills/tuist-pr-upgrader/references/config-schema.md \
  tests/test_tuist_pr_upgrader.py
git commit -m "feat: add tuist repo discovery and config parsing"
```

Expected: one focused commit for config loading and candidate detection.

### Task 3: Add Planning Logic And Version Analysis

**Files:**
- Modify: `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`
- Modify: `tests/test_tuist_pr_upgrader.py`
- Modify: `skills/tuist-pr-upgrader/references/config-schema.md`
- Modify: `skills/tuist-pr-upgrader/README.md`

- [ ] **Step 1: Write failing tests for version and plan analysis**

Add tests for:

- reading the pinned Tuist version from `mise.toml`
- replacing only the `tuist = "..."` entry
- retrieving the latest stable version via `mise latest tuist`
- planning statuses:
  - `up-to-date`
  - `needs-upgrade`
  - `skipped-missing-verification`
  - `skipped-config-error`
- suggesting a fallback verify command in the report without executing it

Use mocked subprocess output like:

```python
CompletedProcess(args=["mise", "latest", "tuist"], returncode=0, stdout="4.171.2\n", stderr="")
```

- [ ] **Step 2: Run the targeted tests and confirm the new cases fail**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: FAIL on the newly added planning and version cases.

- [ ] **Step 3: Implement plan-mode helpers**

Add:

```python
@dataclass
class RepoPlan:
    name: str
    path: Path
    current_version: str | None
    target_version: str | None
    status: str
    reason: str | None
    verify_commands: list[str]
    suggested_verify_commands: list[str]
```

Implement:

- `get_latest_tuist_version()` using `mise latest tuist`
- `read_pinned_tuist_version(mise_toml_path: Path) -> str | None`
- `replace_pinned_tuist_version(text: str, version: str) -> str`
- `suggest_verify_commands(repo_path: Path) -> list[str]`
- `build_repo_plan(...) -> RepoPlan`
- `render_plan_report(...) -> str`

Suggested verify-command heuristics should be reporting-only:

- if `mise.toml` contains `test-macos`, suggest `mise run test-macos`
- else if `mise.toml` contains `run-macos`, suggest `mise run run-macos`
- else suggest `mise exec -- tuist generate --no-open`

- [ ] **Step 4: Re-run the targeted tests and make them pass**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: PASS for parser, discovery, and plan-mode tests.

- [ ] **Step 5: Commit the planning slice**

Run:

```bash
git add skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py \
  skills/tuist-pr-upgrader/README.md \
  skills/tuist-pr-upgrader/references/config-schema.md \
  tests/test_tuist_pr_upgrader.py
git commit -m "feat: add tuist upgrade planning workflow"
```

Expected: one commit for version lookup, planning, and reporting.

### Task 4: Implement Run Mode With Guardrails

**Files:**
- Modify: `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`
- Modify: `tests/test_tuist_pr_upgrader.py`
- Modify: `skills/tuist-pr-upgrader/README.md`

- [ ] **Step 1: Write failing run-mode tests**

Add tests for:

- skipping dirty worktrees
- skipping when an existing same-version PR is found
- creating branch names like `chore/tuist-4-171-2`
- updating `mise.toml` before verification runs
- refusing to push or create a PR when verification fails
- honoring `allow_push = false`, `allow_pr = false`, and `--dry-run`

Mock all git and `gh` subprocess calls.

- [ ] **Step 2: Run the targeted tests and confirm run-mode failures**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: FAIL on the new run-mode cases.

- [ ] **Step 3: Implement the execution engine**

Add:

```python
@dataclass
class RepoRunResult:
    name: str
    status: str
    branch: str | None
    pr_url: str | None
    summary: str
```

Implement:

- `run_command(...)`
- `git_worktree_is_clean(repo: Path) -> bool`
- `resolve_base_branch(repo: Path, configured: str | None) -> str`
- `existing_pr_for_version(repo: Path, version: str, base_branch: str) -> str | None`
- `build_branch_name(version: str) -> str`
- `build_pr_body(...) -> str`
- `run_verification_commands(repo: Path, commands: list[str])`
- `run_repo_upgrade(...) -> RepoRunResult`

Execution order inside `run_repo_upgrade(...)`:

1. `git fetch origin`
2. `git switch <base_branch>`
3. `git pull --ff-only origin <base_branch>`
4. `git switch -c <branch>`
5. write updated `mise.toml`
6. run configured verification commands
7. `git add mise.toml`
8. `git commit -m "chore: bump Tuist to <version>"`
9. optional `git push -u origin <branch>`
10. optional `gh pr create ...`

- [ ] **Step 4: Re-run the targeted tests and make them pass**

Run:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
```

Expected: PASS for parser, planning, and run-mode tests.

- [ ] **Step 5: Commit the guarded execution slice**

Run:

```bash
git add skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py \
  skills/tuist-pr-upgrader/README.md \
  tests/test_tuist_pr_upgrader.py
git commit -m "feat: add guarded tuist upgrade execution"
```

Expected: one commit for run-mode behavior and safety gates.

### Task 5: Finish The Skill Docs

**Files:**
- Modify: `skills/tuist-pr-upgrader/SKILL.md`
- Modify: `skills/tuist-pr-upgrader/README.md`
- Modify: `skills/tuist-pr-upgrader/EXTEND.example.md`
- Modify: `skills/tuist-pr-upgrader/references/config-schema.md`

- [ ] **Step 1: Rewrite `SKILL.md` as the actual trigger and workflow doc**

Include:

- trigger cases
- `EXTEND.md` lookup order
- `scan`, `plan`, `run` commands
- safety rules
- report-only behavior without config
- dry-run behavior

- [ ] **Step 2: Rewrite `README.md` as the human runbook**

Document:

- prerequisites: `mise`, `git`, `gh`
- how `EXTEND.md` works
- how to run `scan`, `plan`, `run`
- expected report outcomes
- how weekly automation should call the skill

- [ ] **Step 3: Finalize the example config and schema doc**

The example should show one fully configured repo:

```toml
scan_roots = ["/path/to/zach-repo"]
include_repos = ["mitori"]
exclude_repos = []
allow_push = true
allow_pr = true

[repos.mitori]
path = "/path/to/zach-repo/mitori"
base_branch = "main"
verify_commands = ["mise run test-macos"]
```

The schema doc should explain every top-level key and every per-repo key.

- [ ] **Step 4: Re-read the docs for broken paths and command drift**

Run:

```bash
rg -n "tuist-pr-upgrader|EXTEND.md|mise latest tuist|gh pr create" \
  skills/tuist-pr-upgrader README.md
```

Expected: the documented commands match the implemented CLI and safety model.

- [ ] **Step 5: Commit the docs slice**

Run:

```bash
git add README.md \
  skills/tuist-pr-upgrader/SKILL.md \
  skills/tuist-pr-upgrader/README.md \
  skills/tuist-pr-upgrader/EXTEND.example.md \
  skills/tuist-pr-upgrader/references/config-schema.md
git commit -m "docs: add tuist pr upgrader runbook"
```

Expected: one commit for finished skill docs and examples.

### Task 6: Validate The Whole Skill End To End

**Files:**
- Modify: `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`
- Modify: `tests/test_tuist_pr_upgrader.py`
- Modify: `skills/tuist-pr-upgrader/README.md`

- [ ] **Step 1: Run the full Zach-Skills test suite**

Run:

```bash
python3 -m unittest discover -s tests -q
```

Expected: PASS, including the new `test_tuist_pr_upgrader.py` cases.

- [ ] **Step 2: Run CLI smoke checks**

Run:

```bash
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py --help
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py scan --help
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py plan --help
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py run --help
```

Expected: each command prints help text without stack traces.

- [ ] **Step 3: Run one dry-run planning pass with a temporary config**

Create a temporary file like `/tmp/tuist-pr-upgrader-extend.md` containing:

````md
# Temp Config

```toml
scan_roots = ["/Users/star/Developer/zach-repo"]
include_repos = ["mitori"]
exclude_repos = []
allow_push = false
allow_pr = false

[repos.mitori]
path = "/Users/star/Developer/zach-repo/mitori"
verify_commands = ["mise run test-macos"]
```
````

Then run:

```bash
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py plan \
  --extend /tmp/tuist-pr-upgrader-extend.md

python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py run \
  --extend /tmp/tuist-pr-upgrader-extend.md \
  --dry-run
```

Expected: the plan reports either `needs-upgrade` or `up-to-date`, and the dry-run reports the branch / PR actions it would take without mutating remotes.

- [ ] **Step 4: Fix any validation fallout and rerun the affected command**

If a test or smoke command fails, patch only the relevant files and rerun the smallest affected command first, then rerun the full suite:

```bash
python3 -m unittest tests.test_tuist_pr_upgrader -q
python3 -m unittest discover -s tests -q
```

Expected: clean pass after the patch.

- [ ] **Step 5: Commit the validation fixes and final state**

Run:

```bash
git add skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py \
  skills/tuist-pr-upgrader/README.md \
  tests/test_tuist_pr_upgrader.py
git commit -m "test: validate tuist pr upgrader workflow"
```

Expected: final commit captures only the fixes that were necessary to make the skill shippable.
